import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ── Algolia ───────────────────────────────────────────────────────────────────
ALGOLIA_APP_ID       = "45BWZJ1SGC"
ALGOLIA_INDEX        = "WaaSPublicCompanyJob_created_at_desc_production"
ALGOLIA_HITS_PER_PAGE = 100   # max per page; Algolia secured key caps total at 1000

# ── WaaS API ──────────────────────────────────────────────────────────────────
WAAS_BASE_URL   = "https://www.workatastartup.com"
WAAS_FETCH_URL  = f"{WAAS_BASE_URL}/companies/fetch"
FETCH_BATCH_SIZE   = 10     # IDs per /companies/fetch POST
RATE_DELAY_SECONDS = 1.0   # polite delay between batches

# ── Storage ───────────────────────────────────────────────────────────────────
DB_PATH      = "waas.db"          # local SQLite (always written)
COOKIES_FILE = "cookies.json"
ALGOLIA_KEY_FILE = "algolia_key.txt"

# Set in .env — if present, jobs are also upserted into Neon PostgreSQL
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# Set in .env — if present, Telegram notifications are sent after each run
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID:   str = os.getenv("TELEGRAM_CHAT_ID", "")
