import json
from tests.integration.base_test_api import BaseTestAPI # Inherit from our base class
from datetime import datetime, timedelta

class TestAPITickets(BaseTestAPI):

    def setUp(self):
        super().setUp() # Call BaseTestAPI's setUp

        # User A
        self.user_a_creds = {"username": "usera_ticket_test", "password": "passwordA", "email": "usera_ticket@example.com"}
        self._register_user(self.user_a_creds)
        login_resp_a = self._login_user({"username": self.user_a_creds["username"], "password": self.user_a_creds["password"]})
        self.user_a_token = login_resp_a.get_json()['access_token']
        self.user_a_id = login_resp_a.get_json()['user_id']

        # User B
        self.user_b_creds = {"username": "userb_ticket_test", "password": "passwordB", "email": "userb_ticket@example.com"}
        self._register_user(self.user_b_creds)
        login_resp_b = self._login_user({"username": self.user_b_creds["username"], "password": self.user_b_creds["password"]})
        self.user_b_token = login_resp_b.get_json()['access_token']
        # self.user_b_id = login_resp_b.get_json()['user_id']

        # User A creates Event 1
        self.event1_data = {
            "name": "Concert by The Testers",
            "date_str": (datetime.now() + timedelta(days=70)).strftime("%Y-%m-%d %H:%M:%S"),
            "venue": "API Arena", "total_tickets": 10, "price": 60.00
        }
        event1_create_resp = self.client.post('/events', json=self.event1_data, headers=self._get_auth_headers(self.user_a_token))
        self.event1_id = event1_create_resp.get_json()['event']['id']

        # User A makes Booking 1 for Event 1 (2 tickets)
        booking1_payload = {"event_id": self.event1_id, "num_tickets": 2}
        booking1_resp = self.client.post('/bookings', json=booking1_payload, headers=self._get_auth_headers(self.user_a_token))
        self.booking1_id = booking1_resp.get_json()['booking']['id']
        self.booking1_ticket_ids = booking1_resp.get_json()['booking']['ticket_ids'] # List of ticket IDs

        # User B makes Booking 2 for Event 1 (1 ticket)
        booking2_payload = {"event_id": self.event1_id, "num_tickets": 1}
        booking2_resp = self.client.post('/bookings', json=booking2_payload, headers=self._get_auth_headers(self.user_b_token))
        self.booking2_id = booking2_resp.get_json()['booking']['id']
        self.booking2_ticket_ids = booking2_resp.get_json()['booking']['ticket_ids']


    def test_get_ticket_details_success_owner(self):
        ticket_id_to_get = self.booking1_ticket_ids[0]
        response = self.client.get(f'/tickets/{ticket_id_to_get}', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['ticket']['id'], ticket_id_to_get)
        self.assertEqual(data['ticket']['booking_id'], self.booking1_id)
        self.assertEqual(data['ticket']['event_id'], self.event1_id)

    def test_get_ticket_details_unauthorized_not_owner(self):
        ticket_id_to_get = self.booking1_ticket_ids[0] # User A's ticket
        # User B tries to access User A's ticket
        response = self.client.get(f'/tickets/{ticket_id_to_get}', headers=self._get_auth_headers(self.user_b_token))
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Unauthorized to view this ticket')

    def test_get_ticket_details_not_found(self):
        response = self.client.get('/tickets/99999', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Ticket not found')

    def test_get_tickets_for_booking_success_owner(self):
        response = self.client.get(f'/bookings/{self.booking1_id}/tickets', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('tickets', data)
        self.assertEqual(len(data['tickets']), len(self.booking1_ticket_ids)) # Should be 2
        retrieved_ids = sorted([t['id'] for t in data['tickets']])
        self.assertEqual(retrieved_ids, sorted(self.booking1_ticket_ids))

    def test_get_tickets_for_booking_unauthorized_not_owner(self):
        # User B tries to access tickets for User A's booking
        response = self.client.get(f'/bookings/{self.booking1_id}/tickets', headers=self._get_auth_headers(self.user_b_token))
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Unauthorized to view tickets for this booking')

    def test_get_tickets_for_booking_booking_not_found(self):
        response = self.client.get('/bookings/99999/tickets', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Booking not found')

    def test_get_tickets_for_event_success(self):
        # User A (any authenticated user for now) gets tickets for Event 1
        # Event 1 has tickets from Booking 1 (2 tickets) and Booking 2 (1 ticket) = 3 total
        response = self.client.get(f'/events/{self.event1_id}/tickets', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('tickets', data)
        self.assertEqual(len(data['tickets']), 3)

        all_event1_ticket_ids = sorted(self.booking1_ticket_ids + self.booking2_ticket_ids)
        retrieved_ids = sorted([t['id'] for t in data['tickets']])
        self.assertEqual(retrieved_ids, all_event1_ticket_ids)

    def test_get_tickets_for_event_event_not_found(self):
        response = self.client.get('/events/99999/tickets', headers=self._get_auth_headers(self.user_a_token))
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Event not found')

    def test_get_tickets_for_event_no_token(self):
        response = self.client.get(f'/events/{self.event1_id}/tickets') # No auth
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
