from datetime import datetime

class Booking:
    def __init__(self, id, user_id, event_id, num_tickets, booking_date=None):
        self.id = id
        self.user_id = user_id
        self.event_id = event_id
        self.num_tickets = num_tickets
        self.booking_date = booking_date if booking_date else datetime.utcnow()
