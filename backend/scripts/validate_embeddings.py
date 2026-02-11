#!/usr/bin/env python3
"""
Validate all inmate embeddings in the database.
Identifies corrupted, invalid, or duplicate embeddings.

Usage:
    cd backend
    python scripts/validate_embeddings.py
"""

import os
import sys
import numpy as np
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate

EXPECTED_DIM = 512


def validate_embedding(emb, expected_dim=512):
    """Validate a single embedding."""
    issues = []

    if emb is None:
        return ["NULL embedding"]

    if not isinstance(emb, (list, np.ndarray)):
        return [f"Invalid type: {type(emb)}"]

    arr = np.array(emb)

    if len(arr) != expected_dim:
        issues.append(f"Wrong dimension: {len(arr)} (expected {expected_dim})")

    if np.isnan(arr).any():
        nan_count = np.isnan(arr).sum()
        issues.append(f"Contains {nan_count} NaN values")

    if np.isinf(arr).any():
        inf_count = np.isinf(arr).sum()
        issues.append(f"Contains {inf_count} Inf values")

    # Check for all zeros (invalid embedding)
    if np.allclose(arr, 0):
        issues.append("All zeros (invalid)")

    return issues


def check_duplicates(embeddings):
    """Check for duplicate embeddings in a list."""
    duplicates = []
    seen_hashes = {}

    for i, emb in enumerate(embeddings):
        if emb is None:
            continue
        arr = np.array(emb)
        # Create a hash of the embedding (rounded to handle float precision)
        emb_hash = hash(arr.round(6).tobytes())

        if emb_hash in seen_hashes:
            duplicates.append((i, seen_hashes[emb_hash]))
        else:
            seen_hashes[emb_hash] = i

    return duplicates


def main():
    print("=" * 70)
    print("EMBEDDING VALIDATION REPORT")
    print("=" * 70)

    app = create_app()

    with app.app_context():
        inmates = Inmate.query.all()
        print(f"\nTotal inmates in database: {len(inmates)}")

        stats = {
            "total": len(inmates),
            "no_embeddings": 0,
            "valid": 0,
            "invalid": 0,
            "with_duplicates": 0,
        }

        issues_report = []

        for inmate in inmates:
            inmate_issues = []
            all_embeddings = []

            # Check legacy face_encoding
            if inmate.face_encoding is not None:
                issues = validate_embedding(inmate.face_encoding)
                if issues:
                    inmate_issues.append(f"Legacy encoding: {', '.join(issues)}")
                all_embeddings.append(inmate.face_encoding)

            # Check multi-embeddings
            if inmate.face_encodings_json:
                try:
                    multi = json.loads(inmate.face_encodings_json)
                    for i, emb in enumerate(multi):
                        issues = validate_embedding(emb)
                        if issues:
                            inmate_issues.append(f"Multi-encoding[{i}]: {', '.join(issues)}")
                        all_embeddings.append(emb)
                except json.JSONDecodeError as e:
                    inmate_issues.append(f"JSON parse error: {e}")

            # Check for duplicates
            if len(all_embeddings) > 1:
                dups = check_duplicates(all_embeddings)
                if dups:
                    inmate_issues.append(f"Duplicate embeddings: {len(dups)} pairs")
                    stats["with_duplicates"] += 1

            # Categorize
            if not all_embeddings:
                stats["no_embeddings"] += 1
            elif inmate_issues:
                stats["invalid"] += 1
                issues_report.append({
                    "inmate_id": inmate.inmate_id,
                    "name": inmate.name,
                    "num_embeddings": len(all_embeddings),
                    "issues": inmate_issues
                })
            else:
                stats["valid"] += 1

        # Print summary
        print("\n" + "-" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"Total inmates: {stats['total']}")
        print(f"Valid embeddings: {stats['valid']}")
        print(f"Invalid embeddings: {stats['invalid']}")
        print(f"No embeddings: {stats['no_embeddings']}")
        print(f"With duplicates: {stats['with_duplicates']}")

        # Print detailed issues
        if issues_report:
            print("\n" + "-" * 70)
            print("INMATES WITH ISSUES")
            print("-" * 70)
            for report in issues_report:
                print(f"\n{report['inmate_id']} ({report['name']}) - {report['num_embeddings']} embeddings:")
                for issue in report['issues']:
                    print(f"  - {issue}")
        else:
            print("\nNo embedding issues found!")

        # Check specific inmates from the problem
        print("\n" + "-" * 70)
        print("CHECKING SPECIFIC INMATES")
        print("-" * 70)

        for inmate_id in ["CDJ-C3A726", "CDJ-ACF8E3"]:
            inmate = Inmate.query.filter_by(inmate_id=inmate_id).first()
            if inmate:
                encodings = inmate.get_all_encodings()
                print(f"\n{inmate_id} ({inmate.name}):")
                print(f"  Mugshot: {inmate.mugshot_path}")
                print(f"  Total embeddings: {len(encodings)}")
                if encodings:
                    dims = [len(e) for e in encodings]
                    print(f"  Dimensions: {set(dims)}")
                    # Check for NaN
                    nan_count = sum(1 for e in encodings if np.isnan(e).any())
                    print(f"  With NaN: {nan_count}")
            else:
                print(f"\n{inmate_id}: NOT FOUND in database")


if __name__ == "__main__":
    main()
