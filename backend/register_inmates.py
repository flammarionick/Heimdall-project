#!/usr/bin/env python3
"""
Register inmates from images in the inmate_images folder.
Extracts unique inmates and creates database entries with realistic data.

Usage:
    cd backend
    python register_inmates.py
"""

import os
import sys
import random
from datetime import datetime, timedelta
from collections import defaultdict

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.inmate import Inmate
from app.models.alert import Alert
from app.models.match import Match

# Name mappings based on initials
FIRST_NAMES = {
    'A': ['Aaron', 'Adam', 'Adrian', 'Alan', 'Albert', 'Alex', 'Andrew', 'Anthony', 'Arthur'],
    'B': ['Benjamin', 'Bernard', 'Bradley', 'Brandon', 'Brian', 'Bruce', 'Bryan'],
    'C': ['Calvin', 'Carl', 'Carlos', 'Charles', 'Chris', 'Christopher', 'Clarence', 'Craig'],
    'D': ['Daniel', 'David', 'Dennis', 'Derek', 'Donald', 'Douglas', 'Dwight', 'Dylan'],
    'E': ['Edward', 'Edwin', 'Eric', 'Ernest', 'Eugene', 'Evan'],
    'F': ['Felix', 'Fernando', 'Francis', 'Frank', 'Frederick'],
    'G': ['Gabriel', 'Gary', 'George', 'Gerald', 'Gilbert', 'Gordon', 'Gregory'],
    'H': ['Harold', 'Harry', 'Henry', 'Herbert', 'Howard', 'Hugh'],
    'I': ['Ian', 'Isaac', 'Ivan'],
    'J': ['Jack', 'Jacob', 'James', 'Jason', 'Jeffrey', 'Jeremy', 'Jerome', 'Jesse', 'John', 'Jonathan', 'Joseph', 'Joshua', 'Juan', 'Justin'],
    'K': ['Keith', 'Kenneth', 'Kevin', 'Kyle'],
    'L': ['Larry', 'Lawrence', 'Leonard', 'Lewis', 'Louis', 'Lucas', 'Luis'],
    'M': ['Malcolm', 'Marcus', 'Mark', 'Martin', 'Matthew', 'Maurice', 'Michael', 'Miguel'],
    'N': ['Nathan', 'Nicholas', 'Norman', 'Neil'],
    'O': ['Oliver', 'Oscar', 'Owen'],
    'P': ['Patrick', 'Paul', 'Peter', 'Philip', 'Preston'],
    'Q': ['Quincy', 'Quinn'],
    'R': ['Ralph', 'Randy', 'Raymond', 'Richard', 'Robert', 'Roger', 'Ronald', 'Roy', 'Russell', 'Ryan'],
    'S': ['Samuel', 'Scott', 'Sean', 'Shane', 'Simon', 'Stanley', 'Stephen', 'Steven', 'Stuart'],
    'T': ['Terry', 'Theodore', 'Thomas', 'Timothy', 'Todd', 'Travis', 'Tyler'],
    'U': ['Ulysses'],
    'V': ['Victor', 'Vincent'],
    'W': ['Walter', 'Wayne', 'William', 'Willie'],
    'X': ['Xavier'],
    'Y': ['Yusuf'],
    'Z': ['Zachary'],
}

LAST_NAMES = {
    'A': ['Adams', 'Allen', 'Anderson', 'Armstrong'],
    'B': ['Baker', 'Barnes', 'Bell', 'Bennett', 'Brooks', 'Brown', 'Bryant', 'Butler'],
    'C': ['Campbell', 'Carter', 'Clark', 'Coleman', 'Collins', 'Cook', 'Cooper', 'Cox', 'Cruz'],
    'D': ['Davis', 'Diaz', 'Dixon'],
    'E': ['Edwards', 'Ellis', 'Evans'],
    'F': ['Fisher', 'Flores', 'Ford', 'Foster', 'Freeman'],
    'G': ['Garcia', 'Gibson', 'Gonzalez', 'Gordon', 'Graham', 'Gray', 'Green', 'Griffin'],
    'H': ['Hall', 'Hamilton', 'Harris', 'Harrison', 'Hayes', 'Henderson', 'Henry', 'Hernandez', 'Hill', 'Howard', 'Hughes', 'Hunt'],
    'I': ['Ingram'],
    'J': ['Jackson', 'James', 'Jenkins', 'Johnson', 'Jones', 'Jordan'],
    'K': ['Kelly', 'Kennedy', 'King', 'Knight'],
    'L': ['Lee', 'Lewis', 'Long', 'Lopez'],
    'M': ['Marshall', 'Martin', 'Martinez', 'Mason', 'McDonald', 'Miller', 'Mitchell', 'Moore', 'Morgan', 'Morris', 'Murphy', 'Murray'],
    'N': ['Nelson', 'Newman', 'Nguyen', 'Nichols'],
    'O': ['Oliver', 'Owens'],
    'P': ['Parker', 'Patterson', 'Perez', 'Perry', 'Peterson', 'Phillips', 'Powell', 'Price'],
    'Q': ['Quinn'],
    'R': ['Ramirez', 'Reed', 'Reid', 'Reynolds', 'Richardson', 'Rivera', 'Roberts', 'Robinson', 'Rodriguez', 'Rogers', 'Ross', 'Russell'],
    'S': ['Sanchez', 'Sanders', 'Scott', 'Shaw', 'Simmons', 'Simpson', 'Smith', 'Snyder', 'Spencer', 'Stephens', 'Stevens', 'Stewart', 'Stone', 'Sullivan'],
    'T': ['Taylor', 'Thomas', 'Thompson', 'Torres', 'Turner'],
    'U': ['Underwood'],
    'V': ['Vasquez', 'Valdez'],
    'W': ['Walker', 'Wallace', 'Ward', 'Washington', 'Watson', 'Webb', 'Wells', 'West', 'White', 'Williams', 'Wilson', 'Wood', 'Wright'],
    'X': ['Xavier'],
    'Y': ['Young'],
    'Z': ['Zimmerman'],
}

