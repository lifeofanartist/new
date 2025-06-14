import sqlite3
from ticket_booking.models import Ticket
from ticket_booking.db import get_db_connection

# In-memory storage `tickets_db` was removed when booking_service was refactored.
# This service will now directly query the database.

def _db_row_to_ticket_object(row):
    if not row:
        return None
    return Ticket(
        id=row['id'],
        booking_id=row['booking_id'],
        event_id=row['event_id'],
        seat_number=row['seat_number'], # Will be None if not set
        qr_code=row['qr_code']         # Will be None if not set
    )

def get_ticket_by_id(ticket_id):
    """Retrieves a specific ticket by its ID."""
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return _db_row_to_ticket_object(row)
    except sqlite3.Error as e:
        # Log error e
        print(f"Database error in get_ticket_by_id: {e}")
        return None # Or raise custom error
    finally:
        if conn: conn.close()

def get_tickets_for_booking(booking_id):
    """Retrieves all tickets associated with a specific booking ID."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE booking_id = ? ORDER BY id ASC", (booking_id,)
        ).fetchall()
        return [_db_row_to_ticket_object(row) for row in rows]
    except sqlite3.Error as e:
        # Log error e
        print(f"Database error in get_tickets_for_booking: {e}")
        return [] # Or raise
    finally:
        if conn: conn.close()

def get_tickets_for_event(event_id):
    """Retrieves all tickets associated with a specific event ID."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE event_id = ? ORDER BY id ASC", (event_id,)
        ).fetchall()
        return [_db_row_to_ticket_object(row) for row in rows]
    except sqlite3.Error as e:
        # Log error e
        print(f"Database error in get_tickets_for_event: {e}")
        return [] # Or raise
    finally:
        if conn: conn.close()

# Potential future functions from original plan (still placeholders):
# def validate_ticket(ticket_id, event_id):
#     # Logic to check if a ticket is valid for entry to an event
#     # This would involve fetching the ticket and comparing its event_id, status etc.
#     raise NotImplementedError("validate_ticket is not yet implemented with DB.")
#
# def assign_seat(ticket_id, seat_number):
#     # Logic to assign a seat to a ticket and update DB
#     # conn = get_db_connection()
#     # try:
#     #   conn.execute("UPDATE tickets SET seat_number = ? WHERE id = ?", (seat_number, ticket_id))
#     #   conn.commit()
#     #   return True
#     # except sqlite3.Error:
#     #   conn.rollback()
#     #   return False
#     # finally:
#     #   if conn: conn.close()
#     raise NotImplementedError("assign_seat is not yet implemented with DB.")
