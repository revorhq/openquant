"""NSE delivery-percentage ingestion.

NSE publishes a daily ``Sec_Bhavdata_Full_DDMMYYYY.csv`` file under
``https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{DDMMYYYY}.csv``
that exposes per-symbol delivery quantities and delivery percentages.

The canonical schema we persist is::

    date, symbol, series, delivery_qty, delivery_pct, traded_qty

Network calls go through the same injectable ``Fetcher`` as the equity
bhavcopy pipeline so the suite stays offline.
"""

from __future__ import annotations

import io
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from oq_data.bhavcopy import Fetcher, _default_fetcher
from oq_data.config import DataPaths, get_paths
from oq_data.storage import write_partitioned

logger = logging.getLogger(__name__)

_NORMALISED_COLUMNS = [
    "date",
    "symbol",
    "series",
    "traded_qty",
    "delivery_qty",
    "delivery_pct",
]


@dataclass(frozen=True, slots=True)
class DeliverySource:
    when: date
    url: str
    filename: str


def build_url(when: date) -> DeliverySource:
    fname = f"sec_bhavdata_full_{when:%d%m%Y}.csv"
    url = f"https://nsearchives.nseindia.com/products/content/{fname}"
    return DeliverySource(when=when, url=url, filename=fname)


def parse_delivery_blob(blob: bytes, when: date) -> pd.DataFrame:
    raw = pd.read_csv(io.BytesIO(blob))
    raw = raw.rename(columns=lambda c: c.strip().upper())
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "symbol": raw["SYMBOL"].astype(str).str.strip(),
            "series": raw["SERIES"].astype(str).str.strip(),
            "traded_qty": pd.to_numeric(raw["TTL_TRD_QNTY"], errors="coerce").astype("Int64"),
            "delivery_qty": pd.to_numeric(raw["DELIV_QTY"], errors="coerce").astype("Int64"),
            "delivery_pct": pd.to_numeric(raw["DELIV_PER"], errors="coerce"),
        }
    )
    return df[_NORMALISED_COLUMNS]


def _cache_dir(paths: DataPaths):
    p = paths.raw / "delivery"
    p.mkdir(parents=True, exist_ok=True)
    return p


def download_delivery(
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
    return parse_delivery_blob(blob, when)


def write_delivery(df: pd.DataFrame, paths: DataPaths | None = None) -> int:
    paths = paths or get_paths()
    paths.ensure()
    return write_partitioned(df, paths.delivery, ["date", "symbol", "series"])


def read_delivery(
    symbols: str | Iterable[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
    paths: DataPaths | None = None,
) -> pd.DataFrame:
    paths = paths or get_paths()
    parts = sorted(paths.delivery.glob("year=*/data.parquet"))
    if not parts:
        return pd.DataFrame(columns=_NORMALISED_COLUMNS)
    frames = [pd.read_parquet(p) for p in parts]
    df = pd.concat(frames, ignore_index=True)
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
                download_delivery(cur, paths=paths, fetcher=fetcher)
                yield cur
            except Exception as exc:
                if on_missing == "raise":
                    raise
                logger.info("delivery file unavailable for %s: %s", cur, exc)
        cur += one_day


__all__ = [
    "DeliverySource",
    "build_url",
    "download_delivery",
    "parse_delivery_blob",
    "read_delivery",
    "sync_range",
    "write_delivery",
]
