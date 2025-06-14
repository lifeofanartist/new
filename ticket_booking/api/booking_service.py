import sqlite3
from ticket_booking.models import Booking, Ticket
from ticket_booking.db import get_db_connection
from ticket_booking.api import event_service # For event operations
from datetime import datetime

# In-memory storage (bookings_db, tickets_db, next_booking_id, next_ticket_id) removed.

def _db_row_to_booking_object(row):
    if not row:
        return None
    return Booking(
        id=row['id'],
        user_id=row['user_id'],
        event_id=row['event_id'],
        num_tickets=row['num_tickets'],
        booking_date=datetime.fromisoformat(row['booking_date'])
    )

def _db_row_to_ticket_object(row):
    if not row:
        return None
    return Ticket(
        id=row['id'],
        booking_id=row['booking_id'],
        event_id=row['event_id'],
        seat_number=row['seat_number'], # Assuming seat_number can be None
        qr_code=row['qr_code']         # Assuming qr_code can be None
    )

def create_booking(user_id, event_id, num_tickets):
    # Validate inputs
    if not isinstance(user_id, int) or user_id <= 0: # Basic check for user_id
        raise ValueError("Invalid user ID.")
    if not isinstance(event_id, int) or event_id <= 0:
        raise ValueError("Invalid event ID.")
    if not isinstance(num_tickets, int) or num_tickets <= 0:
        raise ValueError("Number of tickets must be a positive integer.")

    conn = get_db_connection()
    try:
        conn.execute("BEGIN") # Start transaction

        # 1. Check if the event exists and has enough tickets (using event_service logic)
        #    No need to call get_event directly here if decrease_event_available_tickets handles it.
        #    The decrease_event_available_tickets will raise ValueError if event not found or not enough tickets.

        # 2. Attempt to decrease event ticket count using event_service within the transaction
        #    This function will raise an error if not enough tickets are available.
        event_service.decrease_event_available_tickets(event_id, num_tickets, conn_passed=conn)

        # 3. If ticket count updated successfully, create the booking record
        booking_date_iso = datetime.utcnow().isoformat()
        booking_cursor = conn.execute(
            "INSERT INTO bookings (user_id, event_id, num_tickets, booking_date) VALUES (?, ?, ?, ?)",
            (user_id, event_id, num_tickets, booking_date_iso)
        )
        booking_id = booking_cursor.lastrowid

        # 4. Create individual ticket records for the booking
        created_tickets_objects = []
        for _ in range(num_tickets):
            # Seat number and QR code are not assigned at booking creation in this basic model
            ticket_cursor = conn.execute(
                "INSERT INTO tickets (booking_id, event_id, seat_number, qr_code) VALUES (?, ?, ?, ?)",
                (booking_id, event_id, None, None)
            )
            ticket_id = ticket_cursor.lastrowid
            # Create Ticket object to return, though not strictly necessary if only IDs are needed
            created_tickets_objects.append(Ticket(id=ticket_id, booking_id=booking_id, event_id=event_id))

        conn.commit() # Commit transaction

        # Construct Booking object to return
        booking_obj = Booking(
            id=booking_id,
            user_id=user_id,
            event_id=event_id,
            num_tickets=num_tickets,
            booking_date=datetime.fromisoformat(booking_date_iso)
        )
        return booking_obj, created_tickets_objects

    except ValueError as ve: # Catch ValueErrors from decrease_event_available_tickets or input validation
        if conn.in_transaction: conn.execute("ROLLBACK")
        raise ve # Re-raise the specific ValueError
    except sqlite3.Error as e:
        if conn.in_transaction: conn.execute("ROLLBACK")
        # Log the error e
        raise ValueError(f"Could not create booking due to a database error: {e}")
    finally:
        if conn: conn.close()


def get_booking_details(booking_id):
    conn = get_db_connection()
    try:
        booking_row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not booking_row:
            return None, []

        booking_obj = _db_row_to_booking_object(booking_row)

        ticket_rows = conn.execute("SELECT * FROM tickets WHERE booking_id = ?", (booking_id,)).fetchall()
        associated_tickets = [_db_row_to_ticket_object(row) for row in ticket_rows]

        return booking_obj, associated_tickets
    finally:
        if conn: conn.close()

def get_user_bookings(user_id):
    conn = get_db_connection()
    try:
        booking_rows = conn.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY booking_date DESC", (user_id,)
        ).fetchall()
        return [_db_row_to_booking_object(row) for row in booking_rows]
    finally:
        if conn: conn.close()

# Note: The ticket_service.py also uses an in-memory `tickets_db` (shared from booking_service).
# That service will also need refactoring, or its functionality might be merged/re-evaluated
# now that bookings and tickets are in the DB. For now, focusing on booking_service.
