#!/usr/bin/env python3
"""
Clean up duplicate Brad Pitt test inmates.
Removes CDJ-0BCC0B and CDJ-2A704A, keeps CDJ-C3A726.

Usage:
    cd backend
    python scripts/cleanup_duplicates.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate


def main():
    print("=" * 60)
    print("CLEANUP DUPLICATE BRAD PITT TEST INMATES")
    print("=" * 60)

    # IDs to remove (duplicates using same Brad Pitt mugshot)
    ids_to_remove = ["CDJ-0BCC0B", "CDJ-2A704A"]
    id_to_keep = "CDJ-C3A726"

    app = create_app()

    with app.app_context():
        # Verify the one we're keeping exists
        keeper = Inmate.query.filter_by(inmate_id=id_to_keep).first()
        if keeper:
            print(f"\nKEEPING: {id_to_keep} ({keeper.name})")
            print(f"  Mugshot: {keeper.mugshot_path}")
        else:
            print(f"\nWARNING: {id_to_keep} not found in database!")

        # Remove duplicates
        removed = 0
        for inmate_id in ids_to_remove:
            inmate = Inmate.query.filter_by(inmate_id=inmate_id).first()
            if inmate:
                print(f"\nREMOVING: {inmate_id} ({inmate.name})")
                print(f"  Mugshot: {inmate.mugshot_path}")
                db.session.delete(inmate)
                removed += 1
            else:
                print(f"\nNOT FOUND: {inmate_id} (already removed?)")

        db.session.commit()

        # Final count
        total = Inmate.query.count()
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Removed: {removed} duplicate inmates")
        print(f"Remaining inmates: {total}")


if __name__ == "__main__":
    main()
