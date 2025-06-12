import unittest
from ticket_booking.api import ticket_service
from ticket_booking.api import booking_service # To create prerequisite data
from ticket_booking.api import event_service   # To create prerequisite data
from datetime import datetime, timedelta

class TestTicketService(unittest.TestCase):

    def setUp(self):
        # Reset in-memory databases
        ticket_service.tickets_db = {} # ticket_service uses booking_service.tickets_db
        booking_service.tickets_db = ticket_service.tickets_db # Ensure they share the same dict
        booking_service.bookings_db = {}
        booking_service.next_booking_id = 1
        booking_service.next_ticket_id = 1
        event_service.events_db = {}
        event_service.next_event_id = 1

        # Create sample data
        self.test_user_id = 1
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        self.event1 = event_service.create_event("Event 1", future_date, "Venue 1", 10, 100)
        self.booking1, self.tickets1 = booking_service.create_booking(self.test_user_id, self.event1.id, 2) # 2 tickets

        self.event2 = event_service.create_event("Event 2", future_date, "Venue 2", 5, 50)
        self.booking2, self.tickets2 = booking_service.create_booking(self.test_user_id, self.event2.id, 3) # 3 tickets


    def test_get_ticket_by_id_found(self):
        sample_ticket = self.tickets1[0]
        retrieved_ticket = ticket_service.get_ticket_by_id(sample_ticket.id)
        self.assertEqual(retrieved_ticket, sample_ticket)

    def test_get_ticket_by_id_not_found(self):
        retrieved_ticket = ticket_service.get_ticket_by_id(999)
        self.assertIsNone(retrieved_ticket)

    def test_get_tickets_for_booking(self):
        retrieved_tickets = ticket_service.get_tickets_for_booking(self.booking1.id)
        self.assertEqual(len(retrieved_tickets), len(self.tickets1))
        for t in self.tickets1:
            self.assertIn(t, retrieved_tickets)

        retrieved_tickets_b2 = ticket_service.get_tickets_for_booking(self.booking2.id)
        self.assertEqual(len(retrieved_tickets_b2), len(self.tickets2))


    def test_get_tickets_for_booking_no_tickets(self):
        # A booking ID that exists but somehow has no tickets (shouldn't happen with current logic)
        # or a booking ID that doesn't exist
        retrieved_tickets = ticket_service.get_tickets_for_booking(998) # Non-existent booking
        self.assertEqual(len(retrieved_tickets), 0)

    def test_get_tickets_for_event(self):
        # Event 1 has tickets from booking1
        event1_tickets = ticket_service.get_tickets_for_event(self.event1.id)
        self.assertEqual(len(event1_tickets), len(self.tickets1))
        for t in self.tickets1:
            self.assertIn(t, event1_tickets)

        # Event 2 has tickets from booking2
        event2_tickets = ticket_service.get_tickets_for_event(self.event2.id)
        self.assertEqual(len(event2_tickets), len(self.tickets2))
        for t in self.tickets2:
            self.assertIn(t, event2_tickets)

    def test_get_tickets_for_event_no_tickets(self):
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        event_no_tickets = event_service.create_event("Event No Tickets", future_date, "Venue NoTix", 10, 10)
        retrieved_tickets = ticket_service.get_tickets_for_event(event_no_tickets.id)
        self.assertEqual(len(retrieved_tickets), 0)


if __name__ == '__main__':
    unittest.main()
