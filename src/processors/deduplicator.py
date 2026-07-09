import jieba
from hashlib import md5

from src.models import ContentItem


class Deduplicator:
    FINGERPRINT_BITS = 64

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.seen_fingerprints: list[int] = []
        self.seen_urls: set[str] = set()

    def deduplicate(self, items: list[ContentItem]) -> list[ContentItem]:
        unique: list[ContentItem] = []
        for item in sorted(items, key=lambda x: x.published_at, reverse=True):
            if item.url in self.seen_urls:
                continue
            self.seen_urls.add(item.url)

            text = f"{item.title} {item.content[:200]}"
            fp = self._simhash(text)
            if any(self._hamming_similarity(fp, seen) >= self.threshold
                   for seen in self.seen_fingerprints):
                continue

            self.seen_fingerprints.append(fp)
            unique.append(item)

        return unique

    def _simhash(self, text: str) -> int:
        words = jieba.lcut(text)
        v = [0] * self.FINGERPRINT_BITS

        for word in words:
            if not word.strip():
                continue
            h = self._token_hash(word)
            weight = 1
            for i in range(self.FINGERPRINT_BITS):
                bit = (h >> i) & 1
                if bit:
                    v[i] += weight
                else:
                    v[i] -= weight

        fp = 0
        for i in range(self.FINGERPRINT_BITS):
            if v[i] > 0:
                fp |= (1 << i)
        return fp

    @staticmethod
    def _token_hash(token: str) -> int:
        h = md5(token.encode("utf-8")).digest()
        return int.from_bytes(h[:8], "big")

    @staticmethod
    def _hamming_similarity(a: int, b: int) -> float:
        xor = a ^ b
        dist = bin(xor).count("1")
        return 1.0 - (dist / 64.0)
