"""Corporate-announcements feed ingestion.

NSE publishes a rolling JSON feed of corporate announcements at
``https://www.nseindia.com/api/corporate-announcements?index=equities``.
Each row carries the announcement timestamp, symbol, broad category, a
short subject line, and an attachment URL.

The canonical schema we persist is::

    date, symbol, category, subject, attachment

``date`` is the announcement business date (``date``-typed), suitable
for the same year-partitioned storage layout used by the EOD writers.

Network calls go through the same injectable ``Fetcher`` as the rest of
the pipeline so the suite stays offline.
"""

from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from oq_data.bhavcopy import Fetcher, _default_fetcher
from oq_data.config import DataPaths, get_paths
from oq_data.storage import write_partitioned

logger = logging.getLogger(__name__)

_NORMALISED_COLUMNS = ["date", "symbol", "category", "subject", "attachment"]


@dataclass(frozen=True, slots=True)
class AnnouncementsSource:
    when: date
    url: str
    filename: str


def build_url(when: date) -> AnnouncementsSource:
    fname = f"announcements_{when:%Y%m%d}.json"
    url = (
        "https://www.nseindia.com/api/corporate-announcements"
        f"?index=equities&from_date={when:%d-%m-%Y}&to_date={when:%d-%m-%Y}"
    )
    return AnnouncementsSource(when=when, url=url, filename=fname)


def _pick(row: dict, *keys: str) -> object:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return ""


def parse_announcements_blob(blob: bytes, when: date) -> pd.DataFrame:
    text = blob.decode("utf-8-sig", errors="ignore").lstrip()
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("data", data.get("rows", []))
    else:
        rows = pd.read_csv(io.BytesIO(blob)).to_dict("records")
    if not rows:
        return pd.DataFrame(columns=_NORMALISED_COLUMNS)
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "symbol": [str(_pick(r, "symbol", "Symbol", "SYMBOL")).strip() for r in rows],
            "category": [
                str(_pick(r, "category", "Category", "broadcastsubject")).strip() for r in rows
            ],
            "subject": [
                str(_pick(r, "subject", "Subject", "desc", "Description")).strip() for r in rows
            ],
            "attachment": [
                str(_pick(r, "attchmntFile", "attachment", "attachmentUrl")).strip() for r in rows
            ],
        }
    )
    df = df[df["symbol"] != ""].reset_index(drop=True)
    return df[_NORMALISED_COLUMNS]


def _cache_dir(paths: DataPaths):
    p = paths.raw / "announcements"
    p.mkdir(parents=True, exist_ok=True)
    return p


def download_announcements(
    when: date,
    paths: DataPaths | None = None,
    fetcher: Fetcher | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    paths = paths or get_paths()
    paths.ensure()
    src = build_url(when)
    cache_path = _cache_dir(paths) / src.filename
    fetch = fetcher or _default_fetcher
    if use_cache and cache_path.exists():
        blob = cache_path.read_bytes()
    else:
        blob = fetch(src.url)
        cache_path.write_bytes(blob)
    return parse_announcements_blob(blob, when)


def write_announcements(df: pd.DataFrame, paths: DataPaths | None = None) -> int:
    paths = paths or get_paths()
    paths.ensure()
    keys = ["date", "symbol", "subject"]
    return write_partitioned(df, paths.announcements, keys)


def read_announcements(
    symbols: str | Iterable[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
    paths: DataPaths | None = None,
) -> pd.DataFrame:
    paths = paths or get_paths()
    parts = sorted(paths.announcements.glob("year=*/data.parquet"))
    if not parts:
        return pd.DataFrame(columns=_NORMALISED_COLUMNS)
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    if symbols is not None:
        syms = {symbols} if isinstance(symbols, str) else set(symbols)
        df = df[df["symbol"].isin(syms)]
    if start is not None:
        df = df[df["date"] >= pd.to_datetime(start)]
    if end is not None:
        df = df[df["date"] <= pd.to_datetime(end)]
    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def sync_range(
    start: date,
    end: date,
    paths: DataPaths | None = None,
    fetcher: Fetcher | None = None,
    on_missing: str = "skip",
) -> Iterable[date]:
    if end < start:
        raise ValueError("end must be >= start")
    paths = paths or get_paths()
    paths.ensure()
    cur = start
    one_day = timedelta(days=1)
    while cur <= end:
        if cur.weekday() < 5:
            try:
                download_announcements(cur, paths=paths, fetcher=fetcher)
                yield cur
            except Exception as exc:
                if on_missing == "raise":
                    raise
                logger.info("announcements feed unavailable for %s: %s", cur, exc)
        cur += one_day


__all__ = [
    "AnnouncementsSource",
    "build_url",
    "download_announcements",
    "parse_announcements_blob",
    "read_announcements",
    "sync_range",
    "write_announcements",
]
