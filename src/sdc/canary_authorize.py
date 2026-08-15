"""Offline authorization-artifact generation, deliberately separate from execution."""

from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sdc.canary import LiveGateError
from sdc.contracts import ProviderFailureClass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a reviewed one-use canary authorization without executing it"
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--max-cost-cny", type=Decimal, required=True)
    parser.add_argument("--expires-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.parse_args(argv)
    raise LiveGateError(
        ProviderFailureClass.LIVE_NOT_AUTHORIZED,
        "authorization generation is disabled until an evidence-bound contract is delivered",
    )


if __name__ == "__main__":
    raise SystemExit(main())
