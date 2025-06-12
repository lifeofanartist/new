from ticket_booking.models import Ticket
from ticket_booking.api.booking_service import tickets_db # Accessing the in-memory ticket store

def get_ticket_by_id(ticket_id):
    """Retrieves a specific ticket by its ID."""
    return tickets_db.get(ticket_id)

def get_tickets_for_booking(booking_id):
    """Retrieves all tickets associated with a specific booking ID."""
    return [ticket for ticket in tickets_db.values() if ticket.booking_id == booking_id]

def get_tickets_for_event(event_id):
    """Retrieves all tickets associated with a specific event ID."""
    # This can be useful for event organizers to see all tickets sold for an event
    return [ticket for ticket in tickets_db.values() if ticket.event_id == event_id]

# Potential future functions:
# def validate_ticket(ticket_id, event_id):
#     # Logic to check if a ticket is valid for entry to an event
#     pass
# def assign_seat(ticket_id, seat_number):
#     # Logic to assign a seat to a ticket
#     pass
