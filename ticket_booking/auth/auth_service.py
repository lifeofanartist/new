from ticket_booking.models import User
import hashlib # For basic password hashing (demonstration purposes only)

# In-memory storage for users (replace with database later)
users_db = {}
next_user_id = 1

def hash_password(password):
    # WARNING: This is a very basic hashing example.
    # In a real application, use a strong, salted hashing library like bcrypt or passlib.
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email):
    global next_user_id
    if username in users_db:
        raise ValueError("Username already exists")

    password_hash = hash_password(password)
    user = User(id=next_user_id, username=username, password_hash=password_hash, email=email)
    users_db[username] = user
    next_user_id += 1
    return user

def login_user(username, password):
    user = users_db.get(username)
    if user and user.password_hash == hash_password(password):
        # In a real app, you would typically return a session token or similar
        return user
    return None
