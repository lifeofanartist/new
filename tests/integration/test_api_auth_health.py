import json
from tests.integration.base_test_api import BaseTestAPI

class TestAPIAuthHealth(BaseTestAPI):

    def test_health_check(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'UP')
        self.assertEqual(data['database'], 'connected')

    def test_register_user_success(self):
        response = self._register_user()
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['message'], 'User registered successfully')
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], self.test_user_credentials['username'])
        self.assertEqual(data['user']['email'], self.test_user_credentials['email'])
        self.assertIsNotNone(data['user']['id'])

    def test_register_user_missing_fields(self):
        response = self.client.post('/register', json={
            "username": "missingemail", "password": "pw"
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Missing or empty required fields: email", data['error']['message']) # Adjusted to match error

    def test_register_user_duplicate_username(self):
        self._register_user(user_data={
            "username": "test_dup_user",
            "password": "password123",
            "email": "original_email@example.com"
        }) # Register first user
        response = self._register_user(user_data={ # Attempt with same username, different email
            "username": "test_dup_user",
            "password": "password456",
            "email": "duplicate_user_new_email@example.com"
        })
        self.assertEqual(response.status_code, 409) # Conflict
        data = response.get_json()
        self.assertIn("Username already exists", data['error']['message'])

    def test_register_user_duplicate_email(self):
        self._register_user(user_data={
            "username": "original_user",
            "password": "password123",
            "email": "test_dup_email@example.com"
        }) # Register first user
        response = self._register_user(user_data={ # Attempt with same email, different username
            "username": "duplicate_email_new_user",
            "password": "password456",
            "email": "test_dup_email@example.com"
        })
        self.assertEqual(response.status_code, 409) # Conflict
        data = response.get_json()
        self.assertIn("Email already registered", data['error']['message'])

    def test_login_success(self):
        self._register_user() # Ensure user exists
        response = self._login_user()
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['message'], 'Login successful')
        self.assertIn('access_token', data)
        self.assertIsNotNone(data['access_token'])
        self.assertIsNotNone(self.access_token) # Check base class stored it

    def test_login_missing_fields(self):
        response = self.client.post('/login', json={"username": "testuser"})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Missing or empty required fields: password", data['error']['message']) # Adjusted

    def test_login_invalid_credentials_wrong_password(self):
        self._register_user()
        response = self.client.post('/login', json={
            "username": self.test_user_credentials['username'],
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Invalid username or password')

    def test_login_user_not_found(self):
        response = self.client.post('/login', json={
            "username": "nouser",
            "password": "password"
        })
        self.assertEqual(response.status_code, 401) # Same response as wrong password
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Invalid username or password')

    def test_protected_route_access_with_token(self):
        self._register_user()
        self._login_user() # This sets self.access_token

        self.assertIsNotNone(self.access_token)
        response = self.client.get('/protected', headers=self._get_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Access granted', data['message'])
        self.assertIsNotNone(data['logged_in_as']) # Should be the user's ID

    def test_protected_route_no_token(self):
        response = self.client.get('/protected')
        self.assertEqual(response.status_code, 401) # JWT unauthorized_loader
        data = response.get_json()
        self.assertIn("Missing Authorization Header", data['error']['message'])

    def test_protected_route_invalid_token(self):
        response = self.client.get('/protected', headers={'Authorization': 'Bearer invalidtoken'})
        self.assertEqual(response.status_code, 422) # JWT invalid_token_loader
        data = response.get_json()
        self.assertIn("Invalid token", data['error']['message'])

if __name__ == '__main__':
    unittest.main()
