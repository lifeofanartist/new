from ticket_booking.auth import auth_service
from ticket_booking.api import event_service
from ticket_booking.api import booking_service
from ticket_booking.api import ticket_service
from datetime import datetime

# --- User Authentication Handlers ---
def handle_register_user(payload):
    """
    Simulates handling a user registration request.
    Expected payload: {'username': 'test', 'password': 'pw', 'email': 'test@example.com'}
    """
    try:
        user = auth_service.register_user(
            username=payload['username'],
            password=payload['password'],
            email=payload['email']
        )
        return {'message': 'User registered successfully', 'user_id': user.id}, 201
    except ValueError as e:
        return {'error': str(e)}, 400
    except KeyError as e:
        return {'error': f'Missing field: {str(e)}'}, 400

def handle_login_user(payload):
    """
    Simulates handling a user login request.
    Expected payload: {'username': 'test', 'password': 'pw'}
    """
    try:
        user = auth_service.login_user(
            username=payload['username'],
            password=payload['password']
        )
        if user:
            # In a real API, this would return a session token
            return {'message': 'Login successful', 'user_id': user.id}, 200
        else:
            return {'error': 'Invalid username or password'}, 401
    except KeyError as e:
        return {'error': f'Missing field: {str(e)}'}, 400

# --- Event Management Handlers ---
def handle_create_event(payload):
    """
    Simulates handling an event creation request.
    Expected payload: {'name': 'Concert', 'date_str': 'YYYY-MM-DD HH:MM:SS',
                       'venue': 'Stadium', 'total_tickets': 100, 'price': 50.0}
    """
    try:
        event = event_service.create_event(
            name=payload['name'],
            date_str=payload['date_str'],
            venue=payload['venue'],
            total_tickets=payload['total_tickets'],
            price=payload['price']
        )
        return {'message': 'Event created successfully', 'event_id': event.id}, 201
    except ValueError as e:
        return {'error': str(e)}, 400
    except KeyError as e:
        return {'error': f'Missing field: {str(e)}'}, 400

def handle_get_event(event_id):
    """Simulates handling a request to get a specific event."""
    event = event_service.get_event(int(event_id))
    if event:
        return {
            'id': event.id, 'name': event.name, 'date': event.date.isoformat(),
            'venue': event.venue, 'total_tickets': event.total_tickets,
            'available_tickets': event.available_tickets, 'price': event.price
        }, 200
    else:
        return {'error': 'Event not found'}, 404

def handle_get_all_events():
    """Simulates handling a request to get all events."""
    events = event_service.get_all_events()
    return [{
        'id': event.id, 'name': event.name, 'date': event.date.isoformat(),
        'venue': event.venue, 'total_tickets': event.total_tickets,
        'available_tickets': event.available_tickets, 'price': event.price
    } for event in events], 200

# --- Booking Management Handlers ---
def handle_create_booking(payload):
    """
    Simulates handling a booking creation request.
    Expected payload: {'user_id': 1, 'event_id': 1, 'num_tickets': 2}
    (user_id would typically come from an authenticated session)
    """
    try:
        booking, tickets = booking_service.create_booking(
            user_id=payload['user_id'],
            event_id=payload['event_id'],
            num_tickets=payload['num_tickets']
        )
        return {
            'message': 'Booking successful',
            'booking_id': booking.id,
            'event_id': booking.event_id,
            'num_tickets': booking.num_tickets,
            'booking_date': booking.booking_date.isoformat(),
            'ticket_ids': [ticket.id for ticket in tickets]
        }, 201
    except ValueError as e:
        return {'error': str(e)}, 400
    except KeyError as e:
        return {'error': f'Missing field: {str(e)}'}, 400
    except Exception as e: # Catch other internal errors like event disappearing
        return {'error': f'An internal error occurred: {str(e)}'}, 500


def handle_get_booking_details(booking_id):
    """Simulates handling a request to get booking details."""
    booking, tickets = booking_service.get_booking_details(int(booking_id))
    if booking:
        return {
            'booking_id': booking.id,
            'user_id': booking.user_id,
            'event_id': booking.event_id,
            'num_tickets': booking.num_tickets,
            'booking_date': booking.booking_date.isoformat(),
            'tickets': [{'id': t.id, 'seat_number': t.seat_number} for t in tickets]
        }, 200
    else:
        return {'error': 'Booking not found'}, 404

# --- Ticket Management Handlers ---
def handle_get_ticket(ticket_id):
    """Simulates handling a request to get a specific ticket."""
    ticket = ticket_service.get_ticket_by_id(int(ticket_id))
    if ticket:
        return {
            'id': ticket.id, 'booking_id': ticket.booking_id,
            'event_id': ticket.event_id, 'seat_number': ticket.seat_number
        }, 200
    else:
        return {'error': 'Ticket not found'}, 404

# Add this to ticket_booking/api/__init__.py as well
# from . import handlers
