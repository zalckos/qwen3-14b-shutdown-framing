#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


def analyze_csv(input_csv: Path) -> None:
    output_csv = input_csv.parent / "flagged_bullets.csv"

    with input_csv.open("r", newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)

        if not reader.fieldnames:
            raise ValueError("The input CSV is empty or has no header row.")

        required_columns = {"parse_status", "category"}
        missing = required_columns - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing required CSV columns: {', '.join(sorted(missing))}"
            )

        flagged_rows = [
            row
            for row in reader
            if (
                row["parse_status"].strip().lower() != "exact"
                or row["category"].strip() == "Other/unclear"
            )
        ]

    # Preserve the original column names, order, and complete row contents.
    with output_csv.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=reader.fieldnames,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(flagged_rows)

    print(f"Input file: {input_csv}")
    print(f"Output file: {output_csv}")
    print(f"Total flagged bullets: {len(flagged_rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract bullets requiring manual review from a CSV."
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="Path to the input CSV file",
    )

    args = parser.parse_args()
    analyze_csv(args.input_csv)
