from ticket_booking.models import Booking, Ticket
from ticket_booking.api import event_service # Import the module
from datetime import datetime

# In-memory storage for bookings and tickets (replace with database later)
bookings_db = {}
tickets_db = {} # Simple ticket store, could be part of bookings_db
next_booking_id = 1
next_ticket_id = 1

def create_booking(user_id, event_id, num_tickets):
    global next_booking_id, next_ticket_id

    event = event_service.get_event(event_id)
    if not event:
        raise ValueError("Event not found.")

    if not isinstance(num_tickets, int) or num_tickets <= 0:
        raise ValueError("Number of tickets must be a positive integer.")

    if event.available_tickets < num_tickets:
        raise ValueError(f"Not enough tickets available. Only {event.available_tickets} left.")

    # Simulate user authentication - in a real app, user_id would come from session/token
    if not user_id: # Basic check
        raise ValueError("User must be logged in to book tickets.")

    # Update available tickets for the event
    # Direct modification of event_service.events_db for simplicity; ideally, this would be through event_service method
    event_in_db = event_service.events_db.get(event_id) # Use event_service.events_db
    if event_in_db:
         event_in_db.available_tickets -= num_tickets
    else:
        # This case should ideally not be reached if get_event works correctly
        raise Exception("Internal error: Event disappeared during booking.")


    booking = Booking(
        id=next_booking_id,
        user_id=user_id,
        event_id=event_id,
        num_tickets=num_tickets
    )
    bookings_db[next_booking_id] = booking

    # Create individual tickets for the booking
    created_tickets = []
    for _ in range(num_tickets):
        ticket = Ticket(
            id=next_ticket_id,
            booking_id=next_booking_id,
            event_id=event_id
            # seat_number and qr_code can be assigned later or based on event type
        )
        tickets_db[next_ticket_id] = ticket
        created_tickets.append(ticket)
        next_ticket_id += 1

    next_booking_id += 1
    return booking, created_tickets

def get_booking_details(booking_id):
    booking = bookings_db.get(booking_id)
    if not booking:
        return None, []

    # Find tickets associated with this booking
    associated_tickets = [t for t in tickets_db.values() if t.booking_id == booking_id]
    return booking, associated_tickets

def get_user_bookings(user_id):
    user_bookings = [b for b in bookings_db.values() if b.user_id == user_id]
    return user_bookings
