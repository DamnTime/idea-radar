import json
import os
from pathlib import Path

from openai import AsyncOpenAI

from src.models import ContentItem, ScoredIdea


SCORER_PROMPT_TEMPLATE = """你是一个 AI 创业项目分析师。请评估以下创业点子的可行性。

## 项目描述
标题: {title}
内容: {content}

## 评估维度 (每项 0-10，越高越好)
1. 技术可行性: 技术实现难度如何？是否需要重资产/特殊资质？
2. 市场验证度: 是否有真实用户需求？竞品情况如何？
3. 启动成本: 时间/金钱/人力投入是否可控？
4. 可扩展性: 能否规模化？边际成本如何？
5. 风险等级: 法律/合规/竞争风险高不高？

## 输出要求
只返回 JSON，不要其他文字：
{{
  "tech_feasibility": <0-10>,
  "market_demand": <0-10>,
  "low_barrier": <0-10>,
  "scalability": <0-10>,
  "risk_level": <0-10>,
  "overall": <0-10>,
  "analysis": "<一句中文分析，50字内>"
}}"""


class Scorer:
    DIMENSION_WEIGHTS = {
        "tech_feasibility": 0.25,
        "market_demand": 0.25,
        "low_barrier": 0.20,
        "scalability": 0.15,
        "risk_level": 0.15,
    }

    def __init__(self, config: dict):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=os.getenv(config.get("api_key_env", "OPENAI_API_KEY")),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        self.model = os.getenv("OPENAI_MODEL") or config.get("model", "gpt-4o-mini")
        self._custom_prompt = self._load_prompt()

    @staticmethod
    def _load_prompt() -> str | None:
        prompt_path = Path("prompts/scorer.txt")
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return None

    async def score(self, item: ContentItem) -> ScoredIdea:
        prompt_template = self._custom_prompt or SCORER_PROMPT_TEMPLATE
        prompt = prompt_template.format(
            title=item.title,
            content=item.content[:800],
        )

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)

            overall = data.get("overall", 0)
            dimensions = {
                "tech_feasibility": float(data.get("tech_feasibility", 0)),
                "market_demand": float(data.get("market_demand", 0)),
                "low_barrier": float(data.get("low_barrier", 0)),
                "scalability": float(data.get("scalability", 0)),
                "risk_level": float(data.get("risk_level", 0)),
            }

            if not overall:
                overall = sum(
                    dimensions[k] * self.DIMENSION_WEIGHTS.get(k, 0.2)
                    for k in dimensions
                )

            return ScoredIdea(
                item=item,
                overall_score=round(overall, 1),
                dimensions=dimensions,
                analysis=data.get("analysis", ""),
            )
        except Exception as e:
            print(f"[Scorer] LLM scoring failed for {item.id}: {e}")
            return ScoredIdea(
                item=item,
                overall_score=0.0,
                dimensions={},
                analysis="评分失败",
            )
