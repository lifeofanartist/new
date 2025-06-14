import unittest
import sqlite3 # Import sqlite3 for direct DB manipulation in tests
from ticket_booking.auth import auth_service
from ticket_booking.models import User
from ticket_booking.db import init_db, get_db_connection, DATABASE_NAME # Import db utilities

class TestAuthService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize the database and create tables once for the test class
        # Using a separate test database might be even better, but for now,
        # we'll use the main one and ensure it's clean.
        # For simplicity, we assume DATABASE_NAME is 'ticket_booking.db' or a test-specific DB.
        # If it's the main DB, tests must be careful not to conflict with real data if any.
        init_db()

    def setUp(self):
        # Clear the users table before each test to ensure isolation
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        # It's also good practice to reset autoincrement counters for SQLite if tests rely on specific IDs.
        # However, for these tests, we mostly care about existence and correct data.
        # cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")
        conn.commit()
        conn.close()

    def test_register_user_success(self):
        user = auth_service.register_user("testuser", "password123", "test@example.com")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertIsNotNone(user.id) # ID should be assigned by the DB

        # Verify by fetching from DB directly (optional, but good for confidence)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email FROM users WHERE id = ?", (user.id,))
        db_user = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(db_user)
        self.assertEqual(db_user['username'], "testuser")

    def test_register_user_duplicate_username(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        with self.assertRaisesRegex(ValueError, "Username already exists"):
            auth_service.register_user("testuser", "anotherpassword", "another@example.com")

    def test_register_user_duplicate_email(self):
        auth_service.register_user("testuser1", "password123", "test@example.com")
        with self.assertRaisesRegex(ValueError, "Email already registered"):
            auth_service.register_user("testuser2", "anotherpassword", "test@example.com")

    def test_login_user_success(self):
        # First, register a user
        registered_user = auth_service.register_user("testuser", "password123", "test@example.com")
        # Then, try to login
        logged_in_user = auth_service.login_user("testuser", "password123")
        self.assertIsNotNone(logged_in_user)
        self.assertEqual(logged_in_user.username, "testuser")
        self.assertEqual(logged_in_user.id, registered_user.id)

    def test_login_user_invalid_username(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        user = auth_service.login_user("wronguser", "password123")
        self.assertIsNone(user)

    def test_login_user_invalid_password(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        user = auth_service.login_user("testuser", "wrongpassword")
        self.assertIsNone(user)

    def test_password_hashing(self):
        # This test remains the same as it tests a utility function directly
        password = "securepassword"
        hashed_password = auth_service.hash_password(password)
        self.assertNotEqual(password, hashed_password)
        self.assertTrue(len(hashed_password) > 0)
        self.assertEqual(hashed_password, auth_service.hash_password(password))

if __name__ == '__main__':
    unittest.main()
