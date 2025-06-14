import unittest
import sqlite3
from ticket_booking.api import booking_service
from ticket_booking.api import event_service # For setup and verification
from ticket_booking.auth import auth_service   # Corrected import
from ticket_booking.models import Booking, Ticket
from ticket_booking.db import init_db, get_db_connection, DATABASE_NAME
from datetime import datetime, timedelta

class TestBookingService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        # Clear tables in order of dependencies or disable FKs temporarily for clearing
        cursor.execute("DELETE FROM tickets")
        cursor.execute("DELETE FROM bookings")
        cursor.execute("DELETE FROM events")
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()

        # Setup a default user and event for many tests
        self.test_user = auth_service.register_user("booker", "pass", "booker@test.com")

        event_date_str = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        self.sample_event = event_service.create_event(
            "Bookable Event", event_date_str, "Venue Hall", total_tickets=20, price=50.0
        )

    def test_create_booking_success(self):
        booking, tickets = booking_service.create_booking(
            self.test_user.id, self.sample_event.id, 5
        )
        self.assertIsNotNone(booking)
        self.assertEqual(booking.user_id, self.test_user.id)
        self.assertEqual(booking.event_id, self.sample_event.id)
        self.assertEqual(booking.num_tickets, 5)
        self.assertIsNotNone(booking.id) # DB assigned ID

        self.assertEqual(len(tickets), 5)
        for ticket in tickets:
            self.assertEqual(ticket.booking_id, booking.id)
            self.assertEqual(ticket.event_id, self.sample_event.id)
            self.assertIsNotNone(ticket.id) # DB assigned ID

        # Verify event available tickets are updated
        updated_event = event_service.get_event(self.sample_event.id)
        self.assertEqual(updated_event.available_tickets, self.sample_event.total_tickets - 5) # 20 - 5 = 15

        # Verify booking and tickets exist in DB
        ret_booking, ret_tickets = booking_service.get_booking_details(booking.id)
        self.assertIsNotNone(ret_booking)
        self.assertEqual(len(ret_tickets), 5)

    def test_create_booking_event_not_found(self):
        non_existent_event_id = 9999
        # The error comes from event_service.decrease_event_available_tickets
        with self.assertRaisesRegex(ValueError, f"Event ID {non_existent_event_id} not found for ticket count update."):
            booking_service.create_booking(self.test_user.id, non_existent_event_id, 2)

    def test_create_booking_invalid_num_tickets_zero(self):
        with self.assertRaisesRegex(ValueError, "Number of tickets must be a positive integer"):
            booking_service.create_booking(self.test_user.id, self.sample_event.id, 0)

    def test_create_booking_invalid_num_tickets_negative(self):
        with self.assertRaisesRegex(ValueError, "Number of tickets must be a positive integer"):
            booking_service.create_booking(self.test_user.id, self.sample_event.id, -1)

    def test_create_booking_not_enough_tickets(self):
        # The error comes from event_service.decrease_event_available_tickets
        with self.assertRaisesRegex(ValueError, f"Not enough tickets for event {self.sample_event.id}.*"):
            booking_service.create_booking(self.test_user.id, self.sample_event.id, self.sample_event.total_tickets + 1)

        # Ensure available tickets were not modified
        event_after_failed_booking = event_service.get_event(self.sample_event.id)
        self.assertEqual(event_after_failed_booking.available_tickets, self.sample_event.total_tickets)


    def test_create_booking_invalid_user_id(self):
        with self.assertRaisesRegex(ValueError, "Invalid user ID"):
            booking_service.create_booking(0, self.sample_event.id, 2) # User ID 0

    def test_get_booking_details_found(self):
        booking, _ = booking_service.create_booking(self.test_user.id, self.sample_event.id, 3)
        ret_booking, ret_tickets = booking_service.get_booking_details(booking.id)

        self.assertIsNotNone(ret_booking)
        self.assertEqual(ret_booking.id, booking.id)
        self.assertEqual(len(ret_tickets), 3)
        for ticket in ret_tickets:
            self.assertEqual(ticket.booking_id, booking.id)

    def test_get_booking_details_not_found(self):
        booking, tickets_list = booking_service.get_booking_details(9999) # Non-existent ID
        self.assertIsNone(booking)
        self.assertEqual(len(tickets_list), 0)

    def test_get_user_bookings(self):
        # Create another event for the same user
        event_date_2_str = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
        another_event = event_service.create_event("Another Event", event_date_2_str, "Venue Y", 30, 20)

        booking1, _ = booking_service.create_booking(self.test_user.id, self.sample_event.id, 2)
        booking2, _ = booking_service.create_booking(self.test_user.id, another_event.id, 1)

        # Booking for a different user (should not appear)
        other_user = auth_service.register_user("otheruser", "pass", "other@test.com")
        booking_service.create_booking(other_user.id, self.sample_event.id, 1)

        user_bookings = booking_service.get_user_bookings(self.test_user.id)
        self.assertEqual(len(user_bookings), 2)
        user_booking_ids = [b.id for b in user_bookings]
        self.assertIn(booking1.id, user_booking_ids)
        self.assertIn(booking2.id, user_booking_ids)

    def test_create_booking_transactional_rollback_on_error(self):
        initial_available_tickets = self.sample_event.available_tickets

        # Try to book more tickets than available
        # The error comes from event_service.decrease_event_available_tickets
        with self.assertRaisesRegex(ValueError, f"Not enough tickets for event {self.sample_event.id}.*"):
            booking_service.create_booking(self.test_user.id, self.sample_event.id, initial_available_tickets + 5)

        # Verify that the event's available tickets count has NOT changed
        event_after_failed_booking = event_service.get_event(self.sample_event.id)
        self.assertEqual(event_after_failed_booking.available_tickets, initial_available_tickets)

        # Verify no booking was created for this attempt
        user_bookings = booking_service.get_user_bookings(self.test_user.id)
        self.assertEqual(len(user_bookings), 0)


if __name__ == '__main__':
    unittest.main()
