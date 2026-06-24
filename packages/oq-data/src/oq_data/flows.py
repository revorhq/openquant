"""FII/DII cash-market flows ingestion.

NSE publishes a daily JSON feed at
``https://www.nseindia.com/api/fiidiiTradeReact`` (also exposed as a CSV
on their archives) with the day's FII and DII gross buy / gross sell /
net activity in the cash segment.

The canonical schema we persist is::

    date, category, buy_value, sell_value, net_value

where ``category`` is one of ``FII``, ``DII``.

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

_NORMALISED_COLUMNS = ["date", "category", "buy_value", "sell_value", "net_value"]


@dataclass(frozen=True, slots=True)
class FlowsSource:
    when: date
    url: str
    filename: str


def build_url(when: date) -> FlowsSource:
    fname = f"fii_dii_{when:%Y%m%d}.json"
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    return FlowsSource(when=when, url=url, filename=fname)


def _coerce_category(value: object) -> str:
    s = str(value).strip().upper()
    if "FII" in s or "FPI" in s or "FOREIGN" in s:
        return "FII"
    if "DII" in s or "DOMESTIC" in s:
        return "DII"
    return s


def parse_flows_blob(blob: bytes, when: date) -> pd.DataFrame:
    text = blob.decode("utf-8-sig", errors="ignore").lstrip()
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("data", [])
        raw = pd.DataFrame(rows)
    else:
        raw = pd.read_csv(io.BytesIO(blob))
    raw = raw.rename(columns=lambda c: str(c).strip())
    lookup = {c.lower(): c for c in raw.columns}

    def pick(*candidates: str) -> str | None:
        for cand in candidates:
            if cand.lower() in lookup:
                return lookup[cand.lower()]
        return None

    cat_col = pick("category", "Category", "type")
    buy_col = pick("buyValue", "buy_value", "grossPurchase", "Gross_Purchase")
    sell_col = pick("sellValue", "sell_value", "grossSales", "Gross_Sales")
    net_col = pick("netValue", "net_value", "netInvestment", "Net_Investment")
    if cat_col is None or buy_col is None or sell_col is None:
        raise ValueError("flows payload missing required columns")
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "category": raw[cat_col].map(_coerce_category),
            "buy_value": pd.to_numeric(raw[buy_col], errors="coerce"),
            "sell_value": pd.to_numeric(raw[sell_col], errors="coerce"),
            "net_value": pd.to_numeric(raw[net_col] if net_col else 0, errors="coerce"),
        }
    )
    if net_col is None:
        df["net_value"] = df["buy_value"] - df["sell_value"]
    df = df[df["category"].isin({"FII", "DII"})].reset_index(drop=True)
    return df[_NORMALISED_COLUMNS]


def _cache_dir(paths: DataPaths):
    p = paths.raw / "fii_dii"
    p.mkdir(parents=True, exist_ok=True)
    return p


def download_flows(
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
    return parse_flows_blob(blob, when)


def write_flows(df: pd.DataFrame, paths: DataPaths | None = None) -> int:
    paths = paths or get_paths()
    paths.ensure()
    return write_partitioned(df, paths.fii_dii, ["date", "category"])


def read_flows(
    category: str | Iterable[str] | None = None,
    start: date | str | None = None,
    end: date | str | None = None,
    paths: DataPaths | None = None,
) -> pd.DataFrame:
    paths = paths or get_paths()
    parts = sorted(paths.fii_dii.glob("year=*/data.parquet"))
    if not parts:
        return pd.DataFrame(columns=_NORMALISED_COLUMNS)
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    if category is not None:
        cats = {category} if isinstance(category, str) else set(category)
        df = df[df["category"].isin(cats)]
    if start is not None:
        df = df[df["date"] >= pd.to_datetime(start)]
    if end is not None:
        df = df[df["date"] <= pd.to_datetime(end)]
    return df.sort_values(["date", "category"]).reset_index(drop=True)


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
                download_flows(cur, paths=paths, fetcher=fetcher)
                yield cur
            except Exception as exc:
                if on_missing == "raise":
                    raise
                logger.info("flows feed unavailable for %s: %s", cur, exc)
        cur += one_day


__all__ = [
    "FlowsSource",
    "build_url",
    "download_flows",
    "parse_flows_blob",
    "read_flows",
    "sync_range",
    "write_flows",
]
