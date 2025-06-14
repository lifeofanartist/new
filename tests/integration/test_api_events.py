import json
from tests.integration.base_test_api import BaseTestAPI # Inherit from our base class
from datetime import datetime, timedelta

class TestAPIEvents(BaseTestAPI):

    def setUp(self):
        super().setUp() # Call BaseTestAPI's setUp to get client and clean DB
        # Register and login a user for authenticated event operations
        self._register_user()
        self._login_user()

        self.sample_event_data = {
            "name": "Tech Conference 2024",
            "date_str": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"),
            "venue": "Convention Center Hall A",
            "total_tickets": 500,
            "price": 75.99
        }

    def test_create_event_success(self):
        response = self.client.post('/events',
                                     json=self.sample_event_data,
                                     headers=self._get_auth_headers())
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['message'], 'Event created successfully')
        self.assertIn('event', data)
        self.assertEqual(data['event']['name'], self.sample_event_data['name'])
        self.assertIsNotNone(data['event']['id'])
        # Store created event_id for other tests if needed, or fetch it
        # For example, self.created_event_id = data['event']['id']

    def test_create_event_missing_fields(self):
        incomplete_data = self.sample_event_data.copy()
        del incomplete_data['name']
        response = self.client.post('/events',
                                     json=incomplete_data,
                                     headers=self._get_auth_headers())
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Missing or invalid required fields", data['error']['message'])

    def test_create_event_unauthorized_no_token(self):
        response = self.client.post('/events', json=self.sample_event_data) # No headers
        self.assertEqual(response.status_code, 401) # Unauthorized by JWT

    def test_get_all_events_empty(self):
        response = self.client.get('/events')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['events']), 0)

    def test_get_all_events_with_data(self):
        # Create an event first
        self.client.post('/events', json=self.sample_event_data, headers=self._get_auth_headers())

        response = self.client.get('/events')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['events']), 1)
        self.assertEqual(data['events'][0]['name'], self.sample_event_data['name'])

    def test_get_specific_event_found(self):
        create_response = self.client.post('/events',
                                           json=self.sample_event_data,
                                           headers=self._get_auth_headers())
        event_id = create_response.get_json()['event']['id']

        response = self.client.get(f'/events/{event_id}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['event']['id'], event_id)
        self.assertEqual(data['event']['name'], self.sample_event_data['name'])

    def test_get_specific_event_not_found(self):
        response = self.client.get('/events/99999') # Non-existent ID
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data['error']['message'], 'Event not found')

    def test_update_event_success(self):
        create_response = self.client.post('/events',
                                           json=self.sample_event_data,
                                           headers=self._get_auth_headers())
        event_id = create_response.get_json()['event']['id']

        update_data = {"name": "Updated Tech Conference Name", "price": 89.99}
        response = self.client.put(f'/events/{event_id}',
                                    json=update_data,
                                    headers=self._get_auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['event']['name'], update_data['name'])
        self.assertEqual(data['event']['price'], update_data['price'])
        self.assertEqual(data['event']['venue'], self.sample_event_data['venue']) # Check unchanged field

    def test_update_event_not_found(self):
        update_data = {"name": "Won't Update"}
        response = self.client.put('/events/99999',
                                    json=update_data,
                                    headers=self._get_auth_headers())
        self.assertEqual(response.status_code, 404)

    def test_update_event_unauthorized_no_token(self):
        # Create an event first to get an ID
        create_response = self.client.post('/events',
                                           json=self.sample_event_data,
                                           headers=self._get_auth_headers())
        event_id = create_response.get_json()['event']['id']

        update_data = {"name": "No Token Update"}
        response = self.client.put(f'/events/{event_id}', json=update_data) # No headers
        self.assertEqual(response.status_code, 401)

    def test_delete_event_success(self):
        create_response = self.client.post('/events',
                                           json=self.sample_event_data,
                                           headers=self._get_auth_headers())
        event_id = create_response.get_json()['event']['id']

        response = self.client.delete(f'/events/{event_id}', headers=self._get_auth_headers())
        self.assertEqual(response.status_code, 204) # No Content

        # Verify it's gone
        get_response = self.client.get(f'/events/{event_id}')
        self.assertEqual(get_response.status_code, 404)

    def test_delete_event_not_found(self):
        response = self.client.delete('/events/99999', headers=self._get_auth_headers())
        # The current app.py's delete_event_endpoint returns 400 for "Event not found" from service if delete_event returns False
        # However, the service's delete_event raises ValueError if not found.
        # Let's check app.py: if service.delete_event() returns True, 204. Else, 404.
        # If service.delete_event() raises ValueError and that's "not found", it's 400.
        # The prompt's app.py for delete event:
        #    except ValueError as e: # Catches "event has bookings" or other specific value errors
        #        if "Cannot delete event" in str(e) and "existing bookings" in str(e): abort(409, description=str(e))
        #        else: abort(400, description=str(e)) -> This would be the case for "not found" from service.
        # Let's align with what the app.py does for delete_event service errors for consistency.
        # If event_service.delete_event raises ValueError "Event ID {event_id} not found for deletion."
        # Then the API will return 400.
        # If event_service.delete_event returns False (not the current impl), API returns 404.
        # Current event_service.delete_event raises ValueError for "not found" as part of "Could not delete event: Event ID X not found".
        # This will be caught by the ValueError handler in the endpoint, which returns 400.
        # If delete_event returns False (e.g. rowcount == 0 from DELETE), the endpoint returns 404.
        # Given current service `delete_event` raises ValueError for "not found", then 400 is expected.
        # Let's assume the service `delete_event` itself returns False for not found, and the endpoint returns 404.
        # The app.py has:
        #    if event_service.delete_event(event_id): return '', 204
        #    else: abort(404, description="Event not found.") -> This is if delete_event returns False for not found.
        #    ValueError: if "Cannot delete" -> 409, else 400.
        # The service `delete_event` was:
        #   cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        #   return cursor.rowcount > 0
        # This means it returns False if not found and no error. So endpoint makes it 404.
        self.assertEqual(response.status_code, 404)


    def test_delete_event_unauthorized_no_token(self):
        create_response = self.client.post('/events',
                                           json=self.sample_event_data,
                                           headers=self._get_auth_headers())
        event_id = create_response.get_json()['event']['id']

        response = self.client.delete(f'/events/{event_id}') # No headers
        self.assertEqual(response.status_code, 401)

    # Add test for deleting event with bookings later, once booking API tests are also added
    # def test_delete_event_with_bookings_conflict(self):
    #     # 1. Create event
    #     # 2. Create booking for that event
    #     # 3. Attempt to delete event
    #     # 4. Expect 409 Conflict
    #     pass

if __name__ == '__main__':
    unittest.main()
