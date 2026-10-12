"""CLI command runner for executing Healthcare ETL ingestion."""

import os
import sys
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.database.connection import init_db, SessionLocal
from src.etl.pipeline import HealthcareETLPipeline


def main():
    parser = argparse.ArgumentParser(description="Healthcare Ingestion ETL Pipeline Runner")
    parser.add_argument("--data", type=str, default="data/diabetic_data.csv", help="Path to encounter CSV dataset")
    parser.add_argument("--mapping", type=str, default="data/IDS_mapping.csv", help="Path to IDS_mapping.csv")
    parser.add_argument("--type", type=str, default="INITIAL", choices=["INITIAL", "INCREMENTAL"], help="Batch type")
    parser.add_argument("--limit", type=int, default=None, help="Optional record limit for testing")

    args = parser.parse_args()

    # Resolve paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    data_path = os.path.join(project_root, args.data) if not os.path.isabs(args.data) else args.data
    mapping_path = os.path.join(project_root, args.mapping) if not os.path.isabs(args.mapping) else args.mapping

    if not os.path.exists(data_path):
        # Check standard search locations
        candidate_paths = [
            os.path.join(project_root, "data", "diabetic_data.csv"),
            os.path.join(project_root, "diabetic_data.csv"),
        ]
        for candidate in candidate_paths:
            if os.path.exists(candidate):
                data_path = candidate
                break
        else:
            print(f"Error: Data file not found at {data_path}")
            sys.exit(1)

    if not os.path.exists(mapping_path):
        candidate_mappings = [
            os.path.join(project_root, "data", "IDS_mapping.csv"),
            os.path.join(project_root, "IDS_mapping.csv"),
        ]
        for candidate in candidate_mappings:
            if os.path.exists(candidate):
                mapping_path = candidate
                break

    print("Initializing Database tables and seed roles...")
    init_db()

    print(f"Executing ETL Pipeline (Type: {args.type})...")
    print(f"Data source: {data_path}")
    print(f"Mapping source: {mapping_path}")
    if args.limit:
        print(f"Limit records: {args.limit}")

    with SessionLocal() as db:
        pipeline = HealthcareETLPipeline(db)
        result = pipeline.run_pipeline(
            data_source=data_path,
            mapping_path=mapping_path,
            batch_type=args.type,
            limit_records=args.limit,
        )

    print("\nETL Execution Summary:")
    print("----------------------------------------")
    print(f"Batch ID:           {result['batch_id']}")
    print(f"Status:             {result['status']}")
    print(f"Records Processed:  {result['records_processed']}")
    print(f"Records Ingested:   {result['records_ingested']}")
    print(f"Execution Time:     {result['execution_time_seconds']}s")
    print(f"Cleanliness Score:  {result['data_quality']['cleanliness_percentage']}%")
    print("----------------------------------------")


if __name__ == "__main__":
    main()
