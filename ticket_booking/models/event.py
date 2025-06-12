from datetime import datetime

class Event:
    def __init__(self, id, name, date, venue, total_tickets, price):
        self.id = id
        self.name = name
        self.date = date
        self.venue = venue
        self.total_tickets = total_tickets
        self.available_tickets = total_tickets
        self.price = price
