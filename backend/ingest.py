"""
Ingest cleaned_laptops_rag_dataset.csv into the `laptops` table.

Usage:
    python ingest.py
    python ingest.py --csv ../cleaned_laptops_rag_dataset.csv --db-url sqlite:///./laptops.db

By default this DROPS and recreates the `laptops` table before loading, so the
DB always mirrors the current CSV exactly. Pass --append to insert without
dropping (validation/dedup still runs, but pre-existing rows are kept).
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.cleaning import (
    clean_model_name,
    parse_battery_hours,
    parse_gpu_name,
    parse_ram_expandable,
    resolve_processor_brand_and_ghz,
)
from app.db import Base
from app.models import Laptop
from app.schemas import LaptopIngestRecord

DEFAULT_CSV = Path(__file__).parent.parent / "cleaned_laptops_rag_dataset.csv"
DEFAULT_DB_URL = "sqlite:///./laptops.db"


def clean_row(row: pd.Series) -> LaptopIngestRecord:
    processor_brand, cpu_ghz = resolve_processor_brand_and_ghz(
        row["processor_brand"], row["ghz"], row["processor_name"]
    )
    return LaptopIngestRecord(
        brand=str(row["brand"]).strip(),
        model_name=clean_model_name(str(row["name"])),
        processor=str(row["processor_name"]).strip(),
        processor_brand=processor_brand,
        cpu_ghz=cpu_ghz,
        ram_gb=int(row["ram_gb"]),
        ram_expandable=parse_ram_expandable(row["ram_expandable"]),
        storage_gb=int(row["storage_gb"]),
        screen_size_inches=(None if pd.isna(row["screen_size_inches"]) else float(row["screen_size_inches"])),
        gpu_name=parse_gpu_name(row["gpu"]),
        has_dedicated_gpu=bool(row["has_dedicated_gpu"]),
        os=str(row["os"]).strip(),
        battery_life_hours=parse_battery_hours(row["battery_life"]),
        baseline_price=None,  # not present in the source dataset; populated live in Phase 5
    )


def run_ingestion(csv_path: Path, db_url: str, append: bool) -> None:
    if not csv_path.exists():
        print(f"CSV not found at {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    total_rows = len(df)

    before_dedup = len(df)
    df["_clean_model_name"] = df["name"].map(lambda n: clean_model_name(str(n)))
    df = df.drop_duplicates(subset="_clean_model_name", keep="first")
    duplicates_dropped = before_dedup - len(df)

    valid_records: list[LaptopIngestRecord] = []
    errors: list[tuple[int, str]] = []
    for idx, row in df.iterrows():
        try:
            valid_records.append(clean_row(row))
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append((idx, str(exc)))

    engine = create_engine(db_url, connect_args={"check_same_thread": False} if db_url.startswith("sqlite") else {})
    Session = sessionmaker(bind=engine)

    if not append:
        Base.metadata.drop_all(engine, tables=[Laptop.__table__])
    Base.metadata.create_all(engine, tables=[Laptop.__table__])

    session = Session()
    try:
        inserted = 0
        skipped_existing = 0
        for record in valid_records:
            if append and session.query(Laptop).filter_by(model_name=record.model_name).first():
                skipped_existing += 1
                continue
            session.add(Laptop(**record.model_dump()))
            inserted += 1
        session.commit()
    finally:
        session.close()

    print(f"Source rows:           {total_rows}")
    print(f"Duplicate names:       {duplicates_dropped} (dropped)")
    print(f"Failed validation:     {len(errors)}")
    print(f"Inserted:              {inserted}")
    if append:
        print(f"Skipped (already in DB): {skipped_existing}")
    if errors:
        print("\nFirst 10 validation errors:")
        for idx, msg in errors[:10]:
            print(f"  row {idx}: {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--db-url", type=str, default=DEFAULT_DB_URL)
    parser.add_argument("--append", action="store_true", help="Do not drop the table first")
    args = parser.parse_args()

    run_ingestion(args.csv, args.db_url, args.append)


if __name__ == "__main__":
    main()
