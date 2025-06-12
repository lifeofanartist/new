class User:
    def __init__(self, id, username, password_hash, email):
        self.id = id
        self.username = username
        self.password_hash = password_hash # In a real app, never store plain passwords
        self.email = email
