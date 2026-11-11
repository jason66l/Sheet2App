import pytest


@pytest.fixture(autouse=True)
def _no_proposal_cache(monkeypatch, tmp_path):
    """Tests never read or write the real .cache/ (it could hold a live AI answer)."""
    monkeypatch.setenv("PROPOSAL_CACHE", "0")
    monkeypatch.setenv("PROPOSAL_CACHE_DIR", str(tmp_path / "cache"))
