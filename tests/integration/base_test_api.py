import unittest
import os
# Import the Flask app instance from your main app file
# Assuming your app.py is in the root and 'app' is the Flask instance
from app import app
from ticket_booking.db import init_db, get_db_connection

class BaseTestAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Configure the app for testing
        app.config['TESTING'] = True
        # Use a separate database for testing if desired, or ensure the main one is clean.
        # For simplicity, we'll use the same DB defined by DATABASE_NAME but ensure it's clean.
        # Example: app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' or a test DB file
        # For now, we rely on init_db() and cleaning tables.

        # Ensure the database is initialized
        # In a real test suite, you might have a dedicated test DB configuration
        # For this project, init_db() creates tables if they don't exist.
        with app.app_context():
            init_db()

    def setUp(self):
        # Get a test client for the app
        self.client = app.test_client()

        # Clean database tables before each test
        with app.app_context():
            conn = get_db_connection()
            cursor = conn.cursor()
            # Order matters due to foreign key constraints
            cursor.execute("DELETE FROM tickets")
            cursor.execute("DELETE FROM bookings")
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM users")
            conn.commit()
            conn.close()

        self.test_user_credentials = {
            "username": "testuser_api",
            "password": "password123",
            "email": "testuser_api@example.com"
        }
        self.access_token = None # To store token for protected routes

    def tearDown(self):
        # Can add cleanup here if needed after each test,
        # but cleaning tables in setUp is usually sufficient.
        pass

    def _register_user(self, user_data=None):
        if user_data is None:
            user_data = self.test_user_credentials
        return self.client.post('/register', json=user_data)

    def _login_user(self, credentials=None):
        if credentials is None:
            credentials = {"username": self.test_user_credentials["username"],
                           "password": self.test_user_credentials["password"]}
        response = self.client.post('/login', json=credentials)
        if response.status_code == 200:
            data = response.get_json()
            self.access_token = data.get('access_token')
        return response

    def _get_auth_headers(self, token=None):
        token_to_use = token if token else self.access_token
        if not token_to_use:
            # Potentially log a warning or raise an error if token is expected but not found
            print("Warning: No access token available for authenticated request.")
            return {}
        return {'Authorization': f'Bearer {token_to_use}'}
