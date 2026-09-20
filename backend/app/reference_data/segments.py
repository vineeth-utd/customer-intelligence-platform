from pydantic import BaseModel


class SegmentCatalogEntry(BaseModel):
    segment_name: str
    segment_definition: dict


SEGMENT_CATALOG: list[SegmentCatalogEntry] = [
    SegmentCatalogEntry(
        segment_name="All Active Shoppers",
        segment_definition={"type": "behavioral", "condition": "has_recent_session"}
    ),
    SegmentCatalogEntry(
        segment_name="High Value Customers",
        segment_definition={"type": "transactional", "metric": "lifetime_value", "operator": ">=", "value": 500}
    ),
    SegmentCatalogEntry(
        segment_name="Cart Abandoners",
        segment_definition={"type": "behavioral", "condition": "abandoned_cart_24h"}
    ),
]
