import re
from datetime import datetime, timezone
from hashlib import md5

from src.models import ContentItem
from src.scrapers.base import BaseScraper


class ZhihuScraper(BaseScraper):
    HOT_LIST_URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    SEARCH_URL = "https://www.zhihu.com/api/v4/search_v3"

    def __init__(self, config: dict, http_client=None):
        super().__init__(config, http_client)
        self.fetch_hot = config.get("fetch_hot", True)
        self.search_keywords = config.get("search_keywords", [])
        self.fetch_limit = config.get("fetch_limit", 30)

    async def fetch(self, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []

        if self.fetch_hot:
            try:
                items.extend(await self._fetch_hot_list(since))
            except Exception as e:
                print(f"[Zhihu] Failed to fetch hot list: {e}")

        for keyword in self.search_keywords:
            try:
                items.extend(await self._search(keyword, since))
            except Exception as e:
                print(f"[Zhihu] Failed to search '{keyword}': {e}")

        return items

    async def _fetch_hot_list(self, since: datetime) -> list[ContentItem]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-requested-with": "fetch",
            "Referer": "https://www.zhihu.com/hot",
        }
        params = {"limit": min(self.fetch_limit, 50)}
        resp = await self.client.get(self.HOT_LIST_URL, headers=headers, params=params, timeout=15)
        data = resp.json()

        items: list[ContentItem] = []
        for entry in data.get("data", []):
            target = entry.get("target", {})
            question = target.get("question", {}) or target
            title = question.get("title", "") or target.get("title_area", {}).get("text", "")
            url = question.get("url", f"https://www.zhihu.com/question/{question.get('id', '')}")

            native_id = str(question.get("id", "")) or md5(url.encode()).hexdigest()[:12]
            item_id = self._generate_id("zhihu", "hot", native_id)

            detail = target.get("excerpt", "") or target.get("content", "") or ""
            detail = re.sub(r"<[^>]+>", "", detail)[:1500]

            items.append(ContentItem(
                id=item_id,
                source="zhihu",
                source_type="hot",
                title=title,
                url=url,
                content=detail or title,
                author=question.get("author", {}).get("name") if isinstance(question.get("author"), dict) else None,
                published_at=datetime.now(timezone.utc),
                score=float(entry.get("detail_text", "0").replace("万", "0000").replace("亿", "00000000") or 0),
                tags=["zhihu-hot"],
            ))

        return items

    async def _search(self, keyword: str, since: datetime) -> list[ContentItem]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-requested-with": "fetch",
            "Referer": "https://www.zhihu.com/search",
        }
        params = {"q": keyword, "limit": min(self.fetch_limit // max(len(self.search_keywords), 1), 20)}
        resp = await self.client.get(self.SEARCH_URL, headers=headers, params=params, timeout=15)
        data = resp.json()

        items: list[ContentItem] = []
        for entry in data.get("data", []):
            obj = entry.get("object", {})
            question = obj.get("question", {}) or obj
            title = question.get("title", "") or obj.get("name", "")
            url = question.get("url", obj.get("url", ""))

            native_id = str(question.get("id", "") or obj.get("id", ""))
            if not native_id:
                continue
            item_id = self._generate_id("zhihu", "search", native_id)

            detail = obj.get("content", "") or obj.get("excerpt", "") or ""
            detail = re.sub(r"<[^>]+>", "", detail)[:1500]

            items.append(ContentItem(
                id=item_id,
                source="zhihu",
                source_type="search",
                title=title,
                url=url,
                content=detail or title,
                author=question.get("author", {}).get("name") if isinstance(question.get("author"), dict) else None,
                published_at=datetime.now(timezone.utc),
                tags=["zhihu-search", keyword],
            ))

        return items
