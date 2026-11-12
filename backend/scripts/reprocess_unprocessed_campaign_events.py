"""Campaign-specific alias for backwards compatibility with reprocess_unprocessed_events.

Usage (from backend/):
    python -m scripts.reprocess_unprocessed_campaign_events
"""

import asyncio
import sys

from scripts.reprocess_unprocessed_events import reprocess_domain


async def reprocess_unprocessed_campaign_events() -> dict[str, int]:
    """Reprocess unprocessed campaign events through the generic reprocess_domain utility."""
    return await reprocess_domain("campaign")


def main() -> None:
    stats = asyncio.run(reprocess_unprocessed_campaign_events())
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
