#!/usr/bin/env python3
"""
Seed sample data for Heimdall dashboard testing.
Creates cameras, inmates, alerts, and matches.

Usage:
    cd backend
    python seed_data.py
"""

import os
import sys
from datetime import datetime, timedelta
import random

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match


def seed_database():
    """Add sample data to the database."""
    app = create_app()

    with app.app_context():
        print("Seeding sample data...")

        # Create sample cameras
        cameras_data = [
            {"name": "Main Entrance", "location": "Building A - Front Gate", "status": True},
            {"name": "East Wing Corridor", "location": "Building B - Floor 1", "status": True},
            {"name": "West Wing Corridor", "location": "Building C - Floor 1", "status": True},
            {"name": "Cafeteria", "location": "Building A - Ground Floor", "status": True},
            {"name": "Recreation Area", "location": "Building D - Yard", "status": True},
            {"name": "Checkpoint Alpha", "location": "Perimeter - North", "status": True},
            {"name": "Checkpoint Bravo", "location": "Perimeter - South", "status": False},  # Offline
            {"name": "Medical Wing", "location": "Building E - Floor 2", "status": True},
            {"name": "Visitation Room", "location": "Building A - Floor 1", "status": True},
            {"name": "Loading Dock", "location": "Building F - Rear", "status": False},  # Offline
        ]

        existing_cameras = Camera.query.count()
        if existing_cameras == 0:
            for cam_data in cameras_data:
                camera = Camera(
                    name=cam_data["name"],
                    location=cam_data["location"],
                    status=cam_data["status"]
                )
                db.session.add(camera)
            db.session.commit()
            print(f"  Created {len(cameras_data)} cameras")
        else:
            print(f"  Cameras already exist ({existing_cameras})")

        # Create sample inmates
        inmates_data = [
            {"name": "John Smith", "days": 365, "status": "Incarcerated"},
            {"name": "Michael Johnson", "days": 730, "status": "Incarcerated"},
            {"name": "Robert Williams", "days": 180, "status": "Incarcerated"},
            {"name": "David Brown", "days": 90, "status": "Released"},
            {"name": "James Davis", "days": 540, "status": "Incarcerated"},
            {"name": "Christopher Miller", "days": 1095, "status": "Incarcerated"},
            {"name": "Matthew Wilson", "days": 270, "status": "Incarcerated"},
            {"name": "Anthony Moore", "days": 450, "status": "Incarcerated"},
        ]

        existing_inmates = Inmate.query.count()
        if existing_inmates == 0:
            for inm_data in inmates_data:
                inmate = Inmate(
                    name=inm_data["name"],
                    mugshot_path=f"/static/mugshots/{inm_data['name'].lower().replace(' ', '_')}.jpg",
                    sentence_duration_days=inm_data["days"],
                    status=inm_data["status"]
                )
                db.session.add(inmate)
            db.session.commit()
            print(f"  Created {len(inmates_data)} inmates")
        else:
            print(f"  Inmates already exist ({existing_inmates})")

        # Create sample alerts
        existing_alerts = Alert.query.count()
        if existing_alerts == 0:
            cameras = Camera.query.all()
            inmates = Inmate.query.filter_by(status='Incarcerated').all()

            alerts_data = []
            now = datetime.utcnow()

            # Create alerts over the last 48 hours
            alert_messages = [
                ("Unauthorized access attempt detected", "danger"),
                ("Movement detected in restricted area", "warning"),
                ("Face recognition match found", "warning"),
                ("Camera offline alert", "danger"),
                ("Suspicious activity detected", "warning"),
                ("Perimeter breach alert", "danger"),
                ("Routine check completed", "info"),
                ("System maintenance alert", "info"),
            ]

            for i in range(15):
                msg, level = random.choice(alert_messages)
                camera = random.choice(cameras) if cameras else None
                inmate = random.choice(inmates) if inmates and random.random() > 0.3 else None

                alert = Alert(
                    message=msg,
                    level=level,
                    timestamp=now - timedelta(hours=random.randint(0, 48)),
                    resolved=random.random() > 0.4,  # 60% resolved
                    camera_id=camera.id if camera else None,
                    inmate_id=inmate.id if inmate else None,
                    confidence=round(random.uniform(0.75, 0.99), 2) if inmate else None
                )
                db.session.add(alert)

            db.session.commit()
            print(f"  Created 15 alerts")
        else:
            print(f"  Alerts already exist ({existing_alerts})")

        # Create sample matches
        existing_matches = Match.query.count()
        if existing_matches == 0:
            inmates = Inmate.query.filter_by(status='Incarcerated').all()

            now = datetime.utcnow()
            created_count = 0

            for i in range(10):
                inmate = random.choice(inmates) if inmates else None

                if inmate:
                    match = Match(
                        inmate_id=inmate.id,
                        timestamp=now - timedelta(hours=random.randint(0, 24))
                    )
                    db.session.add(match)
                    created_count += 1

            db.session.commit()
            print(f"  Created {created_count} matches")
        else:
            print(f"  Matches already exist ({existing_matches})")

        print("\nSeed data complete!")

        # Print summary
        print("\nDatabase Summary:")
        print(f"  Cameras: {Camera.query.count()} ({Camera.query.filter_by(status=True).count()} active)")
        print(f"  Inmates: {Inmate.query.count()}")
        print(f"  Alerts: {Alert.query.count()} ({Alert.query.filter_by(resolved=False).count()} unresolved)")
        print(f"  Matches: {Match.query.count()}")


if __name__ == "__main__":
    seed_database()
