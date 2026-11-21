import logging
from typing import Any, Optional
import uuid

from qdrant_client import AsyncQdrantClient, models

from app.config.settings import Settings, settings as global_settings
from app.schemas.knowledge import KnowledgeQdrantPayload

logger = logging.getLogger(__name__)


class KnowledgeRepositoryError(Exception):
    """Base exception for Qdrant knowledge repository operations."""
    pass


class KnowledgeRepositoryDimensionMismatchError(KnowledgeRepositoryError):
    """Raised when existing collection vector dimension does not match configured embedding dimension."""
    pass


def get_qdrant_client(
    settings: Optional[Settings] = None,
    location: Optional[str] = None,
) -> AsyncQdrantClient:
    """
    Factory for instantiating an AsyncQdrantClient.
    Supports in-memory location (e.g. location=":memory:") for hermetic tests.
    """
    if location is not None:
        return AsyncQdrantClient(location=location)

    active_settings = settings or global_settings
    return AsyncQdrantClient(
        host=active_settings.qdrant_host,
        port=active_settings.qdrant_port,
        api_key=active_settings.qdrant_api_key,
        timeout=active_settings.qdrant_timeout_seconds,
        check_compatibility=False,
    )


class KnowledgeRepository:
    """
    Data access layer for managing persistent AI knowledge points and vector representations in Qdrant.
    Encapsulates collection lifecycle, required payload indexing, and deterministic upsert/retrieval primitives.
    """

    # Only create payload indexes for fields with known filtering/authorization/retrieval requirements
    REQUIRED_PAYLOAD_INDEXES: list[tuple[str, models.PayloadSchemaType]] = [
        ("merchant_id", models.PayloadSchemaType.KEYWORD),
        ("access_scope", models.PayloadSchemaType.KEYWORD),
        ("knowledge_type", models.PayloadSchemaType.KEYWORD),
        ("entity_id", models.PayloadSchemaType.KEYWORD),
        ("is_current", models.PayloadSchemaType.BOOL),
    ]

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection_name: Optional[str] = None,
        settings: Optional[Settings] = None,
    ):
        self.client = client
        active_settings = settings or global_settings
        self.collection_name = collection_name or active_settings.qdrant_collection_name

    async def ensure_collection(self, vector_size: int, distance: str = "Cosine") -> None:
        """
        Idempotently ensures the knowledge collection exists with the required vector dimension and distance metric.
        Fails fast if an existing collection has an incompatible vector dimensionality.
        Ensures payload indexes exist on approved filtering and authorization fields.
        """
        dist_enum = getattr(models.Distance, distance.upper(), models.Distance.COSINE)
        exists = await self.client.collection_exists(self.collection_name)

        if exists:
            info = await self.client.get_collection(self.collection_name)
            existing_size: Optional[int] = None
            vectors_config = info.config.params.vectors
            if hasattr(vectors_config, "size"):
                existing_size = vectors_config.size
            elif isinstance(vectors_config, dict) and "size" in vectors_config:
                existing_size = vectors_config["size"]

            if existing_size is not None and existing_size != vector_size:
                raise KnowledgeRepositoryDimensionMismatchError(
                    f"Collection '{self.collection_name}' has vector dimension {existing_size}, "
                    f"but configured dimension is {vector_size}. "
                    "Model or dimension changes require explicit collection recreation/re-indexing."
                )
        else:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=dist_enum),
            )
            logger.info("Created Qdrant collection '%s' with dimension %d.", self.collection_name, vector_size)

        # Create known filtering/authorization payload indexes
        for field_name, schema_type in self.REQUIRED_PAYLOAD_INDEXES:
            try:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=schema_type,
                )
            except Exception as exc:
                # If index already exists or unsupported in test backend, log and continue
                logger.debug("Payload index for '%s' returned: %s", field_name, exc)

    async def upsert_knowledge_point(
        self,
        point_id: uuid.UUID | str,
        vector: list[float],
        payload: KnowledgeQdrantPayload | dict[str, Any],
    ) -> None:
        """
        Deterministically upserts a knowledge point into Qdrant.
        Current-state items overwrite existing points in place; historical items write stable period records.
        Waits for completion before returning to guarantee persistence before downstream state commits.
        """
        pid_str = str(point_id)
        if isinstance(payload, KnowledgeQdrantPayload):
            payload_dict = payload.model_dump(mode="json")
        elif hasattr(payload, "model_dump"):
            payload_dict = payload.model_dump(mode="json")
        else:
            payload_dict = dict(payload)

        point = models.PointStruct(
            id=pid_str,
            vector=vector,
            payload=payload_dict,
        )

        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
                wait=True,
            )
        except Exception as exc:
            raise KnowledgeRepositoryError(
                f"Failed to upsert knowledge point '{pid_str}' to collection '{self.collection_name}': {exc}"
            ) from exc

    async def get_knowledge_point(self, point_id: uuid.UUID | str) -> Optional[dict[str, Any]]:
        """
        Retrieves a knowledge point by its deterministic ID.
        Returns a dict containing point_id, vector, and payload, or None if not found.
        """
        pid_str = str(point_id)
        try:
            records = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[pid_str],
                with_payload=True,
                with_vectors=True,
            )
            if not records:
                return None
            record = records[0]
            return {
                "point_id": record.id,
                "vector": record.vector,
                "payload": record.payload,
            }
        except Exception as exc:
            raise KnowledgeRepositoryError(
                f"Failed to retrieve knowledge point '{pid_str}' from collection '{self.collection_name}': {exc}"
            ) from exc

    async def delete_knowledge_point(self, point_id: uuid.UUID | str) -> bool:
        """
        Deletes a knowledge point by its deterministic ID.
        """
        pid_str = str(point_id)
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[pid_str]),
                wait=True,
            )
            return True
        except Exception as exc:
            raise KnowledgeRepositoryError(
                f"Failed to delete knowledge point '{pid_str}' from collection '{self.collection_name}': {exc}"
            ) from exc

    async def delete_collection(self) -> None:
        """Deletes the entire collection (primarily used for test cleanup)."""
        try:
            if await self.client.collection_exists(self.collection_name):
                await self.client.delete_collection(self.collection_name)
        except Exception as exc:
            raise KnowledgeRepositoryError(
                f"Failed to delete collection '{self.collection_name}': {exc}"
            ) from exc
