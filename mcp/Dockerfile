FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# 依存インストール + タウンワーク用 Chromium（OS依存も含めて導入）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

# 各サイトの実装（server.py / api.py のみ。.venv 等は持ち込まない）
COPY baitoru/server.py baitoru/api.py ./baitoru/
COPY mynavi/server.py mynavi/api.py ./mynavi/
COPY townwork/server.py townwork/api.py ./townwork/
COPY gateway/gateway.py ./gateway/

EXPOSE 8000

CMD ["uvicorn", "gateway.gateway:app", \
     "--app-dir", "/app", "--host", "0.0.0.0", "--port", "8000"]