CRIMES = [
    'Armed Robbery',
    'Assault',
    'Burglary',
    'Drug Trafficking',
    'Fraud',
    'Grand Theft Auto',
    'Kidnapping',
    'Larceny',
    'Money Laundering',
    'Murder',
    'Extortion',
    'Weapons Possession',
    'Identity Theft',
    'Cybercrime',
    'Arson',
    'Breaking and Entering',
]

LOCATIONS = [
    'Kuje Correctional Facility',
    'Kirikiri Maximum Security Prison',
    'Ikoyi Prison',
    'Port Harcourt Prison',
    'Kaduna Convict Prison',
    'Enugu Prison',
    'Ibadan Prison',
    'Benin Prison',
    'Jos Prison',
    'Calabar Prison',
]


def get_name_from_initials(initials):
    """Generate a full name from initials like 'CDJ', 'CS', 'NC'."""
    initials = initials.upper()

    if len(initials) >= 2:
        first_initial = initials[0]
        last_initial = initials[-1]
    else:
        first_initial = initials[0] if initials else 'J'
        last_initial = 'S'

    first_names = FIRST_NAMES.get(first_initial, ['John'])
    last_names = LAST_NAMES.get(last_initial, ['Smith'])

    return f"{random.choice(first_names)} {random.choice(last_names)}"


def register_inmates():
    """Scan inmate_images folder and register each unique inmate."""
    app = create_app()

    with app.app_context():
        # First, clear existing inmates, alerts, and matches
        print("Clearing existing data...")
        Match.query.delete()
        Alert.query.delete()
        Inmate.query.delete()
        db.session.commit()
        print("  Cleared existing inmates, alerts, and matches")

        # Scan the inmate_images folder
        images_dir = os.path.join(os.path.dirname(__file__), 'app', 'static', 'inmate_images')

        if not os.path.exists(images_dir):
            print(f"Error: Images directory not found: {images_dir}")
            return

        # Group images by inmate ID
        inmate_images = defaultdict(list)

        for filename in os.listdir(images_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                # Extract inmate ID from filename (e.g., "CDJ-713551_1.jpg" -> "CDJ-713551")
                base_name = os.path.splitext(filename)[0]

                # Handle both formats: "CDJ-713551_1" and "inmate_1"
                if '_' in base_name:
                    inmate_id = base_name.rsplit('_', 1)[0]
                else:
                    inmate_id = base_name

                inmate_images[inmate_id].append(filename)

        print(f"\nFound {len(inmate_images)} unique inmates from images")

        # Create inmates
        created_count = 0
        for inmate_id, images in inmate_images.items():
            # Sort images to get the first one as primary mugshot
            images.sort()
            primary_image = images[0]

            # Extract initials from inmate_id (e.g., "CDJ-713551" -> "CDJ")
            if '-' in inmate_id:
                initials = inmate_id.split('-')[0]
            else:
                initials = inmate_id[:2].upper()

            # Generate realistic data
            name = get_name_from_initials(initials)
            age = random.randint(22, 55)
            crime = random.choice(CRIMES)
            location = random.choice(LOCATIONS)
            risk_level = random.choices(['High', 'Medium', 'Low'], weights=[20, 50, 30])[0]
            status = random.choices(['Incarcerated', 'Released', 'Escaped'], weights=[75, 20, 5])[0]

            # Random sentence details
            sentence_days = random.randint(180, 3650)  # 6 months to 10 years
            sentence_start = datetime.utcnow() - timedelta(days=random.randint(30, 1000))

            # Last seen based on status
            if status == 'Escaped':
                last_seen = datetime.utcnow() - timedelta(days=random.randint(1, 365))
            elif status == 'Released':
                last_seen = datetime.utcnow() - timedelta(days=random.randint(1, 180))
            else:
                last_seen = datetime.utcnow() - timedelta(hours=random.randint(0, 48))

            # Create the inmate
            inmate = Inmate(
                inmate_id=inmate_id,
                name=name,
                mugshot_path=f'/static/inmate_images/{primary_image}',
                age=age,
                crime=crime,
                risk_level=risk_level,
                location=location,
                sentence_start=sentence_start,
                sentence_duration_days=sentence_days,
                status=status,
                last_seen=last_seen,
            )

            db.session.add(inmate)
            created_count += 1

        db.session.commit()
        print(f"  Created {created_count} inmates")

        # Print summary
        print("\n" + "=" * 50)
        print("Registration Complete!")
        print("=" * 50)

        total = Inmate.query.count()
        incarcerated = Inmate.query.filter_by(status='Incarcerated').count()
        released = Inmate.query.filter_by(status='Released').count()
        escaped = Inmate.query.filter_by(status='Escaped').count()

        print(f"\nInmate Summary:")
        print(f"  Total: {total}")
        print(f"  Incarcerated: {incarcerated}")
        print(f"  Released: {released}")
        print(f"  Escaped: {escaped}")

        # Show some sample inmates
        print(f"\nSample Inmates:")
        for inmate in Inmate.query.limit(5).all():
            print(f"  - {inmate.inmate_id}: {inmate.name} ({inmate.status}) - {inmate.crime}")


if __name__ == "__main__":
    register_inmates()
