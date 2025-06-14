import sqlite3
import os

# Determine the absolute path for the database file
# __file__ is /app/ticket_booking/db/database.py
# os.path.abspath(__file__) is /app/ticket_booking/db/database.py
# os.path.dirname() once is /app/ticket_booking/db
# os.path.dirname() twice is /app/ticket_booking
# os.path.dirname() thrice is /app
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_NAME = os.path.join(APP_ROOT, "ticket_booking.db")
DEFAULT_TIMEOUT = 10 # seconds

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME, timeout=DEFAULT_TIMEOUT)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # User Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    )
    ''')

    # Event Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL, -- Store as ISO8601 string or INTEGER timestamp
        venue TEXT NOT NULL,
        total_tickets INTEGER NOT NULL,
        available_tickets INTEGER NOT NULL,
        price REAL NOT NULL
    )
    ''')

    # Booking Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_id INTEGER NOT NULL,
        num_tickets INTEGER NOT NULL,
        booking_date TEXT NOT NULL, -- Store as ISO8601 string
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (event_id) REFERENCES events(id)
    )
    ''')

    # Ticket Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        event_id INTEGER NOT NULL,
        seat_number TEXT, -- Optional
        qr_code TEXT,     -- Optional, could be path or data
        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (event_id) REFERENCES events(id)
        -- No direct FK to user, but through booking
    )
    ''')

    conn.commit()
    conn.close()

def init_db():
    # This function can be called once at application startup
    create_tables()
    print("Database initialized and tables created.")

if __name__ == '__main__':
    # For manual initialization
    init_db()
