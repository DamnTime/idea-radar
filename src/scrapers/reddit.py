import re
from datetime import datetime
from html import unescape

from src.models import ContentItem
from src.scrapers.base import BaseScraper


class RedditScraper(BaseScraper):
    OLD_REDDIT = "https://old.reddit.com"

    def __init__(self, config: dict, http_client=None):
        super().__init__(config, http_client)
        self.subreddits = config.get("subreddits", [])
        self.fetch_comments = config.get("fetch_comments", 5)

    async def fetch(self, since: datetime) -> list[ContentItem]:
        items: list[ContentItem] = []
        for sr in self.subreddits:
            if not sr.get("enabled", True):
                continue
            try:
                items.extend(await self._fetch_subreddit(sr, since))
            except Exception as e:
                print(f"[Reddit] Failed to fetch r/{sr.get('subreddit')}: {e}")
        return items

    async def _fetch_subreddit(self, sr: dict, since: datetime) -> list[ContentItem]:
        sub = sr["subreddit"]
        sort = sr.get("sort", "hot")
        limit = sr.get("fetch_limit", 25)
        min_score = sr.get("min_score", 0)

        url = f"{self.OLD_REDDIT}/r/{sub}/{sort}/.json?limit={limit}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyIdeaRadar/1.0)"}
        resp = await self.client.get(url, headers=headers, timeout=30)
        data = resp.json()

        items: list[ContentItem] = []
        for post in data.get("data", {}).get("children", []):
            pdata = post.get("data", {})
            if pdata.get("score", 0) < min_score:
                continue

            created = datetime.fromtimestamp(pdata.get("created_utc", 0))
            if created < since:
                continue

            post_id = pdata.get("id", "")
            item_id = self._generate_id("reddit", "post", post_id)

            self_text = unescape(pdata.get("selftext", "") or "")[:1500]
            title = unescape(pdata.get("title", "") or "")

            comments = await self._fetch_comments(sub, post_id)

            items.append(ContentItem(
                id=item_id,
                source="reddit",
                source_type="post",
                title=title,
                url=pdata.get("url", f"{self.OLD_REDDIT}/r/{sub}/comments/{post_id}/"),
                content=self_text or title,
                author=pdata.get("author"),
                author_followers=0,
                published_at=created,
                score=float(pdata.get("score", 0)),
                comment_count=pdata.get("num_comments", 0),
                comments=comments,
                tags=[f"r/{sub}"],
            ))

        return items

    async def _fetch_comments(self, sub: str, post_id: str) -> list[str]:
        url = f"{self.OLD_REDDIT}/r/{sub}/comments/{post_id}/.json?limit=20"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyIdeaRadar/1.0)"}
        try:
            resp = await self.client.get(url, headers=headers, timeout=15)
            data = resp.json()
            if len(data) < 2:
                return []
            comments_data = data[1].get("data", {}).get("children", [])
            extracted = []
            for c in comments_data[:self.fetch_comments]:
                body = c.get("data", {}).get("body", "")
                if body and body not in ("[deleted]", "[removed]"):
                    extracted.append(unescape(body[:500]))
            return extracted
        except Exception:
            return []
