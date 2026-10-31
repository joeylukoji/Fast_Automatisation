import pytest

from app import store


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Chaque test utilise sa propre base SQLite et un environnement LLM vierge."""
    for var in ("KERNEL_LLM_LOCAL", "KERNEL_LLM_MOCK", "KERNEL_LLM_FALLBACK", "KERNEL_LLM_BASE_URL", "KERNEL_LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    store.reset(str(tmp_path / "test.db"))
    yield
    store.reset()
