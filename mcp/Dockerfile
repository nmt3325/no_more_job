FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# 依存インストール + タウンワーク用 Chromium（OS依存も含めて導入）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

# 統合パッケージ
COPY baito_mcp ./baito_mcp

EXPOSE 8000

# 単一サーバーを Streamable HTTP で公開（エンドポイント: /mcp）
CMD ["uvicorn", "baito_mcp.web:app", \
     "--app-dir", "/app", "--host", "0.0.0.0", "--port", "8000"]
