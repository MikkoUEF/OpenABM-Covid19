from pathlib import Path

import pandas as pd
import pytest

from extensions.scenario_api.timeline import (
    TimelineEvent,
    filter_timeline_events,
    load_timeline_events_from_processed,
    timeline_events_to_table,
)
from extensions.scenario_api.timeline_sources import (
    OXCGRT_FALLBACK_CSV_URLS,
    fetch_oxcgrt_finland_raw,
    download_and_save_oxcgrt_finland_timeline,
    load_processed_timeline_events_table,
    load_timeline_raw_snapshot,
    process_oxcgrt_finland_raw_to_events,
    save_processed_timeline_events,
    save_timeline_raw_snapshot,
)


RAW_SAMPLE = """CountryName,CountryCode,Date,C1M,C2M,C3M,C4M,C5M,C6M,C7M,C8EV,H1,H2,H3,H6M,H7,H8M
Finland,FIN,20200101,0,0,0,0,0,0,0,0,0,0,0,0,0,0
Finland,FIN,20200316,3,2,2,4,1,2,1,3,2,2,2,2,0,1
Finland,FIN,20210110,2,2,2,3,1,1,1,2,2,2,2,2,1,1
Sweden,SWE,20200316,1,1,1,1,1,1,1,1,1,1,1,1,1,1
"""


def test_process_oxcgrt_finland_raw_to_events_normalizes_long_table():
    table = process_oxcgrt_finland_raw_to_events(RAW_SAMPLE, start_date="2020-01-01", end_date="2022-12-31")
    assert set(["date", "source", "region_level", "region", "event_type", "value", "notes"]).issubset(
        table.columns
    )
    assert table["source"].unique().tolist() == ["OxCGRT"]
    assert table["region_level"].unique().tolist() == ["country"]
    assert table["region"].unique().tolist() == ["Finland"]
    assert table["date"].min().isoformat() == "2020-01-01"
    assert table["date"].max().isoformat() == "2021-01-10"
    assert "school_closing" in table["event_type"].unique().tolist()
    assert "facial_coverings" in table["event_type"].unique().tolist()


def test_process_oxcgrt_finland_raw_to_events_rejects_missing_columns():
    bad = "CountryCode,Date,C1M\nFIN,20200101,1\n"
    with pytest.raises(ValueError, match="Missing expected OxCGRT columns"):
        process_oxcgrt_finland_raw_to_events(bad)


def test_process_oxcgrt_finland_raw_to_events_rejects_empty_finland_subset():
    no_finland = RAW_SAMPLE.replace("FIN", "XXX").replace("Finland", "Unknown")
    with pytest.raises(RuntimeError, match="Finland subset is empty"):
        process_oxcgrt_finland_raw_to_events(no_finland)


def test_timeline_raw_snapshot_roundtrip(tmp_path: Path):
    raw_path = tmp_path / "raw" / "oxcgrt.csv"
    save_timeline_raw_snapshot(RAW_SAMPLE, raw_path)
    loaded = load_timeline_raw_snapshot(raw_path)
    assert loaded == RAW_SAMPLE


def test_processed_timeline_save_load_and_event_helpers(tmp_path: Path):
    table = process_oxcgrt_finland_raw_to_events(RAW_SAMPLE)
    processed_path = tmp_path / "processed" / "timeline.csv"
    save_processed_timeline_events(table, processed_path)

    loaded = load_processed_timeline_events_table(processed_path)
    events = load_timeline_events_from_processed(processed_path)

    assert not loaded.empty
    assert isinstance(events[0], TimelineEvent)

    filtered = filter_timeline_events(events, event_type="facial_coverings")
    assert len(filtered) > 0
    assert all(e.event_type == "facial_coverings" for e in filtered)

    back = timeline_events_to_table(events)
    assert not back.empty


def test_download_and_save_oxcgrt_finland_timeline_with_mock(monkeypatch, tmp_path: Path):
    from extensions.scenario_api import timeline_sources

    monkeypatch.setattr(timeline_sources, "fetch_oxcgrt_finland_raw", lambda url=timeline_sources.OXCGRT_COMPACT_CSV_URL: RAW_SAMPLE)

    raw = tmp_path / "raw" / "oxcgrt.csv"
    processed = tmp_path / "processed" / "timeline.csv"

    raw_path, processed_path = download_and_save_oxcgrt_finland_timeline(
        raw_output_path=raw,
        processed_output_path=processed,
        start_date="2020-01-01",
        end_date="2022-12-31",
    )

    assert Path(raw_path).exists()
    assert Path(processed_path).exists()
    frame = pd.read_csv(processed_path)
    assert not frame.empty


def test_process_oxcgrt_finland_raw_to_events_accepts_prefixed_columns_and_jurisdiction():
    raw_prefixed = """CountryName,CountryCode,Jurisdiction,Date,C1M_School closing,C2M_Workplace closing,C3M_Cancel public events,C4M_Restrictions on gatherings,C5M_Close public transport,C6M_Stay at home requirements,C7M_Restrictions on internal movement,C8EV_International travel controls,H1_Public information campaigns,H2_Testing policy,H3_Contact tracing,H6M_Facial Coverings,H7_Vaccination policy,H8M_Protection of elderly people
Finland,FIN,NAT_TOTAL,20200316,3,2,2,4,1,2,1,3,2,2,2,2,0,1
Finland,FIN,STATE_TOTAL,20200316,9,9,9,9,9,9,9,9,9,9,9,9,9,9
"""
    table = process_oxcgrt_finland_raw_to_events(raw_prefixed)
    assert not table.empty
    assert table["date"].nunique() == 1
    assert table["event_type"].nunique() == 14
    # Ensure NAT_TOTAL row was used, not STATE_TOTAL.
    assert table.loc[table["event_type"] == "school_closing", "value"].iloc[0] == 3


def test_fetch_oxcgrt_finland_raw_uses_fallback_urls(monkeypatch):
    from extensions.scenario_api import timeline_sources

    class _Resp:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self._body

    calls = {"count": 0}

    def _fake_urlopen(request, timeout=60):
        calls["count"] += 1
        target = request.full_url
        if target == OXCGRT_FALLBACK_CSV_URLS[0]:
            raise timeline_sources.HTTPError(target, 404, "Not Found", hdrs=None, fp=None)
        return _Resp(RAW_SAMPLE.encode("utf-8"))

    monkeypatch.setattr(timeline_sources, "urlopen", _fake_urlopen)

    raw = fetch_oxcgrt_finland_raw(url=OXCGRT_FALLBACK_CSV_URLS[0], timeout=1)
    assert "CountryName,CountryCode,Date" in raw
    assert calls["count"] >= 2
