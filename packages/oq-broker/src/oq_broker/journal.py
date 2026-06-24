"""Order journal export for tax and compliance records."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from oq_broker.models import Fill, Order


def orders_to_frame(orders: Iterable[Order]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for o in orders:
        req = o.request
        rows.append(
            {
                "order_id": o.order_id,
                "broker": o.broker,
                "broker_order_id": o.broker_order_id,
                "status": o.status.value,
                "symbol": req.symbol,
                "exchange": req.exchange,
                "side": req.side.value,
                "quantity": req.quantity,
                "filled_quantity": o.filled_quantity,
                "order_type": req.order_type.value,
                "product": req.product.value,
                "price": req.price,
                "trigger_price": req.trigger_price,
                "average_price": o.average_price,
                "algo_id": req.algo_id,
                "strategy_id": req.strategy_id,
                "placed_at": o.placed_at.isoformat(),
                "updated_at": o.updated_at.isoformat(),
                "tag": req.tag,
                "rejection_reason": o.rejection_reason,
            }
        )
    return pd.DataFrame(rows)


def fills_to_frame(fills: Iterable[Fill]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for f in fills:
        rows.append(
            {
                "fill_id": f.fill_id,
                "order_id": f.order_id,
                "symbol": f.symbol,
                "side": f.side.value,
                "quantity": f.quantity,
                "price": f.price,
                "value": f.price * f.quantity,
                "timestamp": f.timestamp.isoformat(),
            }
        )
    return pd.DataFrame(rows)


def export_journal(
    orders: Iterable[Order],
    fills: Iterable[Fill],
    out_dir: str | Path,
    fmt: str = "csv",
) -> dict[str, Path]:
    """Write orders + fills to ``out_dir`` in either ``csv`` or ``parquet``."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if fmt not in {"csv", "parquet"}:
        raise ValueError("fmt must be 'csv' or 'parquet'")
    odf = orders_to_frame(orders)
    fdf = fills_to_frame(fills)
    ext = "csv" if fmt == "csv" else "parquet"
    o_path = out / f"orders.{ext}"
    f_path = out / f"fills.{ext}"
    if fmt == "csv":
        odf.to_csv(o_path, index=False)
        fdf.to_csv(f_path, index=False)
    else:
        odf.to_parquet(o_path, index=False)
        fdf.to_parquet(f_path, index=False)
    return {"orders": o_path, "fills": f_path}


__all__ = ["export_journal", "fills_to_frame", "orders_to_frame"]
