from flask import Flask, jsonify, request, abort # Added abort
# ... (other imports: get_db_connection, auth_service, event_service, booking_service, ticket_service, jwt, os, datetime, sqlite3)
from flasgger import Swagger, swag_from # Import Swagger and swag_from

# Ensure all existing imports are maintained
from ticket_booking.db import get_db_connection
from ticket_booking.auth import auth_service
from ticket_booking.api import event_service
from ticket_booking.api import booking_service
from ticket_booking.api import ticket_service
from flask_jwt_extended import create_access_token, jwt_required, JWTManager, get_jwt_identity # Removed unused verify_jwt_in_request and specific exceptions for now
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)

# --- Flasgger Configuration ---
app.config['SWAGGER'] = {
    'title': 'Ticket Booking API',
    'uiversion': 3, # Use Swagger UI 3
    'version': '1.0.0',
    'description': 'API for a ticket booking system allowing users to register, login, manage events, and book tickets.',
    # Optional: configure security definitions for JWT
    'securityDefinitions': {
        'BearerAuth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT Access Token (prefix with "Bearer ")'
        }
    },
    'security': [ # Global security requirement (can be overridden at endpoint level)
        {'BearerAuth': []}
    ]
}
swagger = Swagger(app) # Initialize Flasgger

# --- JWT Configuration ---
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "super-secret-dev-key")
jwt = JWTManager(app)

# --- Standardized Error Handlers (as before) ---
# ... (all @app.errorhandler and @jwt.*_loader functions remain)
@app.errorhandler(400) # Bad Request
def bad_request_error(error):
    message = error.description if hasattr(error, 'description') and error.description else "Bad Request"
    return jsonify(error={"code": 400, "message": message}), 400
# ... (and 401, 403, 404, 409, 422, 500)
@app.errorhandler(401)
def unauthorized_error(error):
    message = error.description if hasattr(error, 'description') and error.description else "Unauthorized"
    return jsonify(error={"code": 401, "message": message}), 401
@app.errorhandler(403)
def forbidden_error(error):
    message = error.description if hasattr(error, 'description') and error.description else "Forbidden"
    return jsonify(error={"code": 403, "message": message}), 403
@app.errorhandler(404)
def not_found_error(error):
    message = error.description if hasattr(error, 'description') and error.description else "Resource not found"
    return jsonify(error={"code": 404, "message": message}), 404
@app.errorhandler(409)
def conflict_error(error):
    message = error.description if hasattr(error, 'description') and error.description else "Conflict with current state of the resource"
    return jsonify(error={"code": 409, "message": message}), 409
@app.errorhandler(422)
def unprocessable_entity_error(error):
    messages = error.description if hasattr(error, 'description') and error.description else "Unprocessable Entity"
    return jsonify(error={"code": 422, "message": "Validation error", "errors": messages}), 422
@app.errorhandler(500)
def internal_server_error(error):
    print(f"Server Error: {error}")
    return jsonify(error={"code": 500, "message": "Internal Server Error"}), 500
@jwt.unauthorized_loader
def custom_unauthorized_response(error_string):
    return jsonify(error={"code": 401, "message": error_string}), 401
@jwt.invalid_token_loader
def custom_invalid_token_response(error_string):
    return jsonify(error={"code": 422, "message": f"Invalid token: {error_string}"}), 422 # 422 for unprocessable token
@jwt.expired_token_loader
def custom_expired_token_response(jwt_header, jwt_payload):
    return jsonify(error={"code": 401, "message": "Token has expired"}), 401
@jwt.needs_fresh_token_loader
def custom_needs_fresh_token_response(jwt_header, jwt_payload):
    return jsonify(error={"code": 401, "message": "Fresh token required"}), 401


# --- Routes ---

# Basic Routes (Example: Health Check with Swagger)
@app.route('/health')
@swag_from({
    'tags': ['Health'],
    'summary': 'Check API Health',
    'description': 'Returns the operational status of the API and database connectivity.',
    'responses': {
        200: {
            'description': 'API is UP and database is connected.',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'UP'},
                    'database': {'type': 'string', 'example': 'connected'}
                }
            }
        },
        500: {
            'description': 'API is DOWN or database is disconnected.',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'example': 'DOWN'},
                    'database': {'type': 'string', 'example': 'disconnected'},
                    'error': {'type': 'string'}
                }
            }
        }
    },
    'security': [] # Publicly accessible
})
def health_check():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify(status="UP", database="connected")
    except Exception as e: # Will be caught by 500 handler if not more specific
        print(f"Health Check DB Error: {e}")
        abort(500, description="Database connectivity issue during health check.")


