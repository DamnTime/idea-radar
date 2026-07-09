from datetime import datetime
from hashlib import md5

import feedparser

from src.models import ContentItem
from src.scrapers.base import BaseScraper


class RSSScraper(BaseScraper):
    def __init__(self, config: dict, http_client=None):
        super().__init__(config, http_client)
        self.feeds = config.get("feeds", [])

    async def fetch(self, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []
        for feed_cfg in self.feeds:
            if not feed_cfg.get("enabled", True):
                continue
            try:
                items.extend(self._fetch_feed(feed_cfg, since))
            except Exception as e:
                print(f"[RSS] Failed to fetch {feed_cfg.get('url')}: {e}")
        return items

    def _fetch_feed(self, feed_cfg: dict, since: datetime) -> list[ContentItem]:
        url = feed_cfg["url"]
        name = feed_cfg.get("name", url)
        category = feed_cfg.get("category", "")

        parsed = feedparser.parse(url)
        items: list[ContentItem] = []

        for entry in parsed.entries:
            published = self._parse_date(entry)
            if published and published < since:
                continue

            content = (
                entry.get("summary")
                or entry.get("description")
                or entry.get("content", [{}])[0].get("value", "")
                or ""
            )

            item_id = self._generate_id("rss", "article", md5(entry.link.encode()).hexdigest()[:12])

            items.append(ContentItem(
                id=item_id,
                source="rss",
                source_type="article",
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                content=content[:1500],
                author=entry.get("author"),
                published_at=published or datetime.now(),
                tags=[category] if category else [],
            ))

        return items

    @staticmethod
    def _parse_date(entry) -> datetime | None:
        for field in ("published_parsed", "updated_parsed", "created_parsed"):
            tp = getattr(entry, field, None)
            if tp:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(tp))
                except Exception:
                    pass
        return None
