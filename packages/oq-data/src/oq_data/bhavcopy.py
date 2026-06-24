"""NSE equity Bhavcopy ingestion.

NSE publishes one zipped CSV per trading day with all listed cash-market
instruments and their OHLCV. Two formats are in active circulation:

* **Legacy** (until ~July 2020): ``cm{DDMMMYYYY}bhav.csv.zip`` with the
  classic ``SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,...`` schema.
* **UDiFF** (from ~July 2020 onward): ``BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}
  _F_0000.csv.zip`` with the longer ``TradDt,BizDt,Sgmt,Src,FinInstrmTp,
  FinInstrmId,ISIN,TckrSymb,SctySrs,...`` schema.

This module exposes URL builders, format-detecting parsers, and a single
:func:`download_bhavcopy` entry point that retries, resumes from cache,
and returns a normalised :class:`pandas.DataFrame`.

Network calls are isolated behind an injectable ``fetcher`` callable so
tests run fully offline against the fixtures under ``tests/fixtures``.
"""

from __future__ import annotations

import io
import logging
import time
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd

from oq_data.config import DataPaths, get_paths

logger = logging.getLogger(__name__)

UDIFF_CUTOVER = date(2020, 7, 11)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

Fetcher = Callable[[str], bytes]

_NORMALISED_COLUMNS = [
    "date",
    "symbol",
    "isin",
    "series",
    "open",
    "high",
    "low",
    "close",
    "prev_close",
    "volume",
    "value",
    "trades",
]


@dataclass(frozen=True, slots=True)
class BhavcopySource:
    """The full address of a bhavcopy for a given date."""

    when: date
    url: str
    filename: str
    is_udiff: bool


def is_udiff_date(when: date) -> bool:
    """Return True if NSE was publishing the UDiFF schema on ``when``."""
    return when >= UDIFF_CUTOVER


def build_url(when: date) -> BhavcopySource:
    """Build the canonical NSE archive URL for the bhavcopy on ``when``."""
    if is_udiff_date(when):
        fname = f"BhavCopy_NSE_CM_0_0_0_{when:%Y%m%d}_F_0000.csv.zip"
        url = f"https://nsearchives.nseindia.com/content/cm/{fname}"
        return BhavcopySource(when=when, url=url, filename=fname, is_udiff=True)
    fname = f"cm{when.strftime('%d%b%Y').upper()}bhav.csv.zip"
    url = (
        "https://nsearchives.nseindia.com/content/historical/EQUITIES/"
        f"{when:%Y}/{when.strftime('%b').upper()}/{fname}"
    )
    return BhavcopySource(when=when, url=url, filename=fname, is_udiff=False)


