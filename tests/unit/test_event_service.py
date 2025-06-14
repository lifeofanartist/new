import unittest
import sqlite3
from ticket_booking.api import event_service
from ticket_booking.models import Event
from ticket_booking.db import init_db, get_db_connection, DATABASE_NAME
from datetime import datetime, timedelta

class TestEventService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db() # Ensure tables are created

    def setUp(self):
        # Clean relevant tables before each test
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets") # Child table of bookings
        cursor.execute("DELETE FROM bookings") # Child table of events & users
        cursor.execute("DELETE FROM events")
        cursor.execute("DELETE FROM users") # In case any test creates users for FK purposes
        # Reset autoincrement sequences (optional, but good for predictable IDs if needed)
        # cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('events', 'users', 'bookings', 'tickets')")
        conn.commit()
        conn.close()

        # For some tests, we might need a predefined user if event creation/deletion
        # had user-specific logic (not currently the case for event_service itself,
        # but good to keep in mind for future or related tests)

    def _create_sample_event_direct_db(self, conn_passed=None, name="Sample Event", days_in_future=10, total_tickets=100, price=50, venue="Test Venue"):
        conn = conn_passed or get_db_connection()
        event_date = (datetime.now() + timedelta(days=days_in_future)).isoformat()
        cursor = conn.execute(
            "INSERT INTO events (name, date, venue, total_tickets, available_tickets, price) VALUES (?, ?, ?, ?, ?, ?)",
            (name, event_date, venue, total_tickets, total_tickets, price)
        )
        # If conn was passed, the caller is responsible for commit/close
        if not conn_passed:
            conn.commit()
        event_id = cursor.lastrowid
        if not conn_passed:
            conn.close()
        return event_id

    def test_create_event_success(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Tech Conference", future_date_str, "Convention Center", 500, 75.00)
        self.assertIsNotNone(event)
        self.assertEqual(event.name, "Tech Conference")
        self.assertEqual(event.venue, "Convention Center")
        self.assertEqual(event.total_tickets, 500)
        self.assertEqual(event.available_tickets, 500) # Initial available should equal total
        self.assertEqual(event.price, 75.00)
        self.assertIsNotNone(event.id)

        # Verify in DB
        retrieved_event = event_service.get_event(event.id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.name, "Tech Conference")

    def test_create_event_invalid_date_format(self):
        with self.assertRaisesRegex(ValueError, "Invalid date format"):
            event_service.create_event("Workshop", "2023/12/20 10:00:00", "Online", 50, 20)

    def test_create_event_past_date(self):
        past_date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaisesRegex(ValueError, "Event date must be in the future"):
            event_service.create_event("Past Event", past_date_str, "Venue", 100, 10)

    def test_create_event_invalid_tickets(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaisesRegex(ValueError, "Total tickets must be a positive integer"):
            event_service.create_event("Event", future_date_str, "Venue", 0, 10)
        with self.assertRaisesRegex(ValueError, "Total tickets must be a positive integer"):
            event_service.create_event("Event", future_date_str, "Venue", -5, 10)

    def test_create_event_invalid_price(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        with self.assertRaisesRegex(ValueError, "Price must be a non-negative number"):
            event_service.create_event("Event", future_date_str, "Venue", 100, -5)


    def test_get_event_found(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        created_event = event_service.create_event("Test Event", future_date_str, "Test Venue", 100, 25)
        retrieved_event = event_service.get_event(created_event.id)
        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.id, created_event.id)
        self.assertEqual(retrieved_event.name, created_event.name)
        self.assertEqual(retrieved_event.available_tickets, created_event.available_tickets)


    def test_get_event_not_found(self):
        retrieved_event = event_service.get_event(99999) # Non-existent ID
        self.assertIsNone(retrieved_event)

    def test_get_all_events(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event1 = event_service.create_event("Event 1", future_date_str, "Venue 1", 100, 10)
        event2 = event_service.create_event("Event 2", future_date_str, "Venue 2", 200, 20)
        all_events = event_service.get_all_events()
        self.assertEqual(len(all_events), 2)
        event_ids = [e.id for e in all_events]
        self.assertIn(event1.id, event_ids)
        self.assertIn(event2.id, event_ids)

    def test_update_event_success(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Original Name", future_date_str, "Original Venue", 100, 50)

        updated_name = "Updated Name"
        updated_date_str = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
        # Update total tickets and verify available tickets logic
        updated_event = event_service.update_event(
            event.id, name=updated_name, date_str=updated_date_str, total_tickets=150
        )
        self.assertIsNotNone(updated_event)
        self.assertEqual(updated_event.name, updated_name)
        self.assertEqual(updated_event.date, datetime.strptime(updated_date_str, "%Y-%m-%d %H:%M:%S"))
        self.assertEqual(updated_event.total_tickets, 150)
        self.assertEqual(updated_event.available_tickets, 150) # Since no tickets were sold

    def test_update_event_decrease_total_tickets_with_sold_tickets(self):
        event_id = self._create_sample_event_direct_db(total_tickets=100)
        # Simulate some tickets sold by directly updating available_tickets in DB
        conn = get_db_connection()
        conn.execute("UPDATE events SET available_tickets = 80 WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()

        # Now try to update total_tickets to 90 (100 initial, 20 sold, so 80 available)
        # New total is 90. 20 tickets are sold. So, new available should be 90 - 20 = 70.
        updated_event = event_service.update_event(event_id, total_tickets=90)
        self.assertEqual(updated_event.total_tickets, 90)
        self.assertEqual(updated_event.available_tickets, 70)

    def test_update_event_cannot_reduce_total_tickets_below_sold(self):
        event_id = self._create_sample_event_direct_db(total_tickets=100)
        conn = get_db_connection()
        conn.execute("UPDATE events SET available_tickets = 50 WHERE id = ?", (event_id,)) # 50 tickets sold
        conn.commit()
        conn.close()

        with self.assertRaisesRegex(ValueError, "Cannot reduce total_tickets"):
            event_service.update_event(event_id, total_tickets=40) # Trying to set total to less than sold

    def test_delete_event_success_no_bookings(self):
        future_date_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        event = event_service.create_event("Event to Delete", future_date_str, "Venue", 50, 10)
        self.assertTrue(event_service.delete_event(event.id))
        self.assertIsNone(event_service.get_event(event.id))

    def test_delete_event_fails_with_existing_bookings(self):
        conn = get_db_connection() # Connection is now managed here
        try:
            # 1. Create a user (needed for booking foreign key)
            user_cursor = conn.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                                       ("testuser_for_booking", "hash", "booking@test.com"))
            user_id = user_cursor.lastrowid
            # 2. Create an event (pass the connection)
            event_id = self._create_sample_event_direct_db(conn_passed=conn, name="Event With Booking")
            # 3. Create a booking for that event and user
            conn.execute("INSERT INTO bookings (user_id, event_id, num_tickets, booking_date) VALUES (?, ?, ?, ?)",
                         (user_id, event_id, 1, datetime.now().isoformat()))
            conn.commit() # Commit all changes (user, event, booking) together
        finally:
            conn.close() # Ensure connection is closed

        with self.assertRaisesRegex(ValueError, "Cannot delete event .* existing bookings"): # Adjusted regex slightly
            event_service.delete_event(event_id)

    def test_decrease_event_available_tickets_success(self):
        event_id = self._create_sample_event_direct_db(total_tickets=10, price=10) # This call will use its own conn
        self.assertTrue(event_service.decrease_event_available_tickets(event_id, 3))
        event = event_service.get_event(event_id)
        self.assertEqual(event.available_tickets, 7)

    def test_decrease_event_not_enough_tickets(self):
        event_id = self._create_sample_event_direct_db(total_tickets=5)
        # The error message from the service is "Not enough tickets for event {event_id}. Requested: {quantity}, Available: {current_available}"
        with self.assertRaisesRegex(ValueError, f"Not enough tickets for event {event_id}.*"):
            event_service.decrease_event_available_tickets(event_id, 6)

    def test_increase_event_available_tickets_success(self):
        event_id = self._create_sample_event_direct_db(total_tickets=10)
        # First decrease some
        event_service.decrease_event_available_tickets(event_id, 5) # Available = 5
        # Then increase
        self.assertTrue(event_service.increase_event_available_tickets(event_id, 3)) # Available = 8
        event = event_service.get_event(event_id)
        self.assertEqual(event.available_tickets, 8)

    def test_increase_event_beyond_total_capacity(self):
        event_id = self._create_sample_event_direct_db(total_tickets=10)
        # The error message is "Cannot increase available tickets for event {event_id} beyond total capacity."
        with self.assertRaisesRegex(ValueError, f"Cannot increase available tickets for event {event_id} beyond total capacity"):
            event_service.increase_event_available_tickets(event_id, 1) # Trying to make it 11

if __name__ == '__main__':
    unittest.main()
