"""NSE F&O (futures + options) bhavcopy ingestion.

NSE publishes a daily F&O archive at
``https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{YYYYMMDD}_F_0000.csv.zip``
(UDiFF) and historically at
``https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{YYYY}/
{MMM}/fo{DDMMMYYYY}bhav.csv.zip`` (legacy, pre-2020-07-11).

Each row is one instrument-expiry pair on one trading day with OHLC,
settle price, open interest, and traded volume. We normalise both schemas
into a single shape and persist year-partitioned Parquet under
``DataPaths.eod_fno`` so the same DuckDB query pattern from
``oq_data.storage`` works for derivatives too.

Network calls are isolated behind the same injectable ``Fetcher`` used by
the equity pipeline so the suite stays offline.
"""

from __future__ import annotations

import io
import logging
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from oq_data.bhavcopy import UDIFF_CUTOVER, Fetcher, _default_fetcher
from oq_data.config import DataPaths, get_paths

logger = logging.getLogger(__name__)

_NORMALISED_COLUMNS = [
    "date",
    "instrument",
    "symbol",
    "expiry",
    "strike",
    "option_type",
    "open",
    "high",
    "low",
    "close",
    "settle",
    "volume",
    "value",
    "open_interest",
    "change_in_oi",
]


@dataclass(frozen=True, slots=True)
class FnoSource:
    """The full address of an F&O bhavcopy for a given date."""

    when: date
    url: str
    filename: str
    is_udiff: bool


def is_udiff_date(when: date) -> bool:
    return when >= UDIFF_CUTOVER


def build_url(when: date) -> FnoSource:
    """Build the canonical NSE F&O archive URL for ``when``."""
    if is_udiff_date(when):
        fname = f"BhavCopy_NSE_FO_0_0_0_{when:%Y%m%d}_F_0000.csv.zip"
        url = f"https://nsearchives.nseindia.com/content/fo/{fname}"
        return FnoSource(when=when, url=url, filename=fname, is_udiff=True)
    fname = f"fo{when.strftime('%d%b%Y').upper()}bhav.csv.zip"
    url = (
        "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/"
        f"{when:%Y}/{when.strftime('%b').upper()}/{fname}"
    )
    return FnoSource(when=when, url=url, filename=fname, is_udiff=False)


def _read_csv_from_zip(blob: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("zip archive contains no .csv member")
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh)


def _normalise_legacy(raw: pd.DataFrame, when: date) -> pd.DataFrame:
    raw = raw.rename(columns=lambda c: c.strip().upper())
    expiry = pd.to_datetime(raw["EXPIRY_DT"], format="%d-%b-%Y", errors="coerce").dt.normalize()
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "instrument": raw["INSTRUMENT"].astype(str).str.strip(),
            "symbol": raw["SYMBOL"].astype(str).str.strip(),
            "expiry": expiry,
            "strike": pd.to_numeric(raw.get("STRIKE_PR"), errors="coerce"),
            "option_type": raw.get("OPTION_TYP", pd.Series([pd.NA] * len(raw)))
            .astype("string")
            .str.strip(),
            "open": pd.to_numeric(raw["OPEN"], errors="coerce"),
            "high": pd.to_numeric(raw["HIGH"], errors="coerce"),
            "low": pd.to_numeric(raw["LOW"], errors="coerce"),
            "close": pd.to_numeric(raw["CLOSE"], errors="coerce"),
            "settle": pd.to_numeric(raw.get("SETTLE_PR"), errors="coerce"),
            "volume": pd.to_numeric(raw["CONTRACTS"], errors="coerce").astype("Int64"),
            "value": pd.to_numeric(raw["VAL_INLAKH"], errors="coerce") * 100_000.0,
            "open_interest": pd.to_numeric(raw["OPEN_INT"], errors="coerce").astype("Int64"),
            "change_in_oi": pd.to_numeric(raw["CHG_IN_OI"], errors="coerce").astype("Int64"),
        }
    )
    return df


