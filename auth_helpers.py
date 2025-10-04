"""
Authentication Helper Functions for NeuroShield
Provides utilities for user management, session handling, and security
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import re


# ==================== Decorators ====================

def login_required(f):
    """Decorator to require login for routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        # Check if user is admin (you can add admin flag to users table)
        # For demo, we'll allow all authenticated users
        return f(*args, **kwargs)

    return decorated_function


# ==================== User Validation ====================

def validate_username(username):
    """
    Validate username format
    Rules:
    - 3-20 characters
    - Alphanumeric and underscores only
    - Must start with a letter
    """
    if not username or len(username) < 3 or len(username) > 20:
        return False, "Username must be 3-20 characters long"

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, "Username must start with a letter and contain only letters, numbers, and underscores"

    return True, "Valid"


def validate_password(password):
    """
    Validate password strength
    Rules:
    - At least 6 characters
    - Contains at least one letter and one number (optional but recommended)
    """
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long"

    # Optional: Check for complexity
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    if not (has_letter and has_number):
        return True, "Warning: Password should contain both letters and numbers for better security"

    return True, "Valid"


def validate_registration_data(data):
    """Validate all registration data"""
    username = data.get('username', '')
    password = data.get('password', '')

    # Validate username
    valid, message = validate_username(username)
    if not valid:
        return False, message

    # Validate password
    valid, message = validate_password(password)
    if not valid:
        return False, message

    return True, "Valid"


# ==================== Anonymous ID Generation ====================

def generate_anonymous_id(prefix="anon"):
    """Generate a secure anonymous user ID"""
    random_part = secrets.token_hex(8)
    return f"{prefix}_{random_part}"


# ==================== Password Utilities ====================

def hash_password(password):
    """Hash a password for storage"""
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash, password):
    """Verify a password against its hash"""
    return check_password_hash(password_hash, password)


# ==================== Session Management ====================

def create_user_session(user_id):
    """Create a new user session"""
    session['user_id'] = user_id
    session.permanent = True


def destroy_user_session():
    """Destroy current user session"""
    session.pop('user_id', None)
    session.clear()


def get_current_user_id():
    """Get the current logged-in user ID"""
    return session.get('user_id')


def is_authenticated():
    """Check if user is authenticated"""
    return 'user_id' in session


# ==================== Rate Limiting ====================

class RateLimiter:
    """Simple in-memory rate limiter for login attempts"""

    def __init__(self):
        self.attempts = {}  # {username: [timestamp1, timestamp2, ...]}
        self.max_attempts = 5
        self.window = 300  # 5 minutes in seconds

    def is_rate_limited(self, username):
        """Check if username is rate limited"""
        import time

        if username not in self.attempts:
            return False

        # Remove old attempts outside the window
        current_time = time.time()
        self.attempts[username] = [
            t for t in self.attempts[username]
            if current_time - t < self.window
        ]

        return len(self.attempts[username]) >= self.max_attempts

    def record_attempt(self, username):
        """Record a failed login attempt"""
        import time

        if username not in self.attempts:
            self.attempts[username] = []

        self.attempts[username].append(time.time())

    def reset_attempts(self, username):
        """Reset attempts for a username (on successful login)"""
        if username in self.attempts:
            del self.attempts[username]


# Global rate limiter instance
rate_limiter = RateLimiter()


# ==================== User Info Utilities ====================

def get_user_info(db, user_id):
    """Get user information by ID"""
    user = db.execute(
        'SELECT id, username, anonymous_id, consent_research, created_at FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    if user:
        return {
            'id': user['id'],
            'username': user['username'],
            'anonymous_id': user['anonymous_id'],
            'consent_research': user['consent_research'],
            'created_at': user['created_at']
        }
    return None


def get_user_by_username(db, username):
    """Get user by username"""
    user = db.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,)
    ).fetchone()
    return user


# ==================== Security Utilities ====================

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')

    return text.strip()


def is_safe_redirect_url(url):
    """Check if redirect URL is safe (prevents open redirect)"""
    if not url:
        return False

    # Only allow relative URLs
    if url.startswith('/') and not url.startswith('//'):
        return True

    return False


# ==================== Account Management ====================

def change_password(db, user_id, old_password, new_password):
    """Change user password"""
    # Verify old password
    user = db.execute(
        'SELECT password_hash FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    if not user:
        return False, "User not found"

    if not verify_password(user['password_hash'], old_password):
        return False, "Incorrect current password"

    # Validate new password
    valid, message = validate_password(new_password)
    if not valid:
        return False, message

    # Update password
    new_hash = hash_password(new_password)
    db.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (new_hash, user_id)
    )
    db.commit()

    return True, "Password changed successfully"


def delete_user_account(db, user_id):
    """Delete user account and all associated data"""
    try:
        # Delete in order of foreign key dependencies
        db.execute('DELETE FROM brain_states WHERE session_id IN (SELECT id FROM eeg_sessions WHERE user_id = ?)',
                   (user_id,))
        db.execute('DELETE FROM eeg_sessions WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM emergency_events WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM journal_entries WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM streaks WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()

        return True, "Account deleted successfully"
    except Exception as e:
        db.rollback()
        return False, f"Error deleting account: {str(e)}"


# ==================== Usage Example ====================

"""
Example usage in Flask routes:

from auth_helpers import login_required, validate_registration_data, create_user_session

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()

    # Validate input
    valid, message = validate_registration_data(data)
    if not valid:
        return jsonify({'error': message}), 400

    # Create user...
    create_user_session(user_id)
    return jsonify({'success': True})

@app.route('/api/protected', methods=['GET'])
@login_required
def protected_route():
    user_id = get_current_user_id()
    return jsonify({'user_id': user_id})
"""