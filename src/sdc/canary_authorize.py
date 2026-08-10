"""Offline authorization-artifact generation, deliberately separate from execution."""

from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sdc.canary import build_live_authorization
from sdc.contracts import CanaryExecution, CanaryPlan


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
    args = parser.parse_args(argv)
    plan = CanaryPlan.model_validate_json(args.plan.read_text())
    execution = CanaryExecution.model_validate_json(args.execution.read_text())
    authorization = build_live_authorization(
        plan,
        execution,
        authorization_id=args.authorization_id,
        max_cost_cny=args.max_cost_cny,
        expires_at=args.expires_at,
        nonce=args.nonce,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(authorization.model_dump_json(indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
