"""High-Volume Big Data Generator for CineBook Analytics.

Generates realistic Indian cinema datasets modeled on authentic multiplex booking behaviors:
- Metro distributions (Mumbai, Delhi-NCR, Bengaluru, Hyderabad, Chennai, Pune, Kolkata)
- Heavy UPI preference (GPay, PhonePe, Paytm, UPI 75%+)
- Weekend and evening show peaks
- Blockbuster Pareto volume distributions
- Realistic cancellation rates and seat tiering
- High-performance batched bulk loading (10,000 docs/batch) with progress tracking
"""

import sys
import time
import argparse
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from faker import Faker

try:
    from pymongo import MongoClient, UpdateOne
    from pymongo.errors import PyMongoError
except ImportError:
    MongoClient = None

# Realistic Indian Cinema Constants
INDIAN_CITIES = [
    ("Mumbai", 0.25),
    ("Delhi-NCR", 0.22),
    ("Bengaluru", 0.18),
    ("Hyderabad", 0.14),
    ("Chennai", 0.10),
    ("Pune", 0.06),
    ("Kolkata", 0.05),
]

PAYMENT_METHODS = [
    ("GPay", 0.35),
    ("PhonePe", 0.28),
    ("UPI", 0.12),
    ("Paytm", 0.08),
    ("RuPay", 0.10),
    ("NetBanking", 0.07),
]

MOVIES = [
    {"id": 1, "title": "Kalki 2898 AD", "genre": "Sci-Fi / Mythological Action", "language": "Hindi / Telugu", "weight": 0.24, "base_price": 380},
    {"id": 2, "title": "Stree 2: Sarkate Ka Aatank", "genre": "Horror / Comedy", "language": "Hindi", "weight": 0.22, "base_price": 320},
    {"id": 3, "title": "RRR", "genre": "Action / Epic Period Drama", "language": "Telugu / Hindi", "weight": 0.18, "base_price": 350},
    {"id": 4, "title": "Jawan", "genre": "Action / Thriller", "language": "Hindi / Tamil", "weight": 0.15, "base_price": 340},
    {"id": 5, "title": "Manjummel Boys", "genre": "Survival / Adventure Drama", "language": "Malayalam / Tamil", "weight": 0.11, "base_price": 260},
    {"id": 6, "title": "Kantara", "genre": "Action / Folklore Drama", "language": "Kannada / Hindi", "weight": 0.10, "base_price": 280},
]

SCREENS_FORMATS = [
    ("Audi 1 — IMAX with Laser", "IMAX with Laser", 1.4),
    ("Audi 2 — Dolby Atmos 4K", "Dolby Atmos 4K", 1.2),
    ("Audi 3 — Standard 2D", "Standard 2D", 1.0),
    ("Audi 4 — 4DX Motion", "4DX", 1.5),
]

DEVICES = [("mobile", 0.72), ("desktop", 0.22), ("tablet", 0.06)]
REFERRERS = [("BookMyShow", 0.35), ("Google", 0.30), ("Instagram", 0.18), ("Direct", 0.12), ("Twitter / X", 0.05)]
PATHS = ["/", "/movies/1", "/movies/2", "/movies/3", "/movies/4", "/movies/5", "/movies/6", "/shows/1/seats", "/shows/2/seats", "/shows/3/seats"]


def weighted_choice(items_weights):
    items, weights = zip(*items_weights)
    return random.choices(items, weights=weights, k=1)[0]


