"""``oq`` command-line entrypoint.

Subcommands:

* ``oq sync --start YYYY-MM-DD --end YYYY-MM-DD`` — download every
  bhavcopy in the range and write to the Parquet store.
* ``oq universe INDEX --date YYYY-MM-DD`` — print the PIT membership
  set for the given index on that date.
* ``oq coverage`` — show per-year row and trading-day counts.
* ``oq prices SYMBOL [--start ...] [--end ...]`` — print adjusted EOD
  prices to stdout (CSV).
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import click
import pandas as pd

from oq_data import announcements, api, bhavcopy, delivery, flows, fno, storage
from oq_data.config import get_paths


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--data-dir",
    "data_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override the OpenQuant data directory.",
)
@click.pass_context
def main(ctx: click.Context, data_dir: Path | None) -> None:
    """OpenQuant India — honest, open source quant infrastructure."""
    ctx.ensure_object(dict)
    ctx.obj["paths"] = get_paths(data_dir)


@main.command()
@click.option(
    "--start", "start", type=str, required=False, help="YYYY-MM-DD (default: 30 days back)"
)
@click.option("--end", "end", type=str, required=False, help="YYYY-MM-DD (default: today)")
@click.option("--quick", is_flag=True, help="Sync the last 7 trading days only.")
@click.pass_context
def sync(ctx: click.Context, start: str | None, end: str | None, quick: bool) -> None:
    """Download NSE bhavcopies in [start, end] and write to the Parquet store."""
    paths = ctx.obj["paths"]
    today = date.today()
    if quick:
        end_d = today
        start_d = today - timedelta(days=10)
    else:
        end_d = _parse_date(end) if end else today
        start_d = _parse_date(start) if start else (end_d - timedelta(days=30))

    click.echo(f"[oq] syncing bhavcopies {start_d} -> {end_d} into {paths.eod_equity}")
    written = 0
    for when in bhavcopy.sync_range(start_d, end_d, paths=paths):
        df = bhavcopy.download_bhavcopy(when, paths=paths)
        rows = storage.write_eod(df, paths=paths)
        written += rows
        click.echo(f"  {when}  {rows:>6d} rows")
    click.echo(f"[oq] done. {written} total rows written.")


@main.command()
@click.argument("index_name")
@click.option("--date", "as_of", type=str, required=True, help="YYYY-MM-DD")
@click.pass_context
def universe(ctx: click.Context, index_name: str, as_of: str) -> None:
    """Print the point-in-time members of INDEX as of --date."""
    paths = ctx.obj["paths"]
    members = api.universe(index_name, as_of, paths=paths)
    if not members:
        click.echo(f"[oq] no members found for {index_name} on {as_of}", err=True)
        sys.exit(1)
    for sym in members:
        click.echo(sym)


@main.command()
@click.pass_context
def coverage(ctx: click.Context) -> None:
    """Per-year row and trading-day counts for the EOD dataset."""
    paths = ctx.obj["paths"]
    df = storage.coverage(paths=paths)
    if df.empty:
        click.echo("[oq] no data ingested yet; run `oq sync` first.", err=True)
        sys.exit(1)
    click.echo(df.to_string(index=False))


@main.command()
@click.argument("symbol")
@click.option("--start", "start", type=str, required=False, help="YYYY-MM-DD")
@click.option("--end", "end", type=str, required=False, help="YYYY-MM-DD")
@click.option(
    "--unadjusted",
    is_flag=True,
    default=False,
    help="Return raw (unadjusted) prices.",
)
@click.pass_context
def prices(
    ctx: click.Context,
    symbol: str,
    start: str | None,
    end: str | None,
    unadjusted: bool,
) -> None:
    """Print adjusted EOD prices for SYMBOL as CSV to stdout."""
    paths = ctx.obj["paths"]
    df = api.prices(
        symbol,
        start=_parse_date(start) if start else None,
        end=_parse_date(end) if end else None,
        adjusted=not unadjusted,
        paths=paths,
    )
    if df.empty:
        click.echo(f"[oq] no rows for {symbol}", err=True)
        sys.exit(1)
    pd.options.display.max_rows = None
    click.echo(df.to_csv(index=False))


@main.command("sync-fno")
@click.option("--start", "start", type=str, required=False)
@click.option("--end", "end", type=str, required=False)
@click.option("--quick", is_flag=True, help="Sync the last 10 calendar days only.")
@click.pass_context
def sync_fno(ctx: click.Context, start: str | None, end: str | None, quick: bool) -> None:
    """Download NSE F&O bhavcopies and write to the Parquet store."""
    paths = ctx.obj["paths"]
    today = date.today()
    if quick:
        end_d, start_d = today, today - timedelta(days=10)
    else:
        end_d = _parse_date(end) if end else today
        start_d = _parse_date(start) if start else (end_d - timedelta(days=30))
    click.echo(f"[oq] syncing fno bhavcopies {start_d} -> {end_d} into {paths.eod_fno}")
    written = 0
    for when in fno.sync_range(start_d, end_d, paths=paths):
        df = fno.download_fno(when, paths=paths)
        rows = storage.write_fno(df, paths=paths)
        written += rows
        click.echo(f"  {when}  {rows:>6d} rows")
    click.echo(f"[oq] done. {written} total fno rows written.")


@main.command("sync-delivery")
@click.option("--start", "start", type=str, required=False)
@click.option("--end", "end", type=str, required=False)
@click.option("--quick", is_flag=True)
@click.pass_context
def sync_delivery(ctx: click.Context, start: str | None, end: str | None, quick: bool) -> None:
    """Download NSE delivery-% files and write to the Parquet store."""
    paths = ctx.obj["paths"]
    today = date.today()
    if quick:
        end_d, start_d = today, today - timedelta(days=10)
    else:
        end_d = _parse_date(end) if end else today
        start_d = _parse_date(start) if start else (end_d - timedelta(days=30))
    click.echo(f"[oq] syncing delivery {start_d} -> {end_d} into {paths.delivery}")
    written = 0
    for when in delivery.sync_range(start_d, end_d, paths=paths):
        df = delivery.download_delivery(when, paths=paths)
        rows = delivery.write_delivery(df, paths=paths)
        written += rows
        click.echo(f"  {when}  {rows:>6d} rows")
    click.echo(f"[oq] done. {written} total delivery rows written.")


@main.command("sync-flows")
@click.option("--start", "start", type=str, required=False)
@click.option("--end", "end", type=str, required=False)
@click.option("--quick", is_flag=True)
@click.pass_context
def sync_flows(ctx: click.Context, start: str | None, end: str | None, quick: bool) -> None:
    """Download FII/DII cash-market flows and write to the Parquet store."""
    paths = ctx.obj["paths"]
    today = date.today()
    if quick:
        end_d, start_d = today, today - timedelta(days=10)
    else:
        end_d = _parse_date(end) if end else today
        start_d = _parse_date(start) if start else (end_d - timedelta(days=30))
    click.echo(f"[oq] syncing fii/dii flows {start_d} -> {end_d} into {paths.fii_dii}")
    written = 0
    for when in flows.sync_range(start_d, end_d, paths=paths):
        df = flows.download_flows(when, paths=paths)
        rows = flows.write_flows(df, paths=paths)
        written += rows
        click.echo(f"  {when}  {rows:>6d} rows")
    click.echo(f"[oq] done. {written} total flow rows written.")


@main.command("sync-announcements")
@click.option("--start", "start", type=str, required=False)
@click.option("--end", "end", type=str, required=False)
@click.option("--quick", is_flag=True)
@click.pass_context
def sync_announcements(ctx: click.Context, start: str | None, end: str | None, quick: bool) -> None:
    """Download corporate announcements and write to the Parquet store."""
    paths = ctx.obj["paths"]
    today = date.today()
    if quick:
        end_d, start_d = today, today - timedelta(days=10)
    else:
        end_d = _parse_date(end) if end else today
        start_d = _parse_date(start) if start else (end_d - timedelta(days=30))
    click.echo(f"[oq] syncing announcements {start_d} -> {end_d} into {paths.announcements}")
    written = 0
    for when in announcements.sync_range(start_d, end_d, paths=paths):
        df = announcements.download_announcements(when, paths=paths)
        rows = announcements.write_announcements(df, paths=paths)
        written += rows
        click.echo(f"  {when}  {rows:>6d} rows")
    click.echo(f"[oq] done. {written} total announcement rows written.")


if __name__ == "__main__":
    main(obj={})
