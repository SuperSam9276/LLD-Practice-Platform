"""Seed the three MVP problems (open question #3).

Run once against the target database:

    DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/lld python backend/scripts/seed_problems.py

Two deliberate choices:

1. This writes through SQL against the `problems` table rather than through the
   domain/repository layer. Seeding is developer tooling, not a product use case —
   there is no "create problem" flow in the MVP, so inventing a repository write
   path just for a fixture would add an interface nothing else uses.

2. It is idempotent on `title`: re-running it never duplicates rows. The table has
   no unique constraint on title (problems are developer-authored, not user data),
   so the check is done in the script.

   !! Check `rubric_key` below against the rubric registry in the domain code
   (decision #28). If the key here does not match a registered rubric, problems
   will load in the UI but evaluation will fail when it looks the rubric up.
"""

import os
import sys

from sqlalchemy import create_engine, text

RUBRIC_KEY = "default_lld_v1"  # must match the key in the Python rubric registry

PROBLEMS = [
    {
        "title": "Parking Lot",
        "description": """Design the domain model for a multi-floor parking lot.

Requirements
- The lot has several floors. Each floor has a fixed set of parking spots.
- Spots come in sizes: motorcycle, compact, large. A vehicle may only occupy a spot
  it fits in.
- A vehicle arrives, is assigned a spot, and receives a ticket. On exit the ticket is
  used to compute a fee and free the spot.
- Pricing: the first hour is a flat rate; each additional hour is charged separately.
  Rates differ by spot size.
- The entrance display shows how many spots of each size are free.

Out of scope
- Payment gateways, reservations, number-plate recognition, user accounts.

What to hand in
Requirements and assumptions, the classes you would create and what each owns,
the relationships between them, and the reasoning behind the calls you made.
Say explicitly where a new vehicle type or a new pricing rule would be absorbed.""",
    },
    {
        "title": "Vending Machine",
        "description": """Design the domain model for a coin-operated vending machine.

Requirements
- The machine holds several product slots. Each slot has a product, a price, and a
  quantity.
- A customer inserts coins one at a time, selects a product, and receives the product
  plus change.
- The machine must refuse a selection when the inserted amount is insufficient, the
  slot is empty, or it cannot make exact change.
- The customer can cancel at any point before dispensing and get their coins back.
- An operator can restock a slot and collect the cash.

Out of scope
- Card payments, remote telemetry, multi-machine inventory.

What to hand in
Requirements and assumptions, the classes you would create and what each owns, the
relationships between them, and the reasoning behind the calls you made. Be explicit
about where the machine's states live and what drives a transition between them.""",
    },
    {
        "title": "Elevator System",
        "description": """Design the domain model for an elevator system in an office building.

Requirements
- The building has several floors and more than one elevator car.
- Two kinds of request exist: a hall call (a person on a floor presses up or down) and
  a car call (a person inside presses a floor button).
- A hall call must be assigned to one car. The assignment strategy should be replaceable
  — nearest car today, something smarter later.
- A car moves up or down, stops to open doors, and must not reverse direction while it
  still has requests in the current direction.
- A car can be taken out of service for maintenance and must stop accepting assignments.

Out of scope
- Physical motor control, real-time scheduling guarantees, fire-service modes.

What to hand in
Requirements and assumptions, the classes you would create and what each owns, the
relationships between them, and the reasoning behind the calls you made. Name the
seam where a different dispatch strategy would plug in.""",
    },
]


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    engine = create_engine(url)
    inserted, skipped = 0, 0

    with engine.begin() as conn:
        for problem in PROBLEMS:
            exists = conn.execute(
                text("SELECT 1 FROM problems WHERE title = :title"),
                {"title": problem["title"]},
            ).first()
            if exists:
                skipped += 1
                continue
            conn.execute(
                text(
                    "INSERT INTO problems (title, description, rubric_key) "
                    "VALUES (:title, :description, :rubric_key)"
                ),
                {**problem, "rubric_key": RUBRIC_KEY},
            )
            inserted += 1

    print(f"Seeded {inserted} problem(s); {skipped} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
