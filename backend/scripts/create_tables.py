# scripts/create_tables.py
import sys
from pathlib import Path

# Add backend/ to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()
    print("✅ All tables created!")