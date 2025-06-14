import json
from tests.integration.base_test_api import BaseTestAPI # Inherit from our base class
from datetime import datetime, timedelta

class TestAPIBookings(BaseTestAPI):

    def setUp(self):
        super().setUp() # Call BaseTestAPI's setUp

        # User A (will own events and some bookings)
        self.user_a_creds = {"username": "usera_booking", "password": "passwordA", "email": "usera_booking@example.com"}
        self._register_user(self.user_a_creds)
        login_resp_a = self._login_user({"username": self.user_a_creds["username"], "password": self.user_a_creds["password"]})
        self.user_a_token = login_resp_a.get_json()['access_token']
        self.user_a_id = login_resp_a.get_json()['user_id']

        # User B (will attempt to access User A's stuff and make their own bookings)
        self.user_b_creds = {"username": "userb_booking", "password": "passwordB", "email": "userb_booking@example.com"}
        self._register_user(self.user_b_creds)
        login_resp_b = self._login_user({"username": self.user_b_creds["username"], "password": self.user_b_creds["password"]})
        self.user_b_token = login_resp_b.get_json()['access_token']
        # self.user_b_id = login_resp_b.get_json()['user_id']


        # User A creates an event
        self.event1_data = {
            "name": "Music Festival 2024",
            "date_str": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S"),
            "venue": "Grand Park",
            "total_tickets": 50,
            "price": 120.00
        }
        event_create_resp = self.client.post('/events',
                                             json=self.event1_data,
                                             headers=self._get_auth_headers(self.user_a_token))
        self.event1_id = event_create_resp.get_json()['event']['id']

        self.event2_data = { # Another event with fewer tickets for testing limits
            "name": "Indie Movie Night",
            "date_str": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d %H:%M:%S"),
            "venue": "Cinema Paradiso",
            "total_tickets": 5,
            "price": 15.00
        }
        event2_create_resp = self.client.post('/events',
                                              json=self.event2_data,
                                              headers=self._get_auth_headers(self.user_a_token))
        self.event2_id = event2_create_resp.get_json()['event']['id']


    def test_create_booking_success(self):
        booking_payload = {"event_id": self.event1_id, "num_tickets": 2}
        response = self.client.post('/bookings',
                                     json=booking_payload,
                                     headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['message'], 'Booking created successfully')
        self.assertIn('booking', data)
        self.assertEqual(data['booking']['event_id'], self.event1_id)
        self.assertEqual(data['booking']['num_tickets'], 2)
        self.assertEqual(data['booking']['user_id'], self.user_a_id)
        self.assertIsNotNone(data['booking']['id'])
        self.assertEqual(len(data['booking']['ticket_ids']), 2)

        # Verify available tickets for the event are reduced
        event_resp = self.client.get(f'/events/{self.event1_id}')
        event_data = event_resp.get_json()['event']
        self.assertEqual(event_data['available_tickets'], self.event1_data['total_tickets'] - 2)

    def test_create_booking_no_token(self):
        booking_payload = {"event_id": self.event1_id, "num_tickets": 1}
        response = self.client.post('/bookings', json=booking_payload) # No auth header
        self.assertEqual(response.status_code, 401)

    def test_create_booking_event_not_found(self):
        booking_payload = {"event_id": 99999, "num_tickets": 1}
        response = self.client.post('/bookings',
                                     json=booking_payload,
                                     headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 404) # Service raises ValueError, API maps to 404
        data = response.get_json()
        # Message comes from event_service.decrease_event_available_tickets via booking_service
        self.assertIn("not found for ticket count update", data['error']['message'])


    def test_create_booking_not_enough_tickets(self):
        booking_payload = {"event_id": self.event2_id, "num_tickets": self.event2_data['total_tickets'] + 1}
        response = self.client.post('/bookings',
                                     json=booking_payload,
                                     headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 400) # Changed from 409 to 400 as per app.py logic for "not enough tickets"
        data = response.get_json()
        self.assertIn("Not enough tickets", data['error']['message'])

    def test_create_booking_missing_fields(self):
        response = self.client.post('/bookings',
                                     json={"event_id": self.event1_id},
                                     headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Missing or null required fields: num_tickets", data['error']['message']) # Adjusted message

    def test_get_my_bookings_success(self):
        # User A creates two bookings
        self.client.post('/bookings', json={"event_id": self.event1_id, "num_tickets": 1}, headers=self._get_auth_headers(self.user_a_token))
        self.client.post('/bookings', json={"event_id": self.event2_id, "num_tickets": 1}, headers=self._get_auth_headers(self.user_a_token))

        response = self.client.get('/my-bookings', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['bookings']), 2)

    def test_get_my_bookings_no_bookings(self):
        # User B has no bookings yet
        response = self.client.get('/my-bookings', headers=self._get_auth_headers(self.user_b_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['bookings']), 0)

    def test_get_booking_details_success_owner(self):
        create_resp = self.client.post('/bookings',
                                       json={"event_id": self.event1_id, "num_tickets": 1},
                                       headers=self._get_auth_headers(self.user_a_token))
        booking_id = create_resp.get_json()['booking']['id']

        response = self.client.get(f'/bookings/{booking_id}', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['booking']['id'], booking_id)
        self.assertEqual(data['booking']['user_id'], self.user_a_id)
        self.assertIn('tickets', data['booking']) # Check tickets array is present
        self.assertEqual(len(data['booking']['tickets']), 1)


    def test_get_booking_details_unauthorized_not_owner(self):
        # User A creates a booking
        create_resp = self.client.post('/bookings',
                                       json={"event_id": self.event1_id, "num_tickets": 1},
                                       headers=self._get_auth_headers(self.user_a_token))
        booking_id = create_resp.get_json()['booking']['id']

        # User B tries to access User A's booking
        response = self.client.get(f'/bookings/{booking_id}', headers=self._get_auth_headers(self.user_b_token))
        self.assertEqual(response.status_code, 403) # Forbidden
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Unauthorized to view this booking')

    def test_get_booking_details_not_found(self):
        response = self.client.get('/bookings/99999', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Booking not found')

if __name__ == '__main__':
    unittest.main()
