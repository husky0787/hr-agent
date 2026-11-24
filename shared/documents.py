"""Read the company documents exposed by the citation viewer."""

from shared.config import SEED_DATA_DIR

DOCUMENT_FILENAMES = frozenset({
    "employee-handbook.md",
    "benefits-guide.md",
    "it-setup.md",
    "onboarding-checklist.md",
})

DOCUMENT_TITLES = {
    "employee-handbook.md": "僱員手冊",
    "benefits-guide.md": "福利及開支報銷指南",
    "it-setup.md": "IT 設定及資訊保安指南",
    "onboarding-checklist.md": "首 30 天入職安排",
}


def list_documents() -> list[dict[str, str]]:
    return [{"filename": name, "title": title} for name, title in DOCUMENT_TITLES.items()
            if (SEED_DATA_DIR / name).is_file()]


def read_document(filename: str) -> str:
    if filename not in DOCUMENT_FILENAMES:
        raise FileNotFoundError(filename)
    path = (SEED_DATA_DIR / filename).resolve()
    if path.parent != SEED_DATA_DIR.resolve() or not path.is_file():
        raise FileNotFoundError(filename)
    return path.read_text(encoding="utf-8")
