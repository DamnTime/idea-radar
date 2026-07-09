import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

from src.models import ContentItem, ScoredIdea
from src.scrapers import RSSScraper, RedditScraper, ZhihuScraper
from src.processors import Deduplicator, SpamFilter, Scorer
from src.notifiers import EmailNotifier


class Orchestrator:
    def __init__(self, config: dict):
        self.config = config
        self.scrapers: list = []
        self._init_scrapers()
        self.deduplicator = Deduplicator(
            threshold=config.get("filtering", {}).get("dedup_threshold", 0.92)
        )
        self.spam_filter = SpamFilter(config.get("filtering", {}))
        self.scorer = Scorer(config.get("ai", {}))
        self.notifier = EmailNotifier(config.get("notifier", {}).get("email", {}))
        self.http_client = httpx.AsyncClient(timeout=30)

    def _init_scrapers(self):
        sources = self.config.get("sources", {})
        if "rss" in sources:
            self.scrapers.append(("rss", RSSScraper, sources["rss"]))
        if "reddit" in sources:
            self.scrapers.append(("reddit", RedditScraper, sources["reddit"]))
        if "zhihu" in sources:
            self.scrapers.append(("zhihu", ZhihuScraper, sources["zhihu"]))

    async def run(self, hours: int = 24, top_n: int = 5) -> dict:
        start_time = time.time()
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stats = {"total_fetched": 0, "after_dedup": 0, "after_filter": 0, "scored": 0, "pushed": 0, "errors": []}

        all_items: list[ContentItem] = []
        async with self.http_client:
            tasks = []
            for name, scraper_cls, cfg in self.scrapers:
                scraper = scraper_cls(cfg, self.http_client)
                tasks.append(self._safe_fetch(name, scraper, since))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    stats["errors"].append(str(r))
                elif isinstance(r, list):
                    all_items.extend(r)

        stats["total_fetched"] = len(all_items)
        print(f"[Orchestrator] Fetched {len(all_items)} items from {len(self.scrapers)} sources")

        deduped = self.deduplicator.deduplicate(all_items)
        stats["after_dedup"] = len(deduped)
        print(f"[Orchestrator] After dedup: {len(deduped)} items")

        filtered = self.spam_filter.filter(deduped)
        stats["after_filter"] = len(filtered)
        print(f"[Orchestrator] After spam filter: {len(filtered)} items")

        scored: list[ScoredIdea] = []
        for item in filtered:
            result = await self.scorer.score(item)
            scored.append(result)
        stats["scored"] = len(scored)
        print(f"[Orchestrator] Scored {len(scored)} items")

        scored.sort(key=lambda x: x.overall_score, reverse=True)
        top_ideas = scored[:top_n]
        stats["pushed"] = len(top_ideas)

        if top_ideas:
            success = await self.notifier.send(top_ideas)
            if not success:
                stats["errors"].append("Email push failed")
        else:
            print("[Orchestrator] No ideas to push, skipping notification")

        elapsed = round(time.time() - start_time, 1)
        stats["pipeline_duration_seconds"] = elapsed
        print(f"[Orchestrator] Pipeline completed in {elapsed}s")

        self._save_briefing(top_ideas)
        return stats

    async def _safe_fetch(self, name: str, scraper, since: datetime) -> list[ContentItem]:
        try:
            items = await scraper.fetch(since)
            print(f"[{name}] Fetched {len(items)} items")
            return items
        except Exception as e:
            print(f"[{name}] Fetch error: {e}")
            raise

    def _save_briefing(self, ideas: list[ScoredIdea]):
        output_dir = Path("data/summaries")
        output_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        path = output_dir / f"{today}.json"

        data = []
        for idea in ideas:
            data.append({
                "title": idea.item.title,
                "url": idea.item.url,
                "source": idea.item.source,
                "overall_score": idea.overall_score,
                "dimensions": idea.dimensions,
                "analysis": idea.analysis,
                "author": idea.item.author,
                "published_at": idea.item.published_at.isoformat() if idea.item.published_at else None,
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[Orchestrator] Briefing saved to {path}")
