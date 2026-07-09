import re
from datetime import datetime, timezone
from hashlib import md5

from src.models import ContentItem
from src.scrapers.base import BaseScraper


class ZhihuScraper(BaseScraper):
    HOT_LIST_URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    SEARCH_URL = "https://www.zhihu.com/api/v4/search_v3"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "x-requested-with": "fetch",
        "Referer": "https://www.zhihu.com/hot",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    }

    def __init__(self, config: dict, http_client=None):
        super().__init__(config, http_client)
        self.fetch_hot = config.get("fetch_hot", True)
        self.search_keywords = config.get("search_keywords", [])
        self.fetch_limit = config.get("fetch_limit", 30)

    async def fetch(self, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []

        if self.fetch_hot:
            try:
                result = await self._fetch_hot_list(since)
                items.extend(result)
            except Exception as e:
                print(f"[Zhihu] Hot list failed: {e}")

        for keyword in self.search_keywords:
            try:
                result = await self._search(keyword, since)
                items.extend(result)
            except Exception as e:
                print(f"[Zhihu] Search '{keyword}' failed: {e}")

        return items

    async def _fetch_hot_list(self, since: datetime) -> list[ContentItem]:
        params = {"limit": min(self.fetch_limit, 50)}
        resp = await self.client.get(
            self.HOT_LIST_URL, headers=self.HEADERS, params=params, timeout=15,
            follow_redirects=True,
        )
        data = self._safe_json(resp, "hot_list")
        if not data:
            return []

        items: list[ContentItem] = []
        for entry in data.get("data", []):
            target = entry.get("target", {})
            question = target.get("question", {}) or target
            title = question.get("title", "") or target.get("title_area", {}).get("text", "")
            url = question.get("url", f"https://www.zhihu.com/question/{question.get('id', '')}")

            native_id = str(question.get("id", "")) or md5(url.encode()).hexdigest()[:12]
            detail = target.get("excerpt", "") or target.get("content", "") or ""

            items.append(ContentItem(
                id=self._generate_id("zhihu", "hot", native_id),
                source="zhihu",
                source_type="hot",
                title=title,
                url=url,
                content=re.sub(r"<[^>]+>", "", detail)[:1500] or title,
                published_at=datetime.now(timezone.utc),
                score=float(str(entry.get("detail_text", "0")).replace("万", "0000").replace("亿", "00000000") or 0),
                tags=["zhihu-hot"],
            ))

        return items

    async def _search(self, keyword: str, since: datetime) -> list[ContentItem]:
        params = {"q": keyword, "limit": min(self.fetch_limit // max(len(self.search_keywords), 1), 20)}
        headers = {**self.HEADERS, "Referer": "https://www.zhihu.com/search"}
        resp = await self.client.get(
            self.SEARCH_URL, headers=headers, params=params, timeout=15,
            follow_redirects=True,
        )
        data = self._safe_json(resp, f"search:{keyword}")
        if not data:
            return []

        items: list[ContentItem] = []
        for entry in data.get("data", []):
            obj = entry.get("object", {})
            question = obj.get("question", {}) or obj
            title = question.get("title", "") or obj.get("name", "")
            url = question.get("url", obj.get("url", ""))
            native_id = str(question.get("id", "") or obj.get("id", ""))
            if not native_id:
                continue

            detail = obj.get("content", "") or obj.get("excerpt", "") or ""

            items.append(ContentItem(
                id=self._generate_id("zhihu", "search", native_id),
                source="zhihu",
                source_type="search",
                title=title,
                url=url,
                content=re.sub(r"<[^>]+>", "", detail)[:1500] or title,
                published_at=datetime.now(timezone.utc),
                tags=["zhihu-search", keyword],
            ))

        return items

    @staticmethod
    def _safe_json(resp, label: str) -> dict | None:
        try:
            if resp.status_code != 200:
                print(f"[Zhihu] HTTP {resp.status_code} for {label}")
                return None
            ct = resp.headers.get("content-type", "")
            if "json" not in ct and "text" not in ct:
                print(f"[Zhihu] Unexpected content-type for {label}: {ct[:60]}")
                return None
            return resp.json()
        except Exception as e:
            preview = resp.text[:200] if hasattr(resp, "text") else "no body"
            print(f"[Zhihu] JSON parse failed for {label}: {e} | preview: {preview}")
            return None
