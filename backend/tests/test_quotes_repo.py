import json

from app.data.quotes_repo import (
    load_quotes,
    quotes_meta,
    refresh_quotes,
)

CORPUS = [
    {"phrase": "Knowledge is power.", "author": "Francis Bacon"},
    {
        "phrase": "Imagination is more important than knowledge.",
        "author": "Albert Einstein",
    },
    {"phrase": "The unexamined life is not worth living.", "author": "Socrates"},
]


def test_refresh_writes_and_reports_added(tmp_path, monkeypatch):
    monkeypatch.setattr("app.data.quotes_repo.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.data.quotes_repo.QUOTES_FILE", tmp_path / "quotes.json")
    # estado previo: 2 de 3 frases
    (tmp_path / "quotes.json").write_text(json.dumps(CORPUS[:2]), encoding="utf-8")

    result = refresh_quotes(scraper=lambda: CORPUS)

    assert result["count"] == 3
    assert result["added"] == 1
    assert result["source"] == "https://quotes.toscrape.com"
    assert (tmp_path / "quotes.json").exists()
    assert len(load_quotes(tmp_path / "quotes.json")) == 3


def test_refresh_no_changes(tmp_path, monkeypatch):
    monkeypatch.setattr("app.data.quotes_repo.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.data.quotes_repo.QUOTES_FILE", tmp_path / "quotes.json")
    (tmp_path / "quotes.json").write_text(json.dumps(CORPUS), encoding="utf-8")
    result = refresh_quotes(scraper=lambda: CORPUS)
    assert result["added"] == 0


def test_refresh_filters_empty_items(tmp_path, monkeypatch):
    monkeypatch.setattr("app.data.quotes_repo.DATA_DIR", tmp_path)
    monkeypatch.setattr("app.data.quotes_repo.QUOTES_FILE", tmp_path / "quotes.json")
    result = refresh_quotes(
        scraper=lambda: (
            CORPUS + [{"phrase": "", "author": ""}, {"phrase": None, "author": "X"}]
        )
    )
    assert result["count"] == 3


def test_meta_shape():
    meta = quotes_meta()
    assert meta["source"] == "https://quotes.toscrape.com"
    assert meta["count"] >= 1
    assert "updated_at" in meta
    assert isinstance(meta["quotes"], list)
