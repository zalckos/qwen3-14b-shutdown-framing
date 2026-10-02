#!/usr/bin/env python3

import argparse
import csv
import hashlib
import random
from pathlib import Path


CONDITIONS = ("A", "B", "C")
UINT32_MAX = 2**32 - 1


def generate_unique_seeds(n_pairs, master_seed):
    """Generate one unique 32-bit seed for each matched pair."""
    rng = random.Random(master_seed)

    seeds = set()

    while len(seeds) < n_pairs:
        seeds.add(rng.randint(0, UINT32_MAX))

    return list(seeds)


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Generate fixed paired seeds with randomized execution order."
    )

    parser.add_argument(
        "-n",
        "--pairs",
        type=int,
        default=100,
        help="Number of matched pairs (default: 100)",
    )

    parser.add_argument(
        "--master-seed",
        type=int,
        default=20260922,
        help="Master seed for generating paired seeds.",
    )

    parser.add_argument(
        "--order-seed",
        type=int,
        default=20260923,
        help="Master seed for randomizing execution order.",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("seed_list.csv"),
        help="Output CSV file.",
    )

    args = parser.parse_args()

    if args.pairs <= 0:
        parser.error("--pairs must be greater than zero")

    if not 0 <= args.master_seed <= UINT32_MAX:
        parser.error("--master-seed must be between 0 and 4294967295")

    if not 0 <= args.order_seed <= UINT32_MAX:
        parser.error("--order-seed must be between 0 and 4294967295")

    # ------------------------------------------------------------
    # STEP 1
    # Generate one fixed seed per matched pair.
    # ------------------------------------------------------------

    paired_seeds = generate_unique_seeds(
        args.pairs,
        args.master_seed,
    )

    # ------------------------------------------------------------
    # STEP 2
    # Create A/B/C records for every pair.
    # ------------------------------------------------------------

    runs = []

    for pair_number, seed in enumerate(paired_seeds, start=1):
        pair_id = f"{pair_number:03d}"

        for condition in CONDITIONS:
            runs.append({
                "pair_id": pair_id,
                "condition": condition,
                "seed": seed,
            })

    # ------------------------------------------------------------
    # STEP 3
    # Randomize the execution order of all 3N runs.
    # ------------------------------------------------------------

    order_rng = random.Random(args.order_seed)
    order_rng.shuffle(runs)

    # ------------------------------------------------------------
    # STEP 4
    # Assign execution numbers.
    # ------------------------------------------------------------

    for execution_order, run in enumerate(runs, start=1):
        run["execution_order"] = execution_order

    # ------------------------------------------------------------
    # STEP 5
    # Write CSV.
    # ------------------------------------------------------------

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "execution_order",
                "pair_id",
                "condition",
                "seed",
            ],
        )

        writer.writeheader()
        writer.writerows(runs)

    digest = sha256_file(args.output)

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    sequence = "".join(run["condition"] for run in runs)

    print(f"Created: {args.output}")
    print(f"Paired observations: {args.pairs}")
    print(f"Total runs: {len(runs)}")
    print(f"A runs: {sequence.count('A')}")
    print(f"B runs: {sequence.count('B')}")
    print(f"C runs: {sequence.count('C')}")
    print()
    print(f"Seed master seed:  {args.master_seed}")
    print(f"Order master seed: {args.order_seed}")
    print()
    print(f"Execution sequence:")
    print(sequence)
    print()
    print(f"SHA-256:")
    print(digest)


if __name__ == "__main__":
    main()
