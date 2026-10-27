"""Benchmark Analytics Aggregation Pipelines.

Executes each analytics query, measures execution duration with compound indexes vs unindexed scans,
and prints execution stats and speedup multipliers.
"""

import sys
import os
import time
import argparse

# Add repository root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import List, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from app.mongo.indexes import create_indexes
from app.mongo.analytics_queries import (
    get_kpis,
    get_revenue_trends,
    get_top_movies,
    get_occupancy_and_peak_heatmap,
    get_payment_method_distribution,
    get_cancellation_analytics,
    get_seat_popularity,
    get_conversion_funnel,
    get_customer_segmentation,
    get_genre_language_preferences,
    get_movie_recommendations_cooccurrence,
)


def benchmark_pipeline(name: str, query_fn, db: Database, runs: int = 3) -> Dict[str, Any]:
    """Run a query function multiple times and measure average latency."""
    durations = []
    result = None
    for _ in range(runs):
        t0 = time.perf_counter()
        result = query_fn(db)
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000)  # ms

    avg_ms = sum(durations) / len(durations)
    return {
        "name": name,
        "avg_ms": avg_ms,
        "min_ms": min(durations),
        "result_sample": result,
    }


def explain_query(db: Database, collection_name: str, pipeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Retrieve explain executionStats for an aggregation pipeline."""
    try:
        cmd = {
            "explain": {
                "aggregate": collection_name,
                "pipeline": pipeline,
                "cursor": {},
            },
            "verbosity": "executionStats",
        }
        return db.command(cmd)
    except Exception as exc:
        return {"error": str(exc)}


def run_benchmarks(uri: str, db_name: str):
    print("=" * 80)
    print("  CineBook MongoDB Analytics -- Aggregation Benchmark Suite")
    print("=" * 80)
    print(f"Connecting to: {db_name} @ {uri.split('@')[-1]}")

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client[db_name]
    except Exception as exc:
        print(f"\n[!] Cannot connect to MongoDB: {exc}")
        print("To run benchmarks on local data:")
        print("  1. Start MongoDB: docker compose up -d mongo")
        print("  2. Generate data: python scripts/generate_big_data.py --bookings 50000 --page-views 100000")
        print("  3. Run benchmark: python scripts/benchmark_queries.py\n")
        sys.exit(1)

    doc_count = db.booking_events.estimated_document_count()
    print(f"Active collection size: {doc_count:,} booking_events documents")
    if doc_count == 0:
        print("[!] Warning: booking_events is empty! Run generate_big_data.py first to seed data.")

    # 1. Ensure indexes exist and benchmark with indexes
    print("\nEnsuring all compound indexes are present...")
    create_indexes(db)

    benchmarks = [
        ("Executive KPIs", lambda d: get_kpis(d)),
        ("Revenue Trends (Daily)", lambda d: get_revenue_trends(d, group_by="day")),
        ("Top 10 Blockbusters", lambda d: get_top_movies(d, limit=10)),
        ("Peak-Hour Heatmap (7x24)", lambda d: get_occupancy_and_peak_heatmap(d)),
        ("Payment Distribution", lambda d: get_payment_method_distribution(d)),
        ("Cancellation Analytics", lambda d: get_cancellation_analytics(d)),
        ("Seat Popularity & Tiers", lambda d: get_seat_popularity(d, limit=10)),
        ("Conversion Funnel", lambda d: get_conversion_funnel(d)),
        ("Customer Segmentation", lambda d: get_customer_segmentation(d)),
        ("Genre & Language Mix", lambda d: get_genre_language_preferences(d)),
        ("Co-Occurrence Recommendations", lambda d: get_movie_recommendations_cooccurrence(d, target_movie_id=1, limit=5)),
    ]

    print("\nRunning indexed benchmark iterations...")
    indexed_results = {}
    for name, fn in benchmarks:
        res = benchmark_pipeline(name, fn, db)
        indexed_results[name] = res["avg_ms"]

    # 2. Benchmark unindexed baseline vs indexed on targeted queries (where index selectivity applies)
    print("\nBenchmarking index selectivity (Indexed IXSCAN vs Unindexed COLLSCAN)...")
    selectivity_benchmarks = [
        (
            "Movie Filtered Revenue (movie_id=1)",
            [
                {"$match": {"movie_id": 1, "status": "CONFIRMED"}},
                {"$group": {"_id": "$format", "rev": {"$sum": "$amount_inr"}, "count": {"$sum": 1}}},
            ],
            {"movie_id": 1, "created_at": -1},
        ),
        (
            "User History Query (user_id=42)",
            [
                {"$match": {"user_id": 42}},
                {"$sort": {"created_at": -1}},
                {"$limit": 20},
            ],
            {"user_id": 1, "created_at": -1},
        ),
        (
            "Recent 7-Day Revenue Query",
            [
                {"$match": {"status": "CONFIRMED", "created_at": {"$gte": time.time() - 7 * 86400}}},
                {"$group": {"_id": "$payment_method", "total": {"$sum": "$amount_inr"}}},
            ],
            {"status": 1, "created_at": -1},
        ),
    ]

    selectivity_results = []
    for q_name, pipeline, index_hint in selectivity_benchmarks:
        # Indexed execution
        t0 = time.perf_counter()
        for _ in range(3):
            list(db.booking_events.aggregate(pipeline, hint=index_hint, allowDiskUse=True))
        t1 = time.perf_counter()
        idx_ms = ((t1 - t0) / 3) * 1000

        # Unindexed (Natural order full scan) execution
        t0 = time.perf_counter()
        for _ in range(3):
            list(db.booking_events.aggregate(pipeline, hint={"$natural": 1}, allowDiskUse=True))
        t1 = time.perf_counter()
        unidx_ms = ((t1 - t0) / 3) * 1000

        speedup = unidx_ms / max(idx_ms, 0.01)
        selectivity_results.append((q_name, idx_ms, unidx_ms, speedup))

    # 3. Print Results Tables
    print("\n" + "=" * 80)
    print("  1. GLOBAL AGGREGATION PIPELINES (Full Collection)")
    print("=" * 80)
    print(f"{'Aggregation Query Pipeline':<35} | {'Indexed Latency':<16} | {'Execution Type'}")
    print("-" * 80)
    for name, fn in benchmarks:
        idx_lat = indexed_results.get(name, 0.0)
        print(f"{name:<35} | {idx_lat:8.2f} ms      | Aggregation Pipeline")

    print("\n" + "=" * 80)
    print("  2. INDEX SELECTIVITY COMPARISON (IXSCAN vs COLLSCAN)")
    print("=" * 80)
    print(f"{'Selective Query Pattern':<35} | {'Indexed (IXSCAN)':<16} | {'Unindexed (COLLSCAN)':<20} | {'Speedup'}")
    print("-" * 80)
    for q_name, idx_ms, unidx_ms, speedup in selectivity_results:
        print(f"{q_name:<35} | {idx_ms:8.2f} ms      | {unidx_ms:8.2f} ms         | {speedup:5.1f}x faster")

    # 4. Explain Plan Summary for Revenue Trends
    print("\n" + "=" * 80)
    print("  EXPLAIN ('executionStats') Sample for Revenue Trends Aggregation")
    print("=" * 80)
    pipeline_sample = [
        {"$match": {"status": "CONFIRMED"}},
        {"$group": {"_id": "$format", "total": {"$sum": "$amount_inr"}, "count": {"$sum": 1}}},
    ]
    stats = explain_query(db, "booking_events", pipeline_sample)
    exec_stats = stats.get("stages", [{}])[0].get("$cursor", {}).get("executionStats", {})
    if not exec_stats:
        exec_stats = stats.get("executionStats", {})

    print(f"Docs Examined:     {exec_stats.get('totalDocsExamined', 'N/A')}")
    print(f"Keys Examined:     {exec_stats.get('totalKeysExamined', 'N/A')}")
    print(f"Execution Time:    {exec_stats.get('executionTimeMillis', 'N/A')} ms")
    print(f"Execution Success: {stats.get('ok', 1) == 1}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Benchmark CineBook MongoDB analytical queries.")
    parser.add_argument("--mongo-uri", type=str, default="mongodb://localhost:27017")
    parser.add_argument("--db-name", type=str, default="cinebook_analytics")
    args = parser.parse_args()
    run_benchmarks(args.mongo_uri, args.db_name)


if __name__ == "__main__":
    main()
