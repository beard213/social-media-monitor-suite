from datetime import datetime

from app.adapters.http_authorized import parse_datetime


def test_parse_iso_datetime():
    value = parse_datetime("2026-07-15T10:00:00+08:00")
    assert isinstance(value, datetime)
    assert value.tzinfo is not None


def test_parse_unix_datetime():
    value = parse_datetime(1_700_000_000)
    assert isinstance(value, datetime)
    assert value.tzinfo is not None


def test_demo_relations_are_normalized():
    from app.adapters.demo import DemoAdapter

    rows = DemoAdapter().relations('author-1', limit=10)
    assert rows
    assert rows[0]['relation_type'] in {'friend', 'frequent_commenter'}
