import unittest
import sqlite3
from ticket_booking.api import ticket_service
from ticket_booking.api import booking_service # To create prerequisite data
from ticket_booking.api import event_service   # To create prerequisite data
from ticket_booking.auth import auth_service    # To create prerequisite data (corrected import)
from ticket_booking.db import init_db, get_db_connection, DATABASE_NAME
from datetime import datetime, timedelta

class TestTicketService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        # Clean relevant tables before each test
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets")
        cursor.execute("DELETE FROM bookings")
        cursor.execute("DELETE FROM events")
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()

        # Setup common data: user, event, booking, and tickets
        self.test_user = auth_service.register_user("ticket_tester", "pass", "ticketer@test.com")

        event_date_str = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        self.event1 = event_service.create_event("Event For Tickets 1", event_date_str, "Venue Alpha", 10, 100)
        self.event2 = event_service.create_event("Event For Tickets 2", event_date_str, "Venue Beta", 5, 50)

        # Create bookings and capture the generated tickets
        # Booking 1 for Event 1 (2 tickets)
        self.booking1, self.booking1_tickets = booking_service.create_booking(
            self.test_user.id, self.event1.id, 2
        )
        # Booking 2 for Event 2 (3 tickets)
        self.booking2, self.booking2_tickets = booking_service.create_booking(
            self.test_user.id, self.event2.id, 3
        )
        # Booking 3 for Event 1 by another user (1 ticket)
        other_user = auth_service.register_user("other_ticketer", "pass", "other_ticketer@test.com")
        self.booking3, self.booking3_tickets = booking_service.create_booking(
            other_user.id, self.event1.id, 1
        )


    def test_get_ticket_by_id_found(self):
        # Get one of the tickets created in setUp
        sample_ticket_id = self.booking1_tickets[0].id
        retrieved_ticket = ticket_service.get_ticket_by_id(sample_ticket_id)
        self.assertIsNotNone(retrieved_ticket)
        self.assertEqual(retrieved_ticket.id, sample_ticket_id)
        self.assertEqual(retrieved_ticket.booking_id, self.booking1.id)
        self.assertEqual(retrieved_ticket.event_id, self.event1.id)

    def test_get_ticket_by_id_not_found(self):
        retrieved_ticket = ticket_service.get_ticket_by_id(99999) # Non-existent ID
        self.assertIsNone(retrieved_ticket)

    def test_get_tickets_for_booking_found(self):
        # Test for booking1
        retrieved_tickets_b1 = ticket_service.get_tickets_for_booking(self.booking1.id)
        self.assertEqual(len(retrieved_tickets_b1), 2) # booking1_tickets has 2 tickets
        retrieved_ticket_ids_b1 = sorted([t.id for t in retrieved_tickets_b1])
        expected_ticket_ids_b1 = sorted([t.id for t in self.booking1_tickets])
        self.assertListEqual(retrieved_ticket_ids_b1, expected_ticket_ids_b1)

        # Test for booking2
        retrieved_tickets_b2 = ticket_service.get_tickets_for_booking(self.booking2.id)
        self.assertEqual(len(retrieved_tickets_b2), 3) # booking2_tickets has 3 tickets
        retrieved_ticket_ids_b2 = sorted([t.id for t in retrieved_tickets_b2])
        expected_ticket_ids_b2 = sorted([t.id for t in self.booking2_tickets])
        self.assertListEqual(retrieved_ticket_ids_b2, expected_ticket_ids_b2)


    def test_get_tickets_for_booking_not_found_or_no_tickets(self):
        # Booking ID that doesn't exist
        retrieved_tickets = ticket_service.get_tickets_for_booking(88888)
        self.assertEqual(len(retrieved_tickets), 0)

    def test_get_tickets_for_event_found(self):
        # Event 1 has tickets from booking1 (2 tickets) and booking3 (1 ticket) = 3 tickets total
        event1_tickets_from_service = ticket_service.get_tickets_for_event(self.event1.id)
        self.assertEqual(len(event1_tickets_from_service), 3)

        # Combine tickets from setup for event1 to form the expected list
        expected_event1_ticket_ids = sorted(
            [t.id for t in self.booking1_tickets] + [t.id for t in self.booking3_tickets]
        )
        retrieved_event1_ticket_ids = sorted([t.id for t in event1_tickets_from_service])
        self.assertListEqual(retrieved_event1_ticket_ids, expected_event1_ticket_ids)

        # Event 2 has tickets from booking2 (3 tickets)
        event2_tickets_from_service = ticket_service.get_tickets_for_event(self.event2.id)
        self.assertEqual(len(event2_tickets_from_service), 3)
        retrieved_event2_ticket_ids = sorted([t.id for t in event2_tickets_from_service])
        expected_event2_ticket_ids = sorted([t.id for t in self.booking2_tickets])
        self.assertListEqual(retrieved_event2_ticket_ids, expected_event2_ticket_ids)

    def test_get_tickets_for_event_no_tickets(self):
        # Create an event with no bookings/tickets
        event_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        event_no_tickets = event_service.create_event("Event No Tickets", event_date_str, "Venue Empty", 10, 10)

        retrieved_tickets = ticket_service.get_tickets_for_event(event_no_tickets.id)
        self.assertEqual(len(retrieved_tickets), 0)

if __name__ == '__main__':
    unittest.main()
