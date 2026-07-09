FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --quiet

COPY pyproject.toml .
RUN uv sync --no-dev --frozen

COPY . .

CMD ["uv", "run", "python", "-m", "src.main"]
