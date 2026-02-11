#!/usr/bin/env python3
"""
Database initialization script for Heimdall.
Creates tables and a default admin user.

Usage:
    cd backend
    python init_db.py
"""

import os
import sys

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User


def init_database():
    """Initialize the database and create default admin user."""
    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully.")

        # Check if admin user already exists
        admin = User.query.filter_by(username="admin").first()

        if admin:
            print("Admin user already exists.")
        else:
            # Create default admin user
            admin = User(
                username="admin",
                email="admin@heimdall.local",
                is_admin=True,
                is_suspended=False,
            )
            admin.set_password("admin123")  # Change this in production!

            db.session.add(admin)
            db.session.commit()

            print("Default admin user created:")
            print("  Username: admin")
            print("  Password: admin123")
            print("  (Please change the password after first login!)")

        # Create a regular test user if it doesn't exist
        test_user = User.query.filter_by(username="user").first()

        if test_user:
            print("Test user already exists.")
        else:
            test_user = User(
                username="user",
                email="user@heimdall.local",
                is_admin=False,
                is_suspended=False,
            )
            test_user.set_password("user123")

            db.session.add(test_user)
            db.session.commit()

            print("Test user created:")
            print("  Username: user")
            print("  Password: user123")

        print("\nDatabase initialization complete!")
        print(f"Database location: {app.config.get('SQLALCHEMY_DATABASE_URI')}")


if __name__ == "__main__":
    init_database()
