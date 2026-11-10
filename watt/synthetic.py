"""Generate the same fictional reporting snapshots without a database or API."""
import argparse
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date
import gzip
import io
import json
from pathlib import Path
from typing import Iterable

from .finance import Adjustment, Contract, Month, months_between

START = date(2024, 1, 1)
NOVEMBER = date(2025, 11, 1)
DECEMBER = date(2025, 12, 1)


@dataclass(frozen=True, slots=True)
class Demo:
    contracts: tuple[Contract, ...]
    months: tuple[Month, ...]


def _contracts() -> Iterable[Contract]:
    for i in range(10_000):
        plan = "solar_export_credit" if 20 <= i < 80 else "solar_standard" if i < 200 else "standard"
        yield Contract(f"contract-{i:05}", f"customer-{i:05}", i < 200, START,
                       DECEMBER if i % 10 == 0 else date(2026, 12, 1), plan)


def _rows(contracts: Iterable[Contract]) -> Iterable[Month]:
    for i, contract in enumerate(contracts):
        for period in months_between(START, DECEMBER):
            month = period.month
            seasonal = 360 if month in {12, 1, 2} and 200 <= i < 5100 else 0
            seasonal += 120 if month in {6, 7, 8} else 0
            if period in (NOVEMBER, DECEMBER):
                seasonal = 100 if 200 <= i < 5100 else 0
            imported = 450 + i % 71 + seasonal
            exported = 100 + i % 31 if contract.solar else 0
            export_credit = 5 * exported
            adjustments = ()
            if contract.plan == "solar_export_credit":
                # Higher credits are visible in preceding months as well.
                export_credit += {9: 500, 10: 1500, 11: 2500, 12: 4500}.get(month, 0)
            if period == DECEMBER:
                if i < 20:
                    imported -= 150  # Observed drop; no cause in the fixture.
                elif 80 <= i < 100:
                    adjustments = (Adjustment(f"settlement-2025-12-{i:05}", NOVEMBER, 4500),)
                elif 200 <= i < 420:
                    imported += 100
                elif 5100 <= i < 5180:
                    imported -= 100
            yield Month(contract.contract_id, period, monthrange(period.year, month)[1],
                        imported, exported, energy_revenue=22 * imported, fixed_fees=500,
                        bill_credits=100, export_credits=export_credit, wholesale=8 * imported,
                        ancillary=imported, transmission=2 * imported, other=imported,
                        adjustments=adjustments)


def make_demo() -> Demo:
    contracts = tuple(_contracts())
    return Demo(contracts, tuple(_rows(contracts)))


def _export_rows(path: Path, values: Iterable[Contract | Month]) -> None:
    with path.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, compresslevel=3) as compressed:
        with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as out:
            for value in values:
                out.write(json.dumps(asdict(value), default=date.isoformat, separators=(",", ":")) + "\n")


def export_demo(destination: Path) -> None:
    destination.mkdir(parents=True)
    contracts = tuple(_contracts())
    _export_rows(destination / "contracts.jsonl.gz", contracts)
    _export_rows(destination / "contract_months.jsonl.gz", _rows(contracts))
    manifest = {"synthetic": True, "currency": "USD", "money_unit": "cent",
                "contract_count": 10_000, "contract_month_count": 240_000,
                "snapshots": {"initial": NOVEMBER.isoformat(), "refreshed": DECEMBER.isoformat()}}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New directory for the synthetic export")
    args = parser.parse_args()
    export_demo(args.destination)
    print(f"Exported synthetic contracts and monthly records to {args.destination}")