# User Authentication Endpoints (Example: Register with Swagger)
@app.route('/register', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Register a new user',
    'description': 'Creates a new user account.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password', 'email'],
                'properties': {
                    'username': {'type': 'string', 'example': 'newuser'},
                    'password': {'type': 'string', 'format': 'password', 'example': 'password123'},
                    'email': {'type': 'string', 'format': 'email', 'example': 'newuser@example.com'}
                }
            }
        }
    ],
    'responses': {
        201: {
            'description': 'User registered successfully.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'username': {'type': 'string'},
                            'email': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing or invalid fields (triggers custom 400 error handler)'},
        409: {'description': 'Username or email already exists (triggers custom 409 error handler)'},
        500: {'description': 'Internal server error (triggers custom 500 error handler)'}
    },
    'security': [] # Override global security: registration does not require auth
})
def register():
    data = request.get_json()
    if not data: abort(400, description="Request body must be JSON.")
    required_fields = ['username', 'password', 'email']
    missing_fields = [field for field in required_fields if field not in data or not data.get(field)]
    if missing_fields: abort(400, description=f"Missing or empty required fields: {', '.join(missing_fields)}")
    try:
        user = auth_service.register_user(
            username=data['username'], password=data['password'], email=data['email']
        )
        user_info = {"id": user.id, "username": user.username, "email": user.email}
        return jsonify(message="User registered successfully", user=user_info), 201
    except ValueError as e:
        abort(409, description=str(e))
    except Exception: raise

@app.route('/login', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'summary': 'Log in an existing user',
    'description': 'Authenticates a user and returns JWT access token.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {'type': 'string', 'example': 'testuser'},
                    'password': {'type': 'string', 'format': 'password', 'example': 'password123'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Login successful.',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'access_token': {'type': 'string'},
                    'user_id': {'type': 'integer'}
                }
            }
        },
        400: {'description': 'Missing username or password'},
        401: {'description': 'Invalid username or password'},
        500: {'description': 'Internal server error'}
    },
    'security': [] # Login does not require prior auth
})
def login():
    data = request.get_json()
    if not data: abort(400, description="Request body must be JSON.")
    required_fields = ['username', 'password']
    missing_fields = [field for field in required_fields if field not in data or not data.get(field)]
    if missing_fields: abort(400, description=f"Missing or empty required fields: {', '.join(missing_fields)}")
    try:
        user = auth_service.login_user(username=data['username'], password=data['password'])
        if user:
            access_token = create_access_token(identity=user.id)
            return jsonify(message="Login successful", access_token=access_token, user_id=user.id), 200
        else:
            abort(401, description="Invalid username or password")
    except Exception: raise

# --- Event Management Endpoints ---
# GET /events (Example with Swagger)
@app.route('/events', methods=['GET'])
@swag_from({
    'tags': ['Events'],
    'summary': 'List all available events',
    'description': 'Retrieves a list of all events in the system.',
    'produces': ['application/json'],
    'responses': {
        200: {
            'description': 'A list of events.',
            'schema': {
                'type': 'object',
                'properties': {
                    'events': {
                        'type': 'array',
                        'items': { # Schema for a single event item
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'name': {'type': 'string'},
                                'date': {'type': 'string', 'format': 'date-time'},
                                'venue': {'type': 'string'},
                                'total_tickets': {'type': 'integer'},
                                'available_tickets': {'type': 'integer'},
                                'price': {'type': 'number', 'format': 'float'}
                            }
                        }
                    }
                }
            }
        },
        500: {'description': 'Internal server error'}
    },
    'security': [] # Publicly accessible
})
def get_all_events_endpoint():
    try:
        events = event_service.get_all_events()
        events_info = [{"id": event.id, "name": event.name, "date": event.date.isoformat(), "venue": event.venue, "total_tickets": event.total_tickets, "available_tickets": event.available_tickets, "price": event.price} for event in events]
        return jsonify(events=events_info), 200
    except Exception: raise

