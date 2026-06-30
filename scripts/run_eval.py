#!/usr/bin/env python3
"""Run the evaluation pipeline against a running gateway."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.evaluation.evaluator import run_evaluation


async def main() -> None:
    summary, report_path = await run_evaluation()
    print("Evaluation complete")
    for mode, stats in summary.items():
        print(f"\n{mode}:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
