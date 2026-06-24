"""``oq-zoo`` CLI: run the honesty gate on registered strategies."""

from __future__ import annotations

import argparse
import importlib
import sys

from oq_zoo.gate import HonestyGate, HonestyGateConfig
from oq_zoo.registry import REGISTRY


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="oq-zoo", description="OpenQuant strategy zoo CLI.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List registered strategies.")
    p_list.add_argument("--module", action="append", default=[], help="Import this module first.")

    p_gate = sub.add_parser("gate", help="Run the honesty gate (requires spec hook).")
    p_gate.add_argument("--module", action="append", default=[], help="Import this module first.")
    p_gate.add_argument(
        "--spec-hook",
        required=True,
        help="dotted path to a callable returning list[StrategySpec]",
    )
    p_gate.add_argument("--min-alpha-bps", type=float, default=0.0)
    p_gate.add_argument("--min-oos-sharpe", type=float, default=0.0)
    p_gate.add_argument("--no-walk-forward", action="store_true")

    args = parser.parse_args(argv)
    for mod in args.module:
        importlib.import_module(mod)

    if args.cmd == "list":
        for name, entry in sorted(REGISTRY.items()):
            tags = ",".join(entry.tags) if entry.tags else "-"
            print(f"{name:<32s} {entry.category:<16s} {entry.cost_preset:<10s} tags={tags}")
        return 0

    if args.cmd == "gate":
        module_path, _, attr = args.spec_hook.rpartition(":")
        if not module_path:
            module_path, _, attr = args.spec_hook.rpartition(".")
        spec_module = importlib.import_module(module_path)
        spec_fn = getattr(spec_module, attr)
        specs = spec_fn()
        gate = HonestyGate(
            config=HonestyGateConfig(
                min_alpha_bps=args.min_alpha_bps,
                require_walk_forward=not args.no_walk_forward,
                min_oos_sharpe=args.min_oos_sharpe,
            )
        )
        result = gate.run(specs)
        print(result.summary())
        return 0 if result.passed else 1

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
