from datetime import datetime
from html import unescape

import feedparser

from src.models import ContentItem
from src.scrapers.base import BaseScraper


class RedditScraper(BaseScraper):
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, config: dict, http_client=None):
        super().__init__(config, http_client)
        self.subreddits = config.get("subreddits", [])
        self.fetch_comments = config.get("fetch_comments", 3)

    async def fetch(self, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []
        for sr in self.subreddits:
            if not sr.get("enabled", True):
                continue
            try:
                result = await self._fetch_subreddit(sr, since)
                items.extend(result)
            except Exception as e:
                print(f"[Reddit] Failed to fetch r/{sr.get('subreddit')}: {e}")
        return items

    async def _fetch_subreddit(self, sr: dict, since: datetime) -> list[ContentItem]:
        sub = sr["subreddit"]
        sort = sr.get("sort", "hot")
        limit = sr.get("fetch_limit", 25)
        min_score = sr.get("min_score", 0)

        data = await self._try_json(
            f"https://www.reddit.com/r/{sub}/{sort}/.json?limit={limit}",
            f"https://old.reddit.com/r/{sub}/{sort}/.json?limit={limit}",
        )
        if data:
            return self._parse_json_data(data, sub, min_score, since)

        return await self._fetch_rss_fallback(sub, sort, min_score, since)

    def _parse_json_data(self, data: dict, sub: str, min_score: int, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []
        since_naive = since.replace(tzinfo=None) if since.tzinfo else since
        for post in data.get("data", {}).get("children", []):
            pdata = post.get("data", {})
            if pdata.get("score", 0) < min_score:
                continue
            created = datetime.fromtimestamp(pdata.get("created_utc", 0))
            if created < since_naive:
                continue
            title = unescape(pdata.get("title", "") or "")
            self_text = unescape(pdata.get("selftext", "") or "")[:1500]
            post_id = pdata.get("id", "")
            items.append(ContentItem(
                id=self._generate_id("reddit", "post", post_id),
                source="reddit",
                source_type="post",
                title=title,
                url=pdata.get("url", f"https://reddit.com/r/{sub}/comments/{post_id}/"),
                content=self_text or title,
                author=pdata.get("author"),
                published_at=created,
                score=float(pdata.get("score", 0)),
                comment_count=pdata.get("num_comments", 0),
                tags=[f"r/{sub}"],
            ))
        return items

    async def _fetch_rss_fallback(self, sub: str, sort: str, min_score: int, since: datetime) -> list[ContentItem]:
        url = f"https://www.reddit.com/r/{sub}/{sort}/.rss"
        try:
            resp = await self.client.get(url, headers=self.HEADERS, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                print(f"[Reddit] RSS fallback HTTP {resp.status_code} for r/{sub}")
                return []
            parsed = feedparser.parse(resp.text)
        except Exception as e:
            print(f"[Reddit] RSS fallback failed for r/{sub}: {e}")
            return []

        items: list[ContentItem] = []
        since_naive = since.replace(tzinfo=None) if since.tzinfo else since
        for entry in parsed.entries[:25]:
            created = self._parse_rss_date(entry)
            if created and since_naive and created < since_naive:
                continue

            title = entry.get("title", "")
            link = entry.get("link", "")
            content = entry.get("summary", "") or entry.get("description", "") or ""

            items.append(ContentItem(
                id=self._generate_id("reddit", "rss", entry.get("id", link)[:32]),
                source="reddit",
                source_type="post",
                title=title,
                url=link,
                content=content[:1500] or title,
                author=entry.get("author"),
                published_at=created or datetime.now(),
                tags=[f"r/{sub}"],
            ))

        print(f"[Reddit] RSS fallback got {len(items)} items from r/{sub}")
        return items

    @staticmethod
    def _parse_rss_date(entry) -> datetime | None:
        for field in ("published_parsed", "updated_parsed"):
            tp = getattr(entry, field, None)
            if tp:
                try:
                    from time import mktime
                    return datetime.fromtimestamp(mktime(tp))
                except Exception:
                    pass
        return None

    async def _try_json(self, *urls: str) -> dict | None:
        for url in urls:
            try:
                resp = await self.client.get(url, headers=self.HEADERS, timeout=30, follow_redirects=True)
                if resp.status_code in (403, 429):
                    print(f"[Reddit] HTTP {resp.status_code} on {url}, will try RSS fallback")
                    return None
                if resp.status_code != 200:
                    print(f"[Reddit] HTTP {resp.status_code} on {url}")
                    continue
                ct = resp.headers.get("content-type", "")
                if "json" not in ct:
                    continue
                return resp.json()
            except Exception as e:
                print(f"[Reddit] Error with {url}: {e}")
                continue
        return None
