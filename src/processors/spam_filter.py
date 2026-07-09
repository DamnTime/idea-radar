import re
from pathlib import Path

from src.models import ContentItem


class SpamFilter:
    SPAM_PATTERNS: list[str] = []

    SPAM_FEATURES = {
        "exclamation_ratio": 0.3,
        "emoji_count": 5,
    }

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.threshold = self.config.get("spam_threshold", 0.7)
        self._load_keywords()

    def _load_keywords(self):
        keyword_file = self.config.get("keyword_file", "config/spam_keywords.txt")
        path = Path(keyword_file)
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self.SPAM_PATTERNS = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        else:
            self.SPAM_PATTERNS = [
                r"月入[0-9万\+]+",
                r"零基础.*赚钱",
                r"日赚[0-9]+",
                r"副业.*月入",
                r"保姆级教程",
                r"小白也能",
                r"免费领取",
                r"限时加群",
                r"内部渠道",
                r"点击.*领取",
                r"扫码.*加群",
            ]

    def filter(self, items: list[ContentItem]) -> list[ContentItem]:
        clean: list[ContentItem] = []
        for item in items:
            score = self._compute_spam_score(item)
            if score >= self.threshold:
                item.tags.append("spam")
                continue
            clean.append(item)
        return clean

    def _compute_spam_score(self, item: ContentItem) -> float:
        text = f"{item.title} {item.content}"
        score = 0.0

        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.3

        exc_count = text.count("！") + text.count("!")
        if len(text) > 0 and exc_count / len(text) > self.SPAM_FEATURES["exclamation_ratio"]:
            score += 0.2

        emoji_num = len(re.findall(r"[\U0001F000-\U0010FFFF]", text))
        if emoji_num > self.SPAM_FEATURES["emoji_count"]:
            score += 0.2

        self_promotion_patterns = [
            r"我的.*(?:公众号|微信|星球|课程|社群)",
            r"私信.*领取",
            r"关注.*获取",
        ]
        for pat in self_promotion_patterns:
            if re.search(pat, text):
                score += 0.3
                break

        return min(score, 1.0)
