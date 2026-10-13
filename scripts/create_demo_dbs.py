"""Create demo SQLite databases for testing."""
import sqlite3
from pathlib import Path

DEMO_DIR = Path("artifacts/demo_dbs")
DEMO_DIR.mkdir(parents=True, exist_ok=True)

# Concert Singer Database
def create_concert_singer():
    db_path = DEMO_DIR / "concert_singer" / "concert_singer.sqlite"
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS singer (
            singer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            birth_year INTEGER,
            net_worth_millions REAL,
            citizenship TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS concert (
            concert_id INTEGER PRIMARY KEY,
            concert_name TEXT NOT NULL,
            theme TEXT,
            stadium_id INTEGER,
            year INTEGER
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS singer_in_concert (
            concert_id INTEGER,
            singer_id INTEGER,
            PRIMARY KEY (concert_id, singer_id)
        )
    """)
    
    # Insert sample data
    singers = [
        (1, "John Smith", 1985, 15.5, "USA"),
        (2, "Maria Garcia", 1990, 8.2, "Spain"),
        (3, "Chen Wei", 1988, 12.0, "China"),
        (4, "Sarah Johnson", 1992, 6.5, "UK"),
        (5, "Ahmed Hassan", 1987, 10.3, "Egypt"),
    ]
    cur.executemany("INSERT OR REPLACE INTO singer VALUES (?, ?, ?, ?, ?)", singers)
    
    concerts = [
        (1, "Summer Festival", "Pop", 1, 2023),
        (2, "Rock Night", "Rock", 2, 2023),
        (3, "Classical Evening", "Classical", 1, 2024),
        (4, "Jazz Showcase", "Jazz", 3, 2024),
    ]
    cur.executemany("INSERT OR REPLACE INTO concert VALUES (?, ?, ?, ?, ?)", concerts)
    
    singer_concerts = [
        (1, 1), (1, 2), (2, 3), (2, 4),
        (3, 1), (3, 5), (4, 2),
    ]
    cur.executemany("INSERT OR REPLACE INTO singer_in_concert VALUES (?, ?)", singer_concerts)
    
    conn.commit()
    conn.close()
    print(f"✓ Created {db_path}")

# Pets Database
def create_pets():
    db_path = DEMO_DIR / "pets_1" / "pets_1.sqlite"
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student (
            student_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            age INTEGER,
            sex TEXT,
            major TEXT,
            advisor INTEGER
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS has_pet (
            student_id INTEGER,
            pet_id INTEGER,
            PRIMARY KEY (student_id, pet_id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pets (
            pet_id INTEGER PRIMARY KEY,
            pet_type TEXT,
            pet_age INTEGER,
            weight REAL
        )
    """)
    
    students = [
        (1, "Alice", "Brown", 20, "F", "Computer Science", 101),
        (2, "Bob", "Wilson", 22, "M", "Mathematics", 102),
        (3, "Carol", "Davis", 21, "F", "Biology", 103),
        (4, "David", "Miller", 23, "M", "Physics", 101),
        (5, "Eve", "Taylor", 19, "F", "Chemistry", 102),
    ]
    cur.executemany("INSERT OR REPLACE INTO student VALUES (?, ?, ?, ?, ?, ?, ?)", students)
    
    pets = [
        (1, "cat", 3, 4.5),
        (2, "dog", 5, 12.3),
        (3, "cat", 2, 3.8),
        (4, "dog", 7, 15.2),
        (5, "rabbit", 1, 2.1),
        (6, "cat", 4, 5.0),
    ]
    cur.executemany("INSERT OR REPLACE INTO pets VALUES (?, ?, ?, ?)", pets)
    
    has_pets = [
        (1, 1), (1, 3), (2, 2), (3, 5), (4, 4), (5, 6),
    ]
    cur.executemany("INSERT OR REPLACE INTO has_pet VALUES (?, ?)", has_pets)
    
    conn.commit()
    conn.close()
    print(f"✓ Created {db_path}")

# Car Database
def create_car():
    db_path = DEMO_DIR / "car_1" / "car_1.sqlite"
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS car_makers (
            id INTEGER PRIMARY KEY,
            maker TEXT,
            full_name TEXT,
            country TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS car_names (
            make_id INTEGER,
            model TEXT,
            make TEXT,
            PRIMARY KEY (make_id, model)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cars_data (
            id INTEGER PRIMARY KEY,
            mpg REAL,
            cylinders INTEGER,
            edispl REAL,
            horsepower INTEGER,
            weight INTEGER,
            accelerate REAL,
            year INTEGER
        )
    """)
    
    makers = [
        (1, "toyota", "Toyota Motor Corporation", "Japan"),
        (2, "ford", "Ford Motor Company", "USA"),
        (3, "bmw", "BMW AG", "Germany"),
        (4, "honda", "Honda Motor Company", "Japan"),
        (5, "chevrolet", "Chevrolet", "USA"),
    ]
    cur.executemany("INSERT OR REPLACE INTO car_makers VALUES (?, ?, ?, ?)", makers)
    
    models = [
        (1, "camry", "toyota"),
        (1, "corolla", "toyota"),
        (2, "mustang", "ford"),
        (2, "f-150", "ford"),
        (3, "3 series", "bmw"),
        (4, "civic", "honda"),
        (4, "accord", "honda"),
        (5, "corvette", "chevrolet"),
    ]
    cur.executemany("INSERT OR REPLACE INTO car_names VALUES (?, ?, ?)", models)
    
    cars = [
        (1, 28.5, 4, 2.5, 185, 3200, 8.5, 2023),
        (2, 32.0, 4, 2.0, 168, 2900, 9.0, 2023),
        (3, 20.0, 8, 5.0, 450, 3800, 4.5, 2023),
        (4, 18.0, 6, 3.5, 290, 4200, 6.0, 2023),
        (5, 22.0, 6, 3.0, 320, 3600, 5.5, 2023),
    ]
    cur.executemany("INSERT OR REPLACE INTO cars_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)", cars)
    
    conn.commit()
    conn.close()
    print(f"✓ Created {db_path}")

# Flight Database
def create_flight():
    db_path = DEMO_DIR / "flight_2" / "flight_2.sqlite"
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS airlines (
            uid INTEGER PRIMARY KEY,
            airline TEXT,
            abbreviation TEXT,
            country TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS airports (
            city TEXT,
            airport_code TEXT PRIMARY KEY,
            airport_name TEXT,
            country TEXT
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flights (
            airline INTEGER,
            flight_number INTEGER,
            source_airport TEXT,
            destination_airport TEXT,
            PRIMARY KEY (airline, flight_number)
        )
    """)
    
    airlines = [
        (1, "United Airlines", "UA", "USA"),
        (2, "American Airlines", "AA", "USA"),
        (3, "Delta Air Lines", "DL", "USA"),
        (4, "JetBlue Airways", "B6", "USA"),
        (5, "Southwest Airlines", "WN", "USA"),
    ]
    cur.executemany("INSERT OR REPLACE INTO airlines VALUES (?, ?, ?, ?)", airlines)
    
    airports = [
        ("New York", "JFK", "John F. Kennedy International Airport", "USA"),
        ("Los Angeles", "LAX", "Los Angeles International Airport", "USA"),
        ("Chicago", "ORD", "O'Hare International Airport", "USA"),
        ("San Francisco", "SFO", "San Francisco International Airport", "USA"),
        ("Miami", "MIA", "Miami International Airport", "USA"),
    ]
    cur.executemany("INSERT OR REPLACE INTO airports VALUES (?, ?, ?, ?)", airports)
    
    flights = [
        (1, 100, "JFK", "LAX"),
        (1, 200, "LAX", "ORD"),
        (2, 300, "ORD", "MIA"),
        (2, 400, "MIA", "SFO"),
        (3, 500, "SFO", "JFK"),
        (4, 600, "JFK", "MIA"),
        (5, 700, "LAX", "SFO"),
    ]
    cur.executemany("INSERT OR REPLACE INTO flights VALUES (?, ?, ?, ?)", flights)
    
    conn.commit()
    conn.close()
    print(f"✓ Created {db_path}")

if __name__ == "__main__":
    print("Creating demo databases...")
    create_concert_singer()
    create_pets()
    create_car()
    create_flight()
    print("\n✅ All demo databases created successfully!")
