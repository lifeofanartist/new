class Ticket:
    def __init__(self, id, booking_id, event_id, seat_number=None, qr_code=None):
        self.id = id
        self.booking_id = booking_id
        self.event_id = event_id
        self.seat_number = seat_number # Optional, depending on event type
        self.qr_code = qr_code # For e-tickets
