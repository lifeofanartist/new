import sqlite3 # Make sure this is imported
from ticket_booking.models import User
from ticket_booking.db import get_db_connection # Use our new db connection
import hashlib

# In-memory storage (users_db, next_user_id) should be removed.

def hash_password(password):
    # WARNING: This is a very basic hashing example.
    # In a real application, use a strong, salted hashing library like bcrypt or passlib.
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = hash_password(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        conn.commit()
        user_id = cursor.lastrowid
        # Return a User object, consistent with previous behavior
        created_user = User(id=user_id, username=username, password_hash=password_hash, email=email)
        return created_user
    except sqlite3.IntegrityError as e:
        conn.rollback() # Rollback transaction on error
        if 'UNIQUE constraint failed: users.username' in str(e):
            raise ValueError("Username already exists")
        elif 'UNIQUE constraint failed: users.email' in str(e):
            raise ValueError("Email already registered")
        else:
            # Log the error e for debugging if necessary
            raise ValueError(f"Could not register user due to a database error: {e}")
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    # cursor = conn.cursor() # Not needed if using conn.execute directly and it returns a cursor
    password_hash = hash_password(password)
    try:
        # Using conn.execute directly which returns a cursor
        cursor = conn.execute(
            "SELECT id, username, password_hash, email FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        user_row = cursor.fetchone() # Fetches one row from the cursor
        if user_row:
            # Access by column name due to row_factory = sqlite3.Row in get_db_connection
            return User(id=user_row['id'], username=user_row['username'], password_hash=user_row['password_hash'], email=user_row['email'])
        return None
    except sqlite3.Error as e:
        # Log the error e for debugging
        print(f"Database error during login: {e}")
        return None # Or raise an exception
    finally:
        conn.close()
