FROM python:3.11-slim

WORKDIR /app

# System deps for pdfplumber, pytesseract, playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Install playwright browsers
RUN playwright install chromium --with-deps

COPY firstknock/ ./firstknock/
COPY data/ ./data/
COPY alembic/ ./alembic/
COPY alembic.ini .

CMD ["uvicorn", "firstknock.main:app", "--host", "0.0.0.0", "--port", "8000"]