def print_progress(current: int, total: int, prefix: str = "", start_time: float = 0.0):
    pct = (current / total) * 100 if total > 0 else 100
    bar_len = 32
    filled = int(bar_len * current // total) if total > 0 else bar_len
    bar = "=" * filled + "-" * (bar_len - filled)
    elapsed = max(time.time() - start_time, 0.001)
    rate = current / elapsed
    sys.stdout.write(f"\r{prefix} [{bar}] {pct:5.1f}% ({current:,}/{total:,}) @ {rate:,.0f} docs/sec")
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")


def generate_booking_batch(start_id: int, count: int, fake: Faker, base_date: datetime) -> List[Dict[str, Any]]:
    docs = []
    for i in range(count):
        booking_id = start_id + i
        user_id = random.randint(1, 150000)
        movie = weighted_choice([(m, m["weight"]) for m in MOVIES])
        screen_name, screen_format, price_multiplier = random.choice(SCREENS_FORMATS)

        # Indian cinema day distribution: 65% on weekends (Fri-Sun)
        day_offset = random.randint(0, 179)
        dt = base_date - timedelta(days=day_offset)
        # Shift probability towards Fri(4), Sat(5), Sun(6)
        if random.random() < 0.65:
            dt = dt - timedelta(days=(dt.weekday() - random.choice([4, 5, 6])) % 7)

        # Show times: 55% Evening (18-22), 30% Afternoon (13-17), 15% Morning (9-12)
        time_slot = random.random()
        if time_slot < 0.55:
            hour = random.choice([18, 19, 20, 21, 22])
        elif time_slot < 0.85:
            hour = random.choice([13, 14, 15, 16, 17])
        else:
            hour = random.choice([9, 10, 11, 12])
        minute = random.choice([0, 15, 30, 45])
        show_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Booking created 2 hours to 6 days before show
        lead_hours = random.choice([2, 4, 8, 12, 24, 48, 72, 96])
        created_at = show_dt - timedelta(hours=lead_hours)

        # Ticket quantities: 2 is most common (45%), 1 (20%), 3-4 (25%), 5-6 (10%)
        num_seats = random.choices([1, 2, 3, 4, 5, 6], weights=[0.20, 0.45, 0.15, 0.10, 0.06, 0.04], k=1)[0]
        rows = ["A", "B", "C", "D", "E", "F", "G", "H"]
        selected_row = random.choice(rows)
        start_col = random.randint(1, 10 - num_seats + 1)
        seats = [f"{selected_row}{start_col + s}" for s in range(num_seats)]

        def get_category(row: str) -> str:
            if row in ["G", "H"]:
                return "Recliner"
            elif row in ["C", "D", "E", "F"]:
                return "Prime"
            return "Classic"

        categories = [get_category(selected_row)] * num_seats
        category_mult = 1.5 if categories[0] == "Recliner" else (1.2 if categories[0] == "Prime" else 1.0)
        seat_price = round(movie["base_price"] * price_multiplier * category_mult)
        total_amount = float(seat_price * num_seats)

        # Cancellation rate ~7%
        is_cancelled = random.random() < 0.07
        status = "CANCELLED" if is_cancelled else "CONFIRMED"
        cancelled_at = None
        if is_cancelled:
            # Cancelled between booking creation and 1 hour before show
            cancel_delay = random.randint(1, max(1, lead_hours - 2))
            cancelled_at = created_at + timedelta(hours=cancel_delay)

        doc = {
            "booking_id": booking_id,
            "user_id": user_id,
            "movie_id": movie["id"],
            "movie_title": movie["title"],
            "genre": movie["genre"],
            "language": movie["language"],
            "show_id": random.randint(1, 5000),
            "screen": screen_name,
            "format": screen_format,
            "show_datetime": show_dt,
            "seats": seats,
            "seat_categories": categories,
            "amount_inr": total_amount,
            "payment_method": weighted_choice(PAYMENT_METHODS),
            "status": status,
            "city": weighted_choice(INDIAN_CITIES),
            "created_at": created_at,
            "cancelled_at": cancelled_at,
        }
        docs.append(doc)
    return docs


def generate_page_views_batch(count: int, base_date: datetime) -> List[Dict[str, Any]]:
    docs = []
    for _ in range(count):
        day_offset = random.randint(0, 179)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        ts = base_date - timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
        movie_choice = random.choice(MOVIES)
        path = random.choice(PATHS)
        movie_id = movie_choice["id"] if "/movies/" in path else None

        docs.append({
            "session_id": f"sess_{random.randint(1, 1000000):07x}",
            "user_id": random.randint(1, 150000) if random.random() < 0.4 else None,
            "path": path,
            "movie_id": movie_id,
            "device": weighted_choice(DEVICES),
            "referrer": weighted_choice(REFERRERS),
            "timestamp": ts,
        })
    return docs


def run_generator(
    uri: str,
    db_name: str,
    num_bookings: int,
    num_page_views: int,
    batch_size: int,
    seed: int,
    dry_run: bool = False,
):
    print("=" * 70)
    print("  CineBook Big-Data Generator — Indian Cinema Edition")
    print("=" * 70)
    print(f"Target DB:        {db_name} @ {uri.split('@')[-1]}")
    print(f"Random Seed:      {seed}")
    print(f"Bookings:         {num_bookings:,}")
    print(f"Page Views:       {num_page_views:,}")
    print(f"Batch Size:       {batch_size:,}")
    print(f"Dry Run:          {dry_run}")
    print("-" * 70)

    random.seed(seed)
    fake = Faker("en_IN")
    Faker.seed(seed)
    base_date = datetime.now(timezone.utc)

    db = None
    if not dry_run:
        if MongoClient is None:
            print("ERROR: pymongo is not installed. Install via `pip install pymongo`.")
            sys.exit(1)
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            db = client[db_name]
            print(f"Successfully connected to MongoDB ({db_name}).")
        except Exception as exc:
            print(f"ERROR: Cannot connect to MongoDB: {exc}")
            print("To start local MongoDB with Docker, run:")
            print("  docker compose up -d mongo")
            print("Or set MONGO_URI to an active MongoDB Atlas cluster.")
            sys.exit(1)

    # 1. Generate & Insert Booking Events
    print(f"\n[1/2] Generating {num_bookings:,} booking_events...")
    start_time = time.time()
    inserted_bookings = 0
    current_id = 100000

    while inserted_bookings < num_bookings:
        batch_count = min(batch_size, num_bookings - inserted_bookings)
        docs = generate_booking_batch(current_id, batch_count, fake, base_date)
        current_id += batch_count

        if not dry_run and db is not None:
            db.booking_events.insert_many(docs, ordered=False)

        inserted_bookings += batch_count
        print_progress(inserted_bookings, num_bookings, prefix="Bookings", start_time=start_time)

    # 2. Generate & Insert Page View Events
    print(f"\n[2/2] Generating {num_page_views:,} page_view_events...")
    pv_start = time.time()
    inserted_views = 0

    while inserted_views < num_page_views:
        batch_count = min(batch_size, num_page_views - inserted_views)
        docs = generate_page_views_batch(batch_count, base_date)

        if not dry_run and db is not None:
            db.page_view_events.insert_many(docs, ordered=False)

        inserted_views += batch_count
        print_progress(inserted_views, num_page_views, prefix="Page Views", start_time=pv_start)

    total_time = time.time() - start_time
    print("-" * 70)
    print(f"Data Generation Completed in {total_time:.2f}s ({num_bookings + num_page_views:,} total documents).")
    if not dry_run and db is not None:
        print(f"MongoDB Collection Counts:")
        print(f"  booking_events:    {db.booking_events.estimated_document_count():,}")
        print(f"  page_view_events:  {db.page_view_events.estimated_document_count():,}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Generate realistic big data for CineBook analytics.")
    parser.add_argument("--bookings", type=int, default=1000000, help="Number of booking_events to generate (default: 1,000,000)")
    parser.add_argument("--page-views", type=int, default=5000000, help="Number of page_view_events to generate (default: 5,000,000)")
    parser.add_argument("--batch-size", type=int, default=10000, help="Batch insertion size (default: 10,000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible dataset generation (default: 42)")
    parser.add_argument("--mongo-uri", type=str, default="mongodb://localhost:27017", help="MongoDB Connection URI")
    parser.add_argument("--db-name", type=str, default="cinebook_analytics", help="MongoDB target database name")
    parser.add_argument("--dry-run", action="store_true", help="Generate documents and measure speed without writing to DB")

    args = parser.parse_args()
    run_generator(
        uri=args.mongo_uri,
        db_name=args.db_name,
        num_bookings=args.bookings,
        num_page_views=args.page_views,
        batch_size=args.batch_size,
        seed=args.seed,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
