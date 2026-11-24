import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=False)
SEED_DATA_DIR = ROOT_DIR / "seed-data"
DATA_DIR = Path(os.getenv("DATA_DIR") or ROOT_DIR / "data").resolve()
CHROMA_PATH = DATA_DIR / "chroma"

DATA_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_EMPLOYEE_ID = "alex-chen"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://onboardai:onboardai@localhost:5432/onboardai",
)


def positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except ValueError:
        return default
