"""Synthetic ISM tables: no downloaded observations or network dependency."""
from datetime import date, datetime, timezone
import pytest
from app.ingestion import import_ism as ism
from app import local_ism
from app.analytics import history, series_catalog, relationship_sources


def document(kind="manufacturing"):
    label = kind.capitalize()
    caption = "THE LAST 12 MONTHS" if kind == "manufacturing" else "SERVICES PMI<sup>\u00ae</sup> HISTORY"
    cells = [(date(2024, n, 1), float(n * 3)) for n in range(1, 13)]
    rows = "".join(f"<tr><td>{a:%b %Y}</td><td>{v}</td><td>{b:%b %Y}</td><td>{w}</td></tr>" for (a,v),(b,w) in zip(cells[6:],cells[:6]))
    return f'''<html><meta name="author" content="Institute for Supply Management"><script>{{"datePublished":"2025-01-03T10:00:00-05:00"}}</script>
      <h1>{label} PMI at 36; December 2024 ISM {label} PMI Report</h1>
      <section class="release-body"><p>The {label} PMI<sup>\u00ae</sup> registered 36 percent.</p><p>{caption}</p>
      <table><tr><td>Month</td><td>{label} PMI</td><td>Month</td><td>{label} PMI</td></tr>{rows}</table></section></html>'''


@pytest.mark.parametrize("kind", ["manufacturing", "services"])
def test_parse_both_history_structures(kind):
    result = ism.parse_report(document(kind), kind)
    assert result["series_id"] == ism.KINDS[kind]
    assert len(result["readings"]) == 12
    assert result["readings"][0] == (date(2024,1,1),3)
    assert result["readings"][-1] == (date(2024,12,1),36)
    assert result["published_at"].year == 2025


@pytest.mark.parametrize("change", [
    lambda s: s.replace("Institute for Supply Management", "Another publisher"),
    lambda s: s.replace("Dec 2024", "Nov 2024"),
    lambda s: s.replace("Dec 2024", "Dec 2025"),
    lambda s: s.replace("<td>36.0</td>", "<td>99</td>"),
    lambda s: s.replace("<td>36.0</td>", "<td>nan</td>"),
    lambda s: s.replace("<td>36.0</td>", "<td>101</td>"),
    lambda s: s.replace("THE LAST 12 MONTHS", "Other table"),
    lambda s: s.replace("<td>Jan 2024</td><td>3.0</td>", ""),
    lambda s: s.replace("Manufacturing", "Services"),
    lambda s: "<html>Access denied</html>",
])
def test_invalid_reports_are_rejected(change):
    with pytest.raises(ValueError):
        ism.parse_report(change(document()), "manufacturing")


def test_fetch_rejects_non_html_and_http_failure(monkeypatch):
    import httpx
    url = "https://www.prnewswire.com/news-releases/test.html"
    for code, content_type in [(200,"application/json"), (403,"text/html")]:
        monkeypatch.setattr(ism.httpx, "get", lambda *a, **k: httpx.Response(code, headers={"content-type":content_type}, text="{}", request=httpx.Request("GET",url)))
        with pytest.raises((ValueError, httpx.HTTPError)):
            ism.fetch_report(url,"services")


def test_local_catalog_and_raw_only_policy():
    for sid in local_ism.SERIES:
        meta = series_catalog.get_active_series(sid)
        assert meta["source"] == "ism" and meta["unit"] == "index"
        assert series_catalog.list_available_features(sid)["features"] == []
        relationship_sources.validate_source(sid,None)
        with pytest.raises(history.UnsupportedFeatureError):
            relationship_sources.validate_source(sid,"mom")


def test_idempotency_and_revision_store_without_overwriting(monkeypatch,tmp_path):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def execute(self,sql,params):
            assert "ON CONFLICT (series_id, raw_hash) DO NOTHING" in sql
            self.result = None if params[5] in stored else (len(stored)+1,)
            if self.result: stored[params[5]] = params
        def fetchone(self): return self.result
        def executemany(self,sql,rows): observations.extend(rows)
    class Connection:
        def cursor(self): return Cursor()
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass
    stored,observations = {},[]
    monkeypatch.setattr(ism,"RAW_ROOT",tmp_path / "data" / "raw" / "ism")
    monkeypatch.setattr(ism,"get_connection",Connection)
    report = ism.parse_report(document(),"manufacturing")
    assert ism.store_report(report,"https://example.test",b"first")
    assert not ism.store_report(report,"https://example.test",b"first")
    revised = {**report,"published_at":datetime(2025,2,3,tzinfo=timezone.utc),"readings":[(d,v+1) for d,v in report["readings"]]}
    assert ism.store_report(revised,"https://example.test",b"revision")
    older = {**report,"published_at":datetime(2025,1,2,tzinfo=timezone.utc)}
    assert ism.store_report(older,"https://example.test",b"older-imported-last")
    assert len(stored)==3 and len(observations)==36
    newest = max(stored.values(), key=lambda params: params[2])
    assert newest[2] == revised["published_at"]
    assert observations[12:24] == [(2,d,v) for d,v in revised["readings"]]
    # SQL selection orders by document publication, never import order.
    assert "d.published_at DESC, d.retrieved_at DESC" in local_ism.HISTORY_SQL
    assert "UPDATE" not in local_ism.HISTORY_SQL


def test_local_history_has_document_provenance_and_short_actual_coverage(monkeypatch):
    from tests.test_series_catalog import FakeConnection
    rows = [(date(2024,1,1), 12,datetime(2025,1,3,tzinfo=timezone.utc),"https://example.test",datetime(2025,2,3,tzinfo=timezone.utc),"a"*64)]
    monkeypatch.setattr(local_ism,"get_connection",lambda:FakeConnection(rows))
    result = history.load_series_history("ISM_SERVICES_PMI")
    assert result["coverage_start"] == date(2024,1,1)
    assert len(result["observations"]) == 1
    assert result["observations"][0]["raw_hash"] == "a"*64
    assert "document_published_at" in result["observations"][0]


def test_diffusion_index_blocks_ratio_indexing_and_preserves_pair_count(monkeypatch):
    from app.analytics import relationships as lab
    from tests.test_relationships import make_history
    def loader(sid,start,end):
        result = make_history(sid,"monthly",[(f"2024-{n:02}-01",float(n)) for n in range(1,13)])
        return {**result,"unit":"index"}
    monkeypatch.setattr(history,"load_series_history",loader)
    result = lab.compare_histories("ISM_MANUFACTURING_PMI","ISM_SERVICES_PMI")
    assert not result["indexing"]["available"]
    assert result["normalization_base_period"] is None
    assert result["comparisons"][0]["overlapping_observation_count"] == 12
    assert all(item["unit"] == "index" for item in result["indicators"])
