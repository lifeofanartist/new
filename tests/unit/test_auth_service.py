import unittest
from ticket_booking.auth import auth_service
from ticket_booking.models import User

class TestAuthService(unittest.TestCase):

    def setUp(self):
        # Reset in-memory database for each test
        auth_service.users_db = {}
        auth_service.next_user_id = 1

    def test_register_user_success(self):
        user = auth_service.register_user("testuser", "password123", "test@example.com")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertIn("testuser", auth_service.users_db)
        self.assertEqual(auth_service.users_db["testuser"].id, 1)

    def test_register_user_duplicate_username(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        with self.assertRaisesRegex(ValueError, "Username already exists"):
            auth_service.register_user("testuser", "anotherpassword", "another@example.com")

    def test_login_user_success(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        user = auth_service.login_user("testuser", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")

    def test_login_user_invalid_username(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        user = auth_service.login_user("wronguser", "password123")
        self.assertIsNone(user)

    def test_login_user_invalid_password(self):
        auth_service.register_user("testuser", "password123", "test@example.com")
        user = auth_service.login_user("testuser", "wrongpassword")
        self.assertIsNone(user)

    def test_password_hashing(self):
        # This is a basic test. In real scenarios, you don't test the hash function itself
        # but that it's applied.
        password = "securepassword"
        hashed_password = auth_service.hash_password(password)
        self.assertNotEqual(password, hashed_password)
        self.assertTrue(len(hashed_password) > 0) # Basic check for non-empty hash
        # Check that the same password yields the same hash (deterministic for sha256 without salt)
        self.assertEqual(hashed_password, auth_service.hash_password(password))

if __name__ == '__main__':
    unittest.main()