# POST /events (Example with security)
@app.route('/events', methods=['POST'])
@jwt_required()
@swag_from({
    'tags': ['Events'],
    'summary': 'Create a new event',
    'description': 'Adds a new event to the system. Requires authentication.',
    'consumes': ['application/json'],
    'produces': ['application/json'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['name', 'date_str', 'venue', 'total_tickets', 'price'],
                'properties': {
                    'name': {'type': 'string', 'example': 'Grand Concert'},
                    'date_str': {'type': 'string', 'example': '2024-12-31 20:00:00', 'description': 'Format: YYYY-MM-DD HH:MM:SS'},
                    'venue': {'type': 'string', 'example': 'Main Arena'},
                    'total_tickets': {'type': 'integer', 'example': 1000},
                    'price': {'type': 'number', 'format': 'float', 'example': 75.50}
                }
            }
        }
    ],
    'responses': {
        201: {'description': 'Event created successfully.'}, # Define schema similar to GET /events item
        400: {'description': 'Invalid input or validation error.'},
        401: {'description': 'Authentication required.'}, # From @jwt_required
        500: {'description': 'Internal server error.'}
    }
    # Implicitly uses global BearerAuth security due to @jwt_required
})
def create_event_endpoint():
    # current_user_id = get_jwt_identity() # Available if needed
    data = request.get_json()
    if not data: abort(400, description="Request body must be JSON.")
    required_fields = ['name', 'date_str', 'venue', 'total_tickets', 'price']
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
        elif data.get(field) is None or (isinstance(data.get(field), str) and not data.get(field).strip()):
             missing_fields.append(f"{field} (cannot be empty or null)")
    if missing_fields: abort(400, description=f"Missing or invalid required fields: {', '.join(missing_fields)}")
    try:
        if not isinstance(data['name'], str): raise ValueError("Event name must be a string.")
        if not isinstance(data['date_str'], str): raise ValueError("Event date_str must be a string.")
        if not isinstance(data['venue'], str): raise ValueError("Event venue must be a string.")
        if not isinstance(data['total_tickets'], int): raise ValueError("Total tickets must be an integer.")
        if not isinstance(data['price'], (int, float)): raise ValueError("Price must be a number.")
    except ValueError as ve: abort(400, description=str(ve))
    try:
        event = event_service.create_event(name=data['name'], date_str=data['date_str'], venue=data['venue'], total_tickets=data['total_tickets'], price=data['price'])
        event_info = {"id": event.id, "name": event.name, "date": event.date.isoformat(), "venue": event.venue, "total_tickets": event.total_tickets, "available_tickets": event.available_tickets, "price": event.price}
        return jsonify(message="Event created successfully", event=event_info), 201
    except ValueError as e: abort(400, description=str(e))
    except Exception: raise

# --- Start of Undocumented Routes (to be kept) ---
@app.route('/') # Already present, but not in provided snippet for this subtask
def hello_world(): return jsonify(message="Welcome to the Ticket Booking API!")

@app.route('/protected', methods=['GET']) # Already present
@jwt_required()
def protected(): current_user_id = get_jwt_identity(); return jsonify(logged_in_as=current_user_id, message="Access granted to protected route!"), 200

@app.route('/events/<int:event_id>', methods=['GET'])
def get_event_endpoint(event_id):
    try:
        event = event_service.get_event(event_id)
        if event:
            event_info = {"id": event.id, "name": event.name, "date": event.date.isoformat(), "venue": event.venue, "total_tickets": event.total_tickets, "available_tickets": event.available_tickets, "price": event.price}
            return jsonify(event=event_info), 200
        else:
            abort(404, description="Event not found")
    except Exception: raise

