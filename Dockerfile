FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY master_brain_bridge ./master_brain_bridge
COPY 01_INGEST ./01_INGEST
COPY schemas ./schemas
RUN python -m pip install --no-cache-dir .

VOLUME ["/app/00_RAW_ARCHIVE/chatgpt", "/app/02_EXTRACTED_THOUGHTS", "/data/canonical", "/data/conflicts", "/data/obsidian"]
ENV MASTER_BRAIN_CANONICAL_STORE_PATH=/data/canonical/canonical_records.jsonl \
    MASTER_BRAIN_CANDIDATE_QUEUE_PATH=/data/conflicts/candidate_queue.jsonl \
    MASTER_BRAIN_REVIEW_LOG_PATH=/data/conflicts/review_log.jsonl \
    OBSIDIAN_VAULT_PATH=/data/obsidian
ENTRYPOINT ["derekos"]
