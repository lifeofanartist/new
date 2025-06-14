import sqlite3
from ticket_booking.models import Event
from ticket_booking.db import get_db_connection
from datetime import datetime

# In-memory storage (events_db, next_event_id) should be removed.

def _db_row_to_event_object(row):
    if row is None:
        return None
    event = Event(
        id=row['id'],
        name=row['name'],
        date=datetime.fromisoformat(row['date']),
        venue=row['venue'],
        total_tickets=row['total_tickets'],
        price=row['price']
    )
    event.available_tickets = row['available_tickets']
    return event

def create_event(name, date_str, venue, total_tickets, price):
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

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO events (name, date, venue, total_tickets, available_tickets, price) VALUES (?, ?, ?, ?, ?, ?)",
            (name, event_date.isoformat(), venue, total_tickets, total_tickets, price)
        )
        conn.commit()
        event_id = cursor.lastrowid
        created_event_row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return _db_row_to_event_object(created_event_row)
    except sqlite3.Error as e:
        conn.rollback()
        raise ValueError(f"Could not create event: {e}")
    finally:
        conn.close()

def get_event(event_id):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return _db_row_to_event_object(row)
    finally:
        conn.close()

def get_all_events():
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM events ORDER BY date DESC").fetchall()
        return [_db_row_to_event_object(row) for row in rows]
    finally:
        conn.close()

def update_event(event_id, name=None, date_str=None, venue=None, total_tickets=None, price=None):
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        current_event_row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone() # Removed FOR UPDATE for simplicity
        if not current_event_row:
            conn.execute("ROLLBACK")
            return None

        current_event = _db_row_to_event_object(current_event_row)
        new_name = name if name is not None else current_event.name
        new_date_iso = current_event.date.isoformat()
        if date_str:
            try:
                new_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                if new_date < datetime.now(): # Added check for future date on update
                    conn.execute("ROLLBACK")
                    raise ValueError("Event date must be in the future.")
                new_date_iso = new_date.isoformat()
            except ValueError:
                conn.execute("ROLLBACK")
                raise ValueError("Invalid date format for update. Use YYYY-MM-DD HH:MM:SS")

        new_venue = venue if venue is not None else current_event.venue
        original_total_tickets = current_event.total_tickets
        new_total_tickets = total_tickets if total_tickets is not None else original_total_tickets
        new_price = price if price is not None else current_event.price
        new_available_tickets = current_event.available_tickets

        if total_tickets is not None:
            if not isinstance(total_tickets, int) or total_tickets <= 0:
                conn.execute("ROLLBACK")
                raise ValueError("Total tickets must be a positive integer.")
            tickets_sold = original_total_tickets - current_event.available_tickets
            if new_total_tickets < tickets_sold:
                conn.execute("ROLLBACK")
                raise ValueError(f"Cannot reduce total_tickets to {new_total_tickets}: {tickets_sold} tickets sold.")
            new_available_tickets = new_total_tickets - tickets_sold

        if price is not None and (not isinstance(price, (int, float)) or price < 0):
            conn.execute("ROLLBACK")
            raise ValueError("Price must be a non-negative number.")

        conn.execute(
            "UPDATE events SET name = ?, date = ?, venue = ?, total_tickets = ?, available_tickets = ?, price = ? WHERE id = ?",
            (new_name, new_date_iso, new_venue, new_total_tickets, new_available_tickets, new_price, event_id)
        )
        conn.commit()
        updated_event_row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return _db_row_to_event_object(updated_event_row)
    except Exception as e: # Catch broader exceptions for rollback safety
        if conn.in_transaction: conn.execute("ROLLBACK")
        raise ValueError(f"Could not update event: {e}") # Wrap generic error
    finally:
        if conn: conn.close()

def delete_event(event_id):
    conn = get_db_connection()
    try:
        conn.execute("BEGIN")
        bookings_exist = conn.execute("SELECT 1 FROM bookings WHERE event_id = ?", (event_id,)).fetchone()
        if bookings_exist:
            conn.execute("ROLLBACK")
            raise ValueError(f"Cannot delete event {event_id}: existing bookings. Archive or cancel bookings first.")

        cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        if conn.in_transaction: conn.execute("ROLLBACK")
        raise ValueError(f"Could not delete event: {e}")
    finally:
        if conn: conn.close()

def decrease_event_available_tickets(event_id, quantity, conn_passed=None):
    conn = conn_passed or get_db_connection()
    is_external_transaction = conn_passed is not None
    try:
        if not is_external_transaction: conn.execute("BEGIN")
        current_event_row = conn.execute("SELECT available_tickets FROM events WHERE id = ?", (event_id,)).fetchone()
        if not current_event_row:
            if not is_external_transaction: conn.execute("ROLLBACK")
            raise ValueError(f"Event ID {event_id} not found for ticket count update.")
        current_available = current_event_row['available_tickets']
        if current_available < quantity:
            if not is_external_transaction: conn.execute("ROLLBACK")
            raise ValueError(f"Not enough tickets for event {event_id}. Requested: {quantity}, Available: {current_available}")
        new_available_count = current_available - quantity
        cursor = conn.execute("UPDATE events SET available_tickets = ? WHERE id = ?", (new_available_count, event_id))
        if not is_external_transaction: conn.commit()
        if cursor.rowcount == 0:
             if not is_external_transaction: conn.execute("ROLLBACK")
             raise ValueError(f"Failed to update ticket count for event {event_id} (not found by UPDATE).")
        return True
    except Exception as e:
        if not is_external_transaction and conn.in_transaction: conn.rollback()
        raise ValueError(f"DB error updating event ticket count for event {event_id}: {e}")
    finally:
        if not is_external_transaction and conn: conn.close()

def increase_event_available_tickets(event_id, quantity, conn_passed=None):
    conn = conn_passed or get_db_connection()
    is_external_transaction = conn_passed is not None
    try:
        if not is_external_transaction: conn.execute("BEGIN")
        event_details = conn.execute("SELECT available_tickets, total_tickets FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event_details:
            if not is_external_transaction: conn.execute("ROLLBACK")
            raise ValueError(f"Event ID {event_id} not found for increasing ticket count.")
        new_available_count = event_details['available_tickets'] + quantity
        if new_available_count > event_details['total_tickets']:
            if not is_external_transaction: conn.execute("ROLLBACK")
            raise ValueError(f"Cannot increase available tickets for event {event_id} beyond total capacity.")
        cursor = conn.execute("UPDATE events SET available_tickets = ? WHERE id = ?", (new_available_count, event_id))
        if not is_external_transaction: conn.commit()
        if cursor.rowcount == 0:
            if not is_external_transaction: conn.execute("ROLLBACK")
            raise ValueError(f"Failed to increase ticket count for event {event_id} (not found by UPDATE).")
        return True
    except Exception as e:
        if not is_external_transaction and conn.in_transaction: conn.rollback()
        raise ValueError(f"DB error increasing event ticket count for event {event_id}: {e}")
    finally:
        if not is_external_transaction and conn: conn.close()