@app.route('/events/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event_endpoint(event_id):
    data = request.get_json()
    if not data: abort(400, description="Request body must be JSON and cannot be empty.")
    try:
        if 'name' in data and (not isinstance(data.get('name'), str) or not data.get('name').strip()): raise ValueError("Event name must be a non-empty string if provided.")
        if 'total_tickets' in data and (data.get('total_tickets') is not None and (not isinstance(data['total_tickets'], int) or data['total_tickets'] <= 0)): raise ValueError("Total tickets must be a positive integer if provided.")
        if 'price' in data and (data.get('price') is not None and (not isinstance(data['price'], (int, float)) or data['price'] < 0)): raise ValueError("Price must be a non-negative number if provided.")
    except ValueError as ve: abort(400, description=str(ve))
    try:
        updated_event = event_service.update_event(event_id=event_id, name=data.get('name'), date_str=data.get('date_str'), venue=data.get('venue'), total_tickets=data.get('total_tickets'), price=data.get('price'))
        if updated_event:
            event_info = {"id": updated_event.id, "name": updated_event.name, "date": updated_event.date.isoformat(), "venue": updated_event.venue, "total_tickets": updated_event.total_tickets, "available_tickets": updated_event.available_tickets, "price": updated_event.price}
            return jsonify(message="Event updated successfully", event=event_info), 200
        else:
            abort(404, description="Event not found or update failed (no changes made or event does not exist).")
    except ValueError as e: abort(400, description=str(e))
    except Exception: raise

@app.route('/events/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event_endpoint(event_id):
    try:
        if event_service.delete_event(event_id):
            return '', 204
        else:
            abort(404, description="Event not found.")
    except ValueError as e:
        if "Cannot delete event" in str(e) and "existing bookings" in str(e): abort(409, description=str(e))
        else: abort(400, description=str(e))
    except Exception: raise

@app.route('/bookings', methods=['POST'])
@jwt_required()
def create_booking_endpoint():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data: abort(400, description="Request body must be JSON.")
    required_fields = ['event_id', 'num_tickets']
    missing_fields = [field for field in required_fields if data.get(field) is None]
    if missing_fields: abort(400, description=f"Missing or null required fields: {', '.join(missing_fields)}")
    try:
        event_id = int(data['event_id'])
        num_tickets = int(data['num_tickets'])
    except (TypeError, ValueError): abort(400, description="Invalid event_id or num_tickets format. Must be integers.")
    try:
        booking, tickets = booking_service.create_booking(user_id=current_user_id, event_id=event_id, num_tickets=num_tickets)
        booking_info = {"id": booking.id, "user_id": booking.user_id, "event_id": booking.event_id, "num_tickets": booking.num_tickets, "booking_date": booking.booking_date.isoformat(), "ticket_ids": [ticket.id for ticket in tickets]}
        return jsonify(message="Booking created successfully", booking=booking_info), 201
    except ValueError as e:
        if "not found" in str(e).lower(): abort(404, description=str(e))
        elif "not enough tickets" in str(e).lower() or "Invalid user ID" in str(e): abort(400, description=str(e)) # Adjusted 409 to 400 for not enough tickets as per earlier error handling, or it's a validation issue.
        else: abort(400, description=str(e))
    except Exception: raise

@app.route('/bookings/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_booking_details_endpoint(booking_id):
    current_user_id = get_jwt_identity()
    try:
        booking, tickets = booking_service.get_booking_details(booking_id)
        if booking:
            if booking.user_id != current_user_id: abort(403, description="Unauthorized to view this booking")
            booking_info = {"id": booking.id, "user_id": booking.user_id, "event_id": booking.event_id, "num_tickets": booking.num_tickets, "booking_date": booking.booking_date.isoformat(), "tickets": [{"id": t.id, "seat_number": t.seat_number, "qr_code": t.qr_code} for t in tickets]}
            return jsonify(booking=booking_info), 200
        else:
            abort(404, description="Booking not found")
    except Exception: raise

@app.route('/my-bookings', methods=['GET'])
@jwt_required()
def get_my_bookings_endpoint():
    current_user_id = get_jwt_identity()
    try:
        user_bookings = booking_service.get_user_bookings(current_user_id)
        bookings_info = [{"id": b.id, "user_id": b.user_id, "event_id": b.event_id, "num_tickets": b.num_tickets, "booking_date": b.booking_date.isoformat()} for b in user_bookings]
        return jsonify(bookings=bookings_info), 200
    except Exception: raise

@app.route('/tickets/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket_details_endpoint(ticket_id):
    current_user_id = get_jwt_identity()
    try:
        ticket = ticket_service.get_ticket_by_id(ticket_id)
        if not ticket: abort(404, description="Ticket not found")
        booking, _ = booking_service.get_booking_details(ticket.booking_id)
        if not booking or booking.user_id != current_user_id: abort(403, description="Unauthorized to view this ticket")
        ticket_info = {"id": ticket.id, "booking_id": ticket.booking_id, "event_id": ticket.event_id, "seat_number": ticket.seat_number, "qr_code": ticket.qr_code }
        return jsonify(ticket=ticket_info), 200
    except Exception: raise

@app.route('/bookings/<int:booking_id>/tickets', methods=['GET'])
@jwt_required()
def get_tickets_for_booking_endpoint(booking_id):
    current_user_id = get_jwt_identity()
    try:
        booking, _ = booking_service.get_booking_details(booking_id)
        if not booking: abort(404, description="Booking not found")
        if booking.user_id != current_user_id: abort(403, description="Unauthorized to view tickets for this booking")
        tickets = ticket_service.get_tickets_for_booking(booking_id)
        tickets_info = [{"id": t.id, "booking_id": t.booking_id, "event_id": t.event_id, "seat_number": t.seat_number, "qr_code": t.qr_code} for t in tickets]
        return jsonify(tickets=tickets_info), 200
    except Exception: raise

@app.route('/events/<int:event_id>/tickets', methods=['GET'])
@jwt_required()
def get_tickets_for_event_endpoint(event_id):
    event = event_service.get_event(event_id)
    if not event: abort(404, description="Event not found")
    try:
        tickets = ticket_service.get_tickets_for_event(event_id)
        tickets_info = [{"id": t.id, "booking_id": t.booking_id, "event_id": t.event_id, "seat_number": t.seat_number, "qr_code": t.qr_code} for t in tickets]
        return jsonify(tickets=tickets_info), 200
    except Exception: raise
# --- End of Undocumented Routes ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
