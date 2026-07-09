import argparse
import asyncio
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.orchestrator import Orchestrator


def load_config() -> dict:
    path = os.getenv("CONFIG_PATH", "data/config.json")
    config_path = Path(path)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        print("Copy data/config.example.json to data/config.json and edit it")
        exit(1)

    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    for key, val in os.environ.items():
        placeholder = "${" + key + "}"
        if placeholder in content:
            content = content.replace(placeholder, val)

    return json.loads(content)


def main():
    parser = argparse.ArgumentParser(description="AI 轻创业点子日报系统")
    parser.add_argument("--hours", type=int, default=24, help="采集时间窗口（小时）")
    parser.add_argument("--top-n", type=int, default=5, help="推送数量")
    args = parser.parse_args()

    config = load_config()
    orchestrator = Orchestrator(config)

    stats = asyncio.run(orchestrator.run(hours=args.hours, top_n=args.top_n))

    print("\n=== Pipeline Summary ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if stats.get("errors"):
        exit(1)


if __name__ == "__main__":
    main()
