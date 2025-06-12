import unittest
from ticket_booking.api import booking_service
from ticket_booking.api import event_service # Needed to create events for booking
from ticket_booking.models import Booking, Ticket
from datetime import datetime, timedelta

class TestBookingService(unittest.TestCase):

    def setUp(self):
        # Reset in-memory databases for each test
        booking_service.bookings_db = {}
        booking_service.next_booking_id = 1
        booking_service.tickets_db = {}
        booking_service.next_ticket_id = 1
        event_service.events_db = {} # Crucial: booking service interacts with event_service
        event_service.next_event_id = 1

        # Create a mock user_id for testing
        self.test_user_id = 123

        # Create a sample event for booking tests
        future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        self.sample_event = event_service.create_event(
            "Sample Event", future_date, "Sample Venue", 100, 50.0
        )

    def test_create_booking_success(self):
        booking, tickets = booking_service.create_booking(
            self.test_user_id, self.sample_event.id, 5
        )
        self.assertIsNotNone(booking)
        self.assertEqual(booking.user_id, self.test_user_id)
        self.assertEqual(booking.event_id, self.sample_event.id)
        self.assertEqual(booking.num_tickets, 5)
        self.assertIn(booking.id, booking_service.bookings_db)

        self.assertEqual(len(tickets), 5)
        for ticket in tickets:
            self.assertEqual(ticket.booking_id, booking.id)
            self.assertEqual(ticket.event_id, self.sample_event.id)
            self.assertIn(ticket.id, booking_service.tickets_db)

        # Check if event available tickets are updated
        updated_event = event_service.get_event(self.sample_event.id)
        self.assertEqual(updated_event.available_tickets, self.sample_event.total_tickets - 5)

    def test_create_booking_event_not_found(self):
        with self.assertRaisesRegex(ValueError, "Event not found"):
            booking_service.create_booking(self.test_user_id, 999, 2)

    def test_create_booking_invalid_num_tickets(self):
        with self.assertRaisesRegex(ValueError, "Number of tickets must be a positive integer"):
            booking_service.create_booking(self.test_user_id, self.sample_event.id, 0)
        with self.assertRaisesRegex(ValueError, "Number of tickets must be a positive integer"):
            booking_service.create_booking(self.test_user_id, self.sample_event.id, -1)

    def test_create_booking_not_enough_tickets(self):
        with self.assertRaisesRegex(ValueError, "Not enough tickets available"):
            booking_service.create_booking(self.test_user_id, self.sample_event.id, self.sample_event.total_tickets + 1)

    def test_create_booking_no_user_id(self):
        # Simulate no user_id passed (e.g. user not logged in)
        with self.assertRaisesRegex(ValueError, "User must be logged in to book tickets."):
            booking_service.create_booking(None, self.sample_event.id, 2)


    def test_get_booking_details_found(self):
        booking, _ = booking_service.create_booking(self.test_user_id, self.sample_event.id, 3)
        ret_booking, ret_tickets = booking_service.get_booking_details(booking.id)

        self.assertEqual(ret_booking, booking)
        self.assertEqual(len(ret_tickets), 3)
        for ticket in ret_tickets:
            self.assertEqual(ticket.booking_id, booking.id)

    def test_get_booking_details_not_found(self):
        booking, tickets = booking_service.get_booking_details(999) # Non-existent ID
        self.assertIsNone(booking)
        self.assertEqual(len(tickets), 0)

    def test_get_user_bookings(self):
        booking1, _ = booking_service.create_booking(self.test_user_id, self.sample_event.id, 2)

        # Create another event for a different booking for the same user
        future_date_2 = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
        another_event = event_service.create_event("Another Event", future_date_2, "Venue X", 50, 30)
        booking2, _ = booking_service.create_booking(self.test_user_id, another_event.id, 1)

        # Booking for a different user
        booking_service.create_booking(self.test_user_id + 1, self.sample_event.id, 1)

        user_bookings = booking_service.get_user_bookings(self.test_user_id)
        self.assertEqual(len(user_bookings), 2)
        self.assertIn(booking1, user_bookings)
        self.assertIn(booking2, user_bookings)

if __name__ == '__main__':
    unittest.main()
