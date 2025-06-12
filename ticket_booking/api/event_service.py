from ticket_booking.models import Event
from datetime import datetime

# In-memory storage for events (replace with database later)
events_db = {}
next_event_id = 1

def create_event(name, date_str, venue, total_tickets, price):
    global next_event_id
    # Basic date validation and parsing
    try:
        event_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD HH:MM:SS")

    if event_date < datetime.now():
        raise ValueError("Event date must be in the future.")

    if not isinstance(total_tickets, int) or total_tickets <= 0:
        raise ValueError("Total tickets must be a positive integer.")

    if not isinstance(price, (int, float)) or price < 0:
        raise ValueError("Price must be a non-negative number.")

    event = Event(
        id=next_event_id,
        name=name,
        date=event_date,
        venue=venue,
        total_tickets=total_tickets,
        price=price
    )
    events_db[next_event_id] = event
    next_event_id += 1
    return event

def get_event(event_id):
    return events_db.get(event_id)

def get_all_events():
    return list(events_db.values())

def update_event(event_id, name=None, date_str=None, venue=None, total_tickets=None, price=None):
    event = events_db.get(event_id)
    if not event:
        return None # Or raise ValueError("Event not found")

    if name:
        event.name = name
    if date_str:
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            if event_date < datetime.now(): # Consider allowing updates to past events for record keeping? For now, no.
                raise ValueError("Event date must be in the future.")
            event.date = event_date
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD HH:MM:SS")
    if venue:
        event.venue = venue
    if total_tickets is not None:
        if not isinstance(total_tickets, int) or total_tickets <= 0:
            raise ValueError("Total tickets must be a positive integer.")
        # Adjust available_tickets if total_tickets changes.
        # This can be complex if bookings already exist. For simplicity, assume this is handled carefully.
        # A more robust solution would check against booked tickets.
        event.available_tickets = event.available_tickets + (total_tickets - event.total_tickets)
        event.total_tickets = total_tickets
        if event.available_tickets < 0: # Should not happen with careful adjustment
            event.available_tickets = 0
    if price is not None:
        if not isinstance(price, (int, float)) or price < 0:
            raise ValueError("Price must be a non-negative number.")
        event.price = price

    return event

def delete_event(event_id):
    if event_id in events_db:
        del events_db[event_id]
        return True
    return False
