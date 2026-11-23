"""Read the company documents exposed by the citation viewer."""

from shared.config import SEED_DATA_DIR

DOCUMENT_FILENAMES = frozenset({
    "employee-handbook.md",
    "benefits-guide.md",
    "it-setup.md",
    "onboarding-checklist.md",
})


def read_document(filename: str) -> str:
    if filename not in DOCUMENT_FILENAMES:
        raise FileNotFoundError(filename)
    path = (SEED_DATA_DIR / filename).resolve()
    if path.parent != SEED_DATA_DIR.resolve() or not path.is_file():
        raise FileNotFoundError(filename)
    return path.read_text(encoding="utf-8")