def _normalise_udiff(raw: pd.DataFrame, when: date) -> pd.DataFrame:
    raw = raw.rename(columns=lambda c: c.strip())
    expiry = pd.to_datetime(raw["XpryDt"], errors="coerce").dt.normalize()
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "instrument": raw["FinInstrmTp"].astype(str).str.strip(),
            "symbol": raw["TckrSymb"].astype(str).str.strip(),
            "expiry": expiry,
            "strike": pd.to_numeric(raw.get("StrkPric"), errors="coerce"),
            "option_type": raw.get("OptnTp", pd.Series([pd.NA] * len(raw)))
            .astype("string")
            .str.strip(),
            "open": pd.to_numeric(raw["OpnPric"], errors="coerce"),
            "high": pd.to_numeric(raw["HghPric"], errors="coerce"),
            "low": pd.to_numeric(raw["LwPric"], errors="coerce"),
            "close": pd.to_numeric(raw["ClsPric"], errors="coerce"),
            "settle": pd.to_numeric(raw.get("SttlmPric"), errors="coerce"),
            "volume": pd.to_numeric(raw["TtlTradgVol"], errors="coerce").astype("Int64"),
            "value": pd.to_numeric(raw["TtlTrfVal"], errors="coerce"),
            "open_interest": pd.to_numeric(raw["OpnIntrst"], errors="coerce").astype("Int64"),
            "change_in_oi": pd.to_numeric(raw["ChngInOpnIntrst"], errors="coerce").astype("Int64"),
        }
    )
    return df


def parse_fno_blob(blob: bytes, when: date) -> pd.DataFrame:
    """Parse a downloaded F&O bhavcopy zip into the canonical schema."""
    raw = _read_csv_from_zip(blob) if blob[:2] == b"PK" else pd.read_csv(io.BytesIO(blob))
    upper_cols = {c.strip().upper() for c in raw.columns}
    is_udiff = "XPRYDT" in upper_cols or "TCKRSYMB" in upper_cols
    df = _normalise_udiff(raw, when) if is_udiff else _normalise_legacy(raw, when)
    return df[_NORMALISED_COLUMNS]


def _cache_dir(paths: DataPaths) -> Path:
    p = paths.raw / "fno"
    p.mkdir(parents=True, exist_ok=True)
    return p


def download_fno(
    when: date,
    paths: DataPaths | None = None,
    fetcher: Fetcher | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Download and parse the NSE F&O bhavcopy for ``when``."""
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
    return parse_fno_blob(blob, when)


def sync_range(
    start: date,
    end: date,
    paths: DataPaths | None = None,
    fetcher: Fetcher | None = None,
    on_missing: str = "skip",
) -> Iterable[date]:
    """Download every available F&O bhavcopy in ``[start, end]`` inclusive."""
    if end < start:
        raise ValueError("end must be >= start")
    paths = paths or get_paths()
    paths.ensure()
    cur = start
    one_day = timedelta(days=1)
    while cur <= end:
        if cur.weekday() < 5:
            try:
                download_fno(cur, paths=paths, fetcher=fetcher)
                yield cur
            except Exception as exc:
                if on_missing == "raise":
                    raise
                logger.info("fno bhavcopy unavailable for %s: %s", cur, exc)
        cur += one_day


def parse_filename_date(filename: str) -> date:
    if filename.startswith("BhavCopy_NSE_FO_"):
        token = filename.split("_")[6]
        return datetime.strptime(token, "%Y%m%d").date()
    if filename.startswith("fo") and filename.endswith("bhav.csv.zip"):
        token = filename[2:-12]
        return datetime.strptime(token, "%d%b%Y").date()
    raise ValueError(f"unrecognised fno filename: {filename}")


__all__ = [
    "FnoSource",
    "build_url",
    "download_fno",
    "is_udiff_date",
    "parse_filename_date",
    "parse_fno_blob",
    "sync_range",
]
