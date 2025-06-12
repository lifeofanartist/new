import unittest
from ticket_booking.api import event_service
from ticket_booking.models import Event
from datetime import datetime, timedelta

class TestEventService(unittest.TestCase):

    def setUp(self):
        # Reset in-memory database for each test
        event_service.events_db = {}
        event_service.next_event_id = 1

    def test_create_event_success(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Tech Conference", future_date, "Convention Center", 500, 75.00)
        self.assertIsNotNone(event)
        self.assertEqual(event.name, "Tech Conference")
        self.assertEqual(event.venue, "Convention Center")
        self.assertEqual(event.total_tickets, 500)
        self.assertEqual(event.available_tickets, 500)
        self.assertEqual(event.price, 75.00)
        self.assertIn(event.id, event_service.events_db)

    def test_create_event_invalid_date_format(self):
        with self.assertRaisesRegex(ValueError, "Invalid date format"):
            event_service.create_event("Workshop", "2023/12/20 10:00:00", "Online", 50, 20)

    def test_create_event_past_date(self):
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaisesRegex(ValueError, "Event date must be in the future"):
            event_service.create_event("Past Event", past_date, "Venue", 100, 10)

    def test_create_event_invalid_tickets(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaisesRegex(ValueError, "Total tickets must be a positive integer"):
            event_service.create_event("Event", future_date, "Venue", 0, 10)
        with self.assertRaisesRegex(ValueError, "Total tickets must be a positive integer"):
            event_service.create_event("Event", future_date, "Venue", -5, 10)

    def test_create_event_invalid_price(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaisesRegex(ValueError, "Price must be a non-negative number"):
            event_service.create_event("Event", future_date, "Venue", 100, -5)

    def test_get_event_found(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Test Event", future_date, "Test Venue", 100, 25)
        retrieved_event = event_service.get_event(event.id)
        self.assertEqual(retrieved_event, event)

    def test_get_event_not_found(self):
        retrieved_event = event_service.get_event(999) # Non-existent ID
        self.assertIsNone(retrieved_event)

    def test_get_all_events(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event1 = event_service.create_event("Event 1", future_date, "Venue 1", 100, 10)
        event2 = event_service.create_event("Event 2", future_date, "Venue 2", 200, 20)
        all_events = event_service.get_all_events()
        self.assertEqual(len(all_events), 2)
        self.assertIn(event1, all_events)
        self.assertIn(event2, all_events)

    def test_update_event_success(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Original Name", future_date, "Original Venue", 100, 50)

        updated_name = "Updated Name"
        updated_venue = "Updated Venue"
        updated_date_str = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
        updated_total_tickets = 150
        updated_price = 60.0

        updated_event = event_service.update_event(
            event.id,
            name=updated_name,
            date_str=updated_date_str,
            venue=updated_venue,
            total_tickets=updated_total_tickets,
            price=updated_price
        )
        self.assertIsNotNone(updated_event)
        self.assertEqual(updated_event.name, updated_name)
        self.assertEqual(updated_event.venue, updated_venue)
        self.assertEqual(updated_event.date, datetime.strptime(updated_date_str, "%Y-%m-%d %H:%M:%S"))
        self.assertEqual(updated_event.total_tickets, updated_total_tickets)
        # Test available tickets adjustment
        # Original: 100 total, 100 available. New: 150 total. Diff: +50
        # Available should be 100 + 50 = 150
        self.assertEqual(updated_event.available_tickets, 150)
        self.assertEqual(updated_event.price, updated_price)

    def test_update_event_not_found(self):
        updated_event = event_service.update_event(999, name="Non Existent")
        self.assertIsNone(updated_event)

    def test_update_event_total_tickets_adjustment(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Event", future_date, "Venue", 100, 50)
        event.available_tickets = 80 # Simulate some tickets sold

        # Increase total tickets
        updated_event = event_service.update_event(event.id, total_tickets=120)
        self.assertEqual(updated_event.total_tickets, 120)
        self.assertEqual(updated_event.available_tickets, 100) # 80 + (120 - 100)

        # Decrease total tickets
        updated_event = event_service.update_event(event.id, total_tickets=90)
        self.assertEqual(updated_event.total_tickets, 90)
        self.assertEqual(updated_event.available_tickets, 70) # 100 + (90 - 120) -> 100 - 30 = 70

    def test_delete_event_success(self):
        future_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Event to Delete", future_date, "Venue", 50, 10)
        self.assertTrue(event_service.delete_event(event.id))
        self.assertIsNone(event_service.get_event(event.id))
        self.assertNotIn(event.id, event_service.events_db)

    def test_delete_event_not_found(self):
        self.assertFalse(event_service.delete_event(999))

if __name__ == '__main__':
    unittest.main()