def _default_fetcher(url: str, timeout: float = 30.0, retries: int = 3) -> bytes:
    """HTTP GET with retry and NSE-friendly headers. Raises on final failure."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(
                headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.content
        except httpx.HTTPError as exc:
            last_exc = exc
            logger.warning("bhavcopy fetch failed (attempt %d/%d): %s", attempt, retries, exc)
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"failed to fetch {url} after {retries} attempts") from last_exc


def _read_csv_from_zip(blob: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("zip archive contains no .csv member")
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh)


def _normalise_legacy(raw: pd.DataFrame, when: date) -> pd.DataFrame:
    raw = raw.rename(columns=lambda c: c.strip().upper())
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "symbol": raw["SYMBOL"].astype(str).str.strip(),
            "isin": raw.get("ISIN", pd.Series([pd.NA] * len(raw))).astype("string").str.strip(),
            "series": raw["SERIES"].astype(str).str.strip(),
            "open": pd.to_numeric(raw["OPEN"], errors="coerce"),
            "high": pd.to_numeric(raw["HIGH"], errors="coerce"),
            "low": pd.to_numeric(raw["LOW"], errors="coerce"),
            "close": pd.to_numeric(raw["CLOSE"], errors="coerce"),
            "prev_close": pd.to_numeric(raw["PREVCLOSE"], errors="coerce"),
            "volume": pd.to_numeric(raw["TOTTRDQTY"], errors="coerce").astype("Int64"),
            "value": pd.to_numeric(raw["TOTTRDVAL"], errors="coerce"),
            "trades": pd.to_numeric(raw.get("TOTALTRADES", pd.NA), errors="coerce").astype("Int64"),
        }
    )
    return df


def _normalise_udiff(raw: pd.DataFrame, when: date) -> pd.DataFrame:
    raw = raw.rename(columns=lambda c: c.strip())
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(when),
            "symbol": raw["TckrSymb"].astype(str).str.strip(),
            "isin": raw["ISIN"].astype("string").str.strip(),
            "series": raw["SctySrs"].astype(str).str.strip(),
            "open": pd.to_numeric(raw["OpnPric"], errors="coerce"),
            "high": pd.to_numeric(raw["HghPric"], errors="coerce"),
            "low": pd.to_numeric(raw["LwPric"], errors="coerce"),
            "close": pd.to_numeric(raw["ClsPric"], errors="coerce"),
            "prev_close": pd.to_numeric(raw["PrvsClsgPric"], errors="coerce"),
            "volume": pd.to_numeric(raw["TtlTradgVol"], errors="coerce").astype("Int64"),
            "value": pd.to_numeric(raw["TtlTrfVal"], errors="coerce"),
            "trades": pd.to_numeric(raw["TtlNbOfTxsExctd"], errors="coerce").astype("Int64"),
        }
    )
    fininstrm = raw.get("FinInstrmTp")
    if fininstrm is not None:
        df = df[fininstrm.astype(str).str.upper().isin({"STK", "EQ"})].reset_index(drop=True)
    return df


def parse_bhavcopy_blob(blob: bytes, when: date) -> pd.DataFrame:
    """Parse a downloaded bhavcopy zip (or raw csv) into the canonical schema.

    The schema returned, regardless of input format, is exactly:
    ``date, symbol, isin, series, open, high, low, close, prev_close,
    volume, value, trades``.
    """
    raw = _read_csv_from_zip(blob) if blob[:2] == b"PK" else pd.read_csv(io.BytesIO(blob))
    upper_cols = {c.strip().upper() for c in raw.columns}
    is_udiff = "TCKRSYMB" in upper_cols
    df = _normalise_udiff(raw, when) if is_udiff else _normalise_legacy(raw, when)
    return df[_NORMALISED_COLUMNS]


def download_bhavcopy(
    when: date,
    paths: DataPaths | None = None,
    fetcher: Fetcher | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Download and parse the NSE equity bhavcopy for ``when``.

    The raw zip is cached under ``paths.bhavcopy`` so reruns are offline.
    Pass ``fetcher`` to substitute a callable (used by tests) or to swap
    in your own retry/auth wrapper.
    """
    paths = paths or get_paths()
    paths.ensure()
    src = build_url(when)
    cache_path = paths.bhavcopy / src.filename
    fetch = fetcher or _default_fetcher

    if use_cache and cache_path.exists():
        blob = cache_path.read_bytes()
    else:
        blob = fetch(src.url)
        cache_path.write_bytes(blob)
    return parse_bhavcopy_blob(blob, when)


def sync_range(
    start: date,
    end: date,
    paths: DataPaths | None = None,
    fetcher: Fetcher | None = None,
    on_missing: str = "skip",
) -> Iterable[date]:
    """Download every available bhavcopy in ``[start, end]`` inclusive.

    Weekends are always skipped. NSE holidays show up as 404s; with
    ``on_missing='skip'`` (default) they are silently passed over. With
    ``on_missing='raise'`` the first 404 aborts the run.
    Yields the dates that were successfully ingested.
    """
    if end < start:
        raise ValueError("end must be >= start")
    paths = paths or get_paths()
    paths.ensure()
    cur = start
    one_day = timedelta(days=1)
    while cur <= end:
        if cur.weekday() < 5:
            try:
                download_bhavcopy(cur, paths=paths, fetcher=fetcher)
                yield cur
            except Exception as exc:
                if on_missing == "raise":
                    raise
                logger.info("bhavcopy unavailable for %s: %s", cur, exc)
        cur += one_day


def parse_filename_date(filename: str) -> date:
    """Recover the trading date from a cached bhavcopy filename."""
    if filename.startswith("BhavCopy_NSE_CM_"):
        token = filename.split("_")[6]
        return datetime.strptime(token, "%Y%m%d").date()
    if filename.startswith("cm") and filename.endswith("bhav.csv.zip"):
        token = filename[2:-12]
        return datetime.strptime(token, "%d%b%Y").date()
    raise ValueError(f"unrecognised bhavcopy filename: {filename}")


def iter_cached(paths: DataPaths) -> Iterable[Path]:
    """Yield every cached bhavcopy archive under ``paths.bhavcopy``."""
    if not paths.bhavcopy.exists():
        return
    for entry in sorted(paths.bhavcopy.iterdir()):
        if entry.is_file() and entry.suffix == ".zip":
            yield entry


__all__ = [
    "DEFAULT_HEADERS",
    "UDIFF_CUTOVER",
    "BhavcopySource",
    "Fetcher",
    "build_url",
    "download_bhavcopy",
    "is_udiff_date",
    "iter_cached",
    "parse_bhavcopy_blob",
    "parse_filename_date",
    "sync_range",
]
