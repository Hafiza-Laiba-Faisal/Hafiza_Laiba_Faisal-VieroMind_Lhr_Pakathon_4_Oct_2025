"""
NeuroShield - Flask Backend with Fixed Agent System
"""

from flask import Flask, request, jsonify, render_template, session, redirect
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
import requests
import sqlite3
import numpy as np
import pickle
import os
import json
import threading
import asyncio
from scipy import signal
from scipy.signal import butter, filtfilt, welch
import time


import sys
from io import StringIO


load_dotenv()
app = Flask(__name__)
# app.secret_key = os.urandom(24)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# CORS(app)
CORS(app,
     cors_allowed_origins="*",  # ← Change to specific origin in production
     supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
DATABASE = 'neuroshield.db'
MODEL_PATH = 'models/eeg_classifier.pkl'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('models', exist_ok=True)

# ==================== Database Setup ====================

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database schema"""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            anonymous_id TEXT UNIQUE,
            consent_research BOOLEAN DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_check_in DATE,
            total_clean_days INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date DATE NOT NULL,
            mood TEXT,
            triggers TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        CREATE TABLE IF NOT EXISTS eeg_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_end TIMESTAMP,
            avg_risk_score REAL,
            triggered_count INTEGER DEFAULT 0,
            focused_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        CREATE TABLE IF NOT EXISTS brain_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            state TEXT NOT NULL,
            confidence REAL NOT NULL,
            risk_score REAL,
            FOREIGN KEY (session_id) REFERENCES eeg_sessions (id)
        );
        
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            sender TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        
        CREATE TABLE IF NOT EXISTS emergency_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action_taken TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')
    db.commit()
    db.close()

# ==================== EEG Signal Processing ====================

class EEGProcessor:
    """Process EEG signals and extract features"""

    def __init__(self, fs=250, n_channels=19):
        self.fs = fs
        self.n_channels = n_channels
        self.bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 45)
        }

    def bandpass_filter(self, data, lowcut, highcut, order=4):
        """Apply bandpass filter"""
        nyq = 0.5 * self.fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data, axis=0)

    def notch_filter(self, data, freq=50, quality=30):
        """Remove powerline noise"""
        nyq = 0.5 * self.fs
        w0 = freq / nyq
        b, a = signal.iirnotch(w0, quality)
        return filtfilt(b, a, data, axis=0)


    def extract_band_powers(self, data):
        features = []
        for ch in range(data.shape[1]):
            freqs, psd = welch(data[:, ch], self.fs, nperseg=min(256, len(data)))
            for band_name, (low, high) in self.bands.items():
                idx = np.logical_and(freqs >= low, freqs <= high)
                band_power = np.trapezoid(psd[idx], freqs[idx])  # Fixed deprecated trapz
                features.append(band_power)
        return np.array(features)

    def extract_features(self, epoch):
        """Extract comprehensive features from EEG epoch"""
        # Apply filters
        filtered = self.bandpass_filter(epoch, 0.5, 45)
        filtered = self.notch_filter(filtered, 50)

        # Band powers
        band_powers = self.extract_band_powers(filtered)

        # Statistical features
        stats = []
        for ch in range(filtered.shape[1]):
            stats.extend([
                np.mean(filtered[:, ch]),
                np.std(filtered[:, ch]),
                np.var(filtered[:, ch]),
                np.max(filtered[:, ch]) - np.min(filtered[:, ch])
            ])

        return np.concatenate([band_powers, stats])

# ==================== ML Model ====================

class BrainStateClassifier:
    """Classify brain states from EEG features"""

    def __init__(self, model_path=MODEL_PATH):
        self.model = None
        self.processor = EEGProcessor()
        self.model_path = model_path
        self.load_model()

    def load_model(self):
        """Load pre-trained model"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
        else:
            # Create dummy model for demo
            self.create_dummy_model()

    def create_dummy_model(self):
        """Create a simple rule-based classifier for demo"""
        class DummyModel:
            def predict_proba(self, features):
                # Simple rule: high theta/alpha ratio = triggered
                # This is a simplified demo logic
                n_samples = features.shape[0]
                probs = np.random.rand(n_samples, 2)
                probs = probs / probs.sum(axis=1, keepdims=True)
                return probs

            def predict(self, features):
                probs = self.predict_proba(features)
                return (probs[:, 1] > 0.5).astype(int)

        self.model = DummyModel()

    def predict(self, eeg_data):
        """Predict brain state from raw EEG data"""
        # Extract features
        features = self.processor.extract_features(eeg_data)
        features = features.reshape(1, -1)

        # Predict
        prediction = self.model.predict(features)[0]
        probs = self.model.predict_proba(features)[0]

        state = 'triggered' if prediction == 1 else 'focused'
        confidence = probs[prediction]
        risk_score = probs[1]  # Probability of triggered state

        return {
            'state': state,
            'confidence': float(confidence),
            'risk_score': float(risk_score),
            'timestamp': datetime.now().isoformat()
        }

# Initialize classifier
classifier = BrainStateClassifier()

# ==================== NLP Support Coach ====================

class SupportCoach:
    """AI-powered support coach with rule-based responses"""

    def __init__(self, use_ai=False):
        self.use_ai = use_ai
        self.conversation_history = {}  # {user_id: [(role, content), ...]}

        # Initialize OpenRouter client if AI mode is enabled
        if self.use_ai:
            try:
                from openai import OpenAI
                openrouter_api_key = os.environ.get('OPENROUTER_API_KEY')
                if not openrouter_api_key:
                    print("Warning: OPENROUTER_API_KEY not set. Falling back to rule-based mode.")
                    self.use_ai = False
                else:
                    self.client = OpenAI(
                        api_key=openrouter_api_key,
                        base_url="https://openrouter.ai/api/v1"
                    )
                    print("✓ OpenRouter AI client initialized")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenRouter client: {e}")
                self.use_ai = False

        self.responses = {
            'urge': [
                "Take a deep breath. This feeling is temporary. Let's do a breathing exercise together.",
                "You're stronger than this urge. Remember your {streak}-day streak and why you started.",
                "This is your brain seeking a dopamine hit. Let's redirect: go for a 5-minute walk.",
            ],
            'anxiety': [
                "I hear you. Anxiety is challenging. Try this: name 5 things you can see right now.",
                "Let's ground yourself. Focus on your breathing - inhale for 4, hold for 4, exhale for 6.",
                "Anxiety often triggers urges. What's making you anxious? Let's address the root cause.",
            ],
            'success': [
                "That's amazing! Your progress shows real commitment. Keep going!",
                "Every clean day is a victory. You're building a healthier life.",
                "Your brain is rewiring itself. This gets easier with time. Proud of you!",
            ],
            'relapse': [
                "Relapse doesn't erase your progress. What matters is that you're here now.",
                "Let's learn from this. What triggered the relapse? Understanding helps prevent it next time.",
                "You're not starting from zero. All your clean days taught your brain new patterns.",
            ],
            'general': [
                "I'm here to support you 24/7. How are you feeling right now?",
                "Remember: recovery is a journey, not a destination. Every day counts.",
                "What's on your mind? Let's talk through it together.",
            ]
        }

    def detect_intent(self, message):
        """Detect user intent from message"""
        message_lower = message.lower()

        urge_keywords = ['urge', 'triggered', 'tempted', 'want to', 'craving']
        anxiety_keywords = ['anxious', 'stressed', 'worried', 'nervous', 'panic']
        success_keywords = ['good', 'great', 'clean', 'proud', 'strong']
        relapse_keywords = ['relapsed', 'failed', 'gave in', 'broke']

        if any(word in message_lower for word in urge_keywords):
            return 'urge'
        elif any(word in message_lower for word in anxiety_keywords):
            return 'anxiety'
        elif any(word in message_lower for word in success_keywords):
            return 'success'
        elif any(word in message_lower for word in relapse_keywords):
            return 'relapse'
        else:
            return 'general'

    def get_system_prompt(self, user_data=None):
        """Generate system prompt for AI coach"""
        streak = user_data.get('streak', 0) if user_data else 0

        return f"""You are a compassionate, professional AI support coach for NeuroShield, an app helping users overcome pornography addiction through neuroscience and EEG-based brain state detection.

Your role:
- Provide empathetic, non-judgmental support 24/7
- Offer evidence-based coping strategies (breathing exercises, mindfulness, CBT techniques)
- Help users understand triggers and develop healthy habits
- Celebrate their progress and encourage persistence
- Never shame or blame users for struggles or relapses

User context:
- Current streak: {streak} days
- They're actively working on recovery and using EEG monitoring to understand their brain states

Guidelines:
- Keep responses supportive, concise (2-4 sentences usually)
- Suggest practical immediate actions when they're struggling
- Normalize the difficulty of recovery
- Emphasize that setbacks are part of the journey
- Focus on progress, not perfection
- If they're in crisis, prioritize immediate coping strategies (breathing, grounding techniques)

Remember: You're a support tool, NOT a replacement for professional therapy. If someone needs urgent help, encourage them to contact a mental health professional."""

    def get_ai_response(self, user_id, message, user_data=None):
        """Get response from OpenRouter AI"""
        try:
            # Initialize conversation history for new users
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            # Add user message to history
            self.conversation_history[user_id].append(("user", message))

            # Prepare messages for LLM (including system prompt + history)
            messages = [
                {
                    "role": "system",
                    "content": self.get_system_prompt(user_data)
                }
            ]

            # Add conversation history
            for role, content in self.conversation_history[user_id]:
                messages.append({
                    "role": role,
                    "content": content
                })

            # Call OpenRouter API
            completion = self.client.chat.completions.create(
                model="anthropic/claude-3.5-sonnet",  # Change this line  # Using Grok model
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            response_text = completion.choices[0].message.content

            # Add assistant response to history
            self.conversation_history[user_id].append(("assistant", response_text))

            # Keep only last 20 messages (10 exchanges) to manage context length
            if len(self.conversation_history[user_id]) > 20:
                self.conversation_history[user_id] = self.conversation_history[user_id][-20:]

            return response_text

        except Exception as e:
            print(f"Error getting AI response: {e}")
            # Fallback to rule-based response
            return self.get_rule_based_response(message, user_data)

    def get_rule_based_response(self, message, user_data=None):
        """Get rule-based response (fallback)"""
        intent = self.detect_intent(message)
        response = np.random.choice(self.responses[intent])

        # Personalize with user data
        if user_data and '{streak}' in response:
            response = response.format(streak=user_data.get('streak', 0))

        return response

    def get_response(self, user_id, message, user_data=None):
        """Main method to get response (AI or rule-based)"""
        if self.use_ai:
            return self.get_ai_response(user_id, message, user_data)
        else:
            return self.get_rule_based_response(message, user_data)

    def clear_history(self, user_id):
        """Clear conversation history for a user"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]

# Initialize coach with AI mode (set to True to enable OpenRouter)
# Set environment variable: export OPENROUTER_API_KEY=your_key_here
USE_AI_COACH = os.environ.get('USE_AI_COACH', 'false').lower() == 'true'
coach = SupportCoach(use_ai=USE_AI_COACH)

# ==================== Routes ====================

@app.route('/')
def index():
    """Home page"""
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Login and registration page"""
    if 'user_id' in session:
        return redirect('/')
    return render_template('login.html')

@app.route('/admin-dashboard')
def admin_dashboard_page():
    """Admin dashboard page"""
    return render_template('admin.html')

@app.route('/api/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    consent_research = data.get('consent_research', False)

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    db = get_db()
    try:
        # Generate anonymous ID
        anonymous_id = f"anon_{os.urandom(8).hex()}"
        password_hash = generate_password_hash(password)

        cursor = db.execute(
            'INSERT INTO users (username, password_hash, anonymous_id, consent_research) VALUES (?, ?, ?, ?)',
            (username, password_hash, anonymous_id, consent_research)
        )
        user_id = cursor.lastrowid

        # Initialize streak
        db.execute(
            'INSERT INTO streaks (user_id, current_streak, longest_streak) VALUES (?, 0, 0)',
            (user_id,)
        )
        db.commit()

        session['user_id'] = user_id
        return jsonify({'success': True, 'user_id': user_id, 'anonymous_id': anonymous_id})

    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        db.close()


@app.route('/api/login', methods=['POST'])
def login():
    """User login"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    db.close()

    if user and check_password_hash(user['password_hash'], password):
        session.permanent = True  # ← Add this
        session['user_id'] = user['id']
        return jsonify({'success': True, 'user_id': user['id']})

    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """User logout"""
    session.pop('user_id', None)
    return jsonify({'success': True})

@app.route('/api/upload_eeg', methods=['POST'])
def upload_eeg():
    """Upload and analyze EEG file"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save file
    filename = f"{session['user_id']}_{datetime.now().timestamp()}.npy"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # Load EEG data
        eeg_data = np.load(filepath)

        # Create session
        db = get_db()
        cursor = db.execute(
            'INSERT INTO eeg_sessions (user_id) VALUES (?)',
            (session['user_id'],)
        )
        session_id = cursor.lastrowid
        db.commit()
        db.close()

        # Analyze data (simplified for demo)
        result = classifier.predict(eeg_data[:500])  # Use first 2 seconds

        return jsonify({
            'success': True,
            'session_id': session_id,
            'result': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start_stream', methods=['POST'])
def start_stream():
    """Start simulated EEG streaming session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db = get_db()
    cursor = db.execute(
        'INSERT INTO eeg_sessions (user_id) VALUES (?)',
        (session['user_id'],)
    )
    session_id = cursor.lastrowid
    db.commit()
    db.close()

    session['current_session_id'] = session_id

    return jsonify({
        'success': True,
        'session_id': session_id,
        'message': 'Streaming session started'
    })

@app.route('/api/stop_stream', methods=['POST'])
def stop_stream():
    """Stop streaming session"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    session_id = session.get('current_session_id')
    if not session_id:
        return jsonify({'error': 'No active session'}), 400

    db = get_db()
    db.execute(
        'UPDATE eeg_sessions SET session_end = CURRENT_TIMESTAMP WHERE id = ?',
        (session_id,)
    )
    db.commit()
    db.close()

    session.pop('current_session_id', None)

    return jsonify({'success': True})

@app.route('/api/state', methods=['GET', 'POST'])
def get_state():
    """Get current brain state (simulated or from uploaded data)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    # Generate simulated EEG data for demo
    simulated_eeg = np.random.randn(500, 19) * 50  # 2 seconds of data

    result = classifier.predict(simulated_eeg)

    # Save state to database
    session_id = session.get('current_session_id')
    if session_id:
        db = get_db()
        db.execute(
            'INSERT INTO brain_states (session_id, state, confidence, risk_score) VALUES (?, ?, ?, ?)',
            (session_id, result['state'], result['confidence'], result['risk_score'])
        )
        db.commit()
        db.close()

    return jsonify(result)

@app.route('/api/emergency', methods=['POST'])
def emergency():
    """Handle emergency support request"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json() or {}
    action = data.get('action', 'breathing')

    # Log emergency event
    db = get_db()
    db.execute(
        'INSERT INTO emergency_events (user_id, action_taken) VALUES (?, ?)',
        (session['user_id'], action)
    )
    db.commit()
    db.close()

    breathing_exercises = {
        'box': {
            'name': 'Box Breathing',
            'steps': ['Inhale 4 seconds', 'Hold 4 seconds', 'Exhale 4 seconds', 'Hold 4 seconds'],
            'duration': 16
        },
        '478': {
            'name': '4-7-8 Breathing',
            'steps': ['Inhale 4 seconds', 'Hold 7 seconds', 'Exhale 8 seconds'],
            'duration': 19
        }
    }

    motivational_quotes = [
        "You are stronger than this urge. It will pass.",
        "Every moment you resist, you're rewiring your brain.",
        "Remember why you started. Your future self will thank you.",
        "This feeling is temporary. Your progress is permanent.",
        "You've come too far to give up now. Keep going!"
    ]

    return jsonify({
        'success': True,
        'breathing_exercise': breathing_exercises['box'],
        'quote': np.random.choice(motivational_quotes),
        'actions': [
            {'label': 'Talk to AI Coach', 'action': 'chat'},
            {'label': 'Write in Journal', 'action': 'journal'},
            {'label': 'Take a Walk', 'action': 'walk'}
        ]
    })

@app.route('/api/user/streak', methods=['GET'])
def get_streak():
    """Get user's current streak"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db = get_db()
    streak = db.execute(
        'SELECT * FROM streaks WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()
    db.close()

    if streak:
        return jsonify({
            'current_streak': streak['current_streak'],
            'longest_streak': streak['longest_streak'],
            'total_clean_days': streak['total_clean_days'],
            'last_check_in': streak['last_check_in']
        })

    return jsonify({'current_streak': 0, 'longest_streak': 0, 'total_clean_days': 0})

@app.route('/api/user/streak', methods=['POST'])
def update_streak():
    """Update user streak (check-in)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    is_clean = data.get('is_clean', True)

    db = get_db()
    streak = db.execute(
        'SELECT * FROM streaks WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()

    today = datetime.now().date()

    if streak:
        current = streak['current_streak']
        longest = streak['longest_streak']
        total = streak['total_clean_days']

        if is_clean:
            current += 1
            total += 1
            longest = max(longest, current)
        else:
            current = 0

        db.execute(
            'UPDATE streaks SET current_streak = ?, longest_streak = ?, total_clean_days = ?, last_check_in = ? WHERE user_id = ?',
            (current, longest, total, today, session['user_id'])
        )

    db.commit()
    db.close()

    return jsonify({'success': True, 'current_streak': current, 'longest_streak': longest})

@app.route('/api/journal', methods=['GET'])
def get_journal():
    """Get journal entries"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db = get_db()
    entries = db.execute(
        'SELECT * FROM journal_entries WHERE user_id = ? ORDER BY entry_date DESC LIMIT 30',
        (session['user_id'],)
    ).fetchall()
    db.close()

    return jsonify([dict(entry) for entry in entries])

@app.route('/api/journal', methods=['POST'])
def create_journal():
    """Create journal entry"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    mood = data.get('mood')
    triggers = data.get('triggers')
    note = data.get('note')
    entry_date = data.get('date', datetime.now().date())

    db = get_db()
    cursor = db.execute(
        'INSERT INTO journal_entries (user_id, entry_date, mood, triggers, note) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], entry_date, mood, triggers, note)
    )
    entry_id = cursor.lastrowid
    db.commit()
    db.close()

    return jsonify({'success': True, 'entry_id': entry_id})

@app.route('/api/nlp/message', methods=['POST'])
def chat_message():
    """Send message to AI coach"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    message = data.get('message', '')

    if not message:
        return jsonify({'error': 'Message required'}), 400

    user_id = session['user_id']

    # Get user data for personalization
    db = get_db()
    streak = db.execute(
        'SELECT current_streak FROM streaks WHERE user_id = ?',
        (user_id,)
    ).fetchone()

    user_data = {'streak': streak['current_streak'] if streak else 0}

    # Save user message
    db.execute(
        'INSERT INTO chat_history (user_id, message, sender) VALUES (?, ?, ?)',
        (user_id, message, 'user')
    )

    # Generate AI response (using OpenRouter if enabled, otherwise rule-based)
    response = coach.get_response(user_id, message, user_data)

    # Save AI response
    db.execute(
        'INSERT INTO chat_history (user_id, message, sender) VALUES (?, ?, ?)',
        (user_id, response, 'coach')
    )

    db.commit()
    db.close()

    return jsonify({
        'success': True,
        'response': response,
        'intent': coach.detect_intent(message),
        'ai_mode': coach.use_ai
    })

@app.route('/api/chat/history', methods=['GET'])
def chat_history():
    """Get chat history"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db = get_db()
    messages = db.execute(
        'SELECT * FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC LIMIT 100',
        (session['user_id'],)
    ).fetchall()
    db.close()

    return jsonify([dict(msg) for msg in messages])

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    """Clear chat history for current user"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']

    # Clear database history
    db = get_db()
    db.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    db.commit()
    db.close()

    # Clear in-memory conversation history
    coach.clear_history(user_id)

    return jsonify({
        'success': True,
        'message': 'Chat history cleared'
    })

@app.route('/api/coach/status', methods=['GET'])
def coach_status():
    """Get AI coach status and configuration"""
    return jsonify({
        'ai_mode': coach.use_ai,
        'model': 'x-ai/grok-2-1212' if coach.use_ai else 'rule-based',
        'description': 'OpenRouter AI-powered responses' if coach.use_ai else 'Rule-based pattern matching'
    })

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    """Admin dashboard with anonymized analytics"""
    db = get_db()

    # Aggregate statistics
    total_users = db.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    active_sessions = db.execute('SELECT COUNT(*) as count FROM eeg_sessions WHERE session_end IS NULL').fetchone()['count']
    total_clean_days = db.execute('SELECT SUM(total_clean_days) as total FROM streaks').fetchone()['total'] or 0
    avg_streak = db.execute('SELECT AVG(current_streak) as avg FROM streaks').fetchone()['avg'] or 0

    # Emergency events
    emergency_count = db.execute('SELECT COUNT(*) as count FROM emergency_events WHERE timestamp > datetime("now", "-7 days")').fetchone()['count']

    # State distribution
    states = db.execute('''
        SELECT state, COUNT(*) as count 
        FROM brain_states 
        WHERE timestamp > datetime("now", "-7 days")
        GROUP BY state
    ''').fetchall()

    db.close()

    stats = {
        'total_users': total_users,
        'active_sessions': active_sessions,
        'total_clean_days': total_clean_days,
        'avg_current_streak': round(avg_streak, 1),
        'emergency_events_week': emergency_count,
        'state_distribution': {row['state']: row['count'] for row in states}
    }

    return jsonify(stats)

@app.route('/api/analytics/user', methods=['GET'])
def user_analytics():
    """Get user-specific analytics"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db = get_db()

    # Get user sessions
    sessions = db.execute('''
        SELECT id, session_start, session_end, avg_risk_score, triggered_count, focused_count
        FROM eeg_sessions
        WHERE user_id = ?
        ORDER BY session_start DESC
        LIMIT 10
    ''', (session['user_id'],)).fetchall()

    # Get brain states over time
    states_timeline = db.execute('''
        SELECT bs.timestamp, bs.state, bs.risk_score
        FROM brain_states bs
        JOIN eeg_sessions es ON bs.session_id = es.id
        WHERE es.user_id = ?
        ORDER BY bs.timestamp DESC
        LIMIT 100
    ''', (session['user_id'],)).fetchall()

    db.close()

    return jsonify({
        'sessions': [dict(s) for s in sessions],
        'states_timeline': [dict(s) for s in states_timeline]
    })




# Agent server URL
AGENTS_SERVER = 'http://localhost:5000'


@app.route('/api/debate/start', methods=['POST'])
def start_agent_debate():
    """Proxy to start agent debate"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    topic = data.get('topic')

    # Forward to agents server
    response = requests.post(f'{AGENTS_SERVER}/api/agents/start_debate', json={
        'topic': topic,
        'session_id': f"user_{session['user_id']}_{topic}"
    })

    return jsonify(response.json())





# ==================== Agent System Integration ====================

from flask_socketio import SocketIO, emit, join_room, leave_room

socketio = SocketIO(app, cors_allowed_origins="*")


# Debate state
active_debates = {}

# Updated personas map
personas_map = {
    'sarah': {'name': 'Dr. Sarah Chen', 'icon': 'fa-user-md', 'color': '#3b82f6', 'role': 'CBT Expert'},
    'james': {'name': 'Dr. James Williams', 'icon': 'fa-spa', 'color': '#10b981', 'role': 'Holistic Healer'},
    'maria': {'name': 'Dr. Maria Rodriguez', 'icon': 'fa-brain', 'color': '#8b5cf6', 'role': 'Psychologist'},
    'david': {'name': 'Dr. David Thompson', 'icon': 'fa-pills', 'color': '#ef4444', 'role': 'Psychiatrist'},
    'lisa': {'name': 'Dr. Lisa Park', 'icon': 'fa-heart', 'color': '#f59e0b', 'role': 'Trauma Specialist'},
    'michael': {'name': 'Dr. Michael Chen', 'icon': 'fa-om', 'color': '#06b6d4', 'role': 'Mindfulness Expert'}
}
# Updated topic prompts
topic_prompts = {
    'anxiety': """A user is struggling with anxiety triggering pornography urges. 
Dr. Sarah (CBT): suggest cognitive techniques. 
Dr. James (holistic): recommend somatic practices. 
Dr. Maria (psychologist): explore root causes.
Dr. David (psychiatrist): discuss neurochemistry.
Dr. Lisa (trauma): address trauma-anxiety connection.
Dr. Michael (mindfulness): teach urge surfing.
Each provides 2-3 sentences.""",

    'digital_therapy': """Debate digital therapy vs in-person treatment for addiction recovery.
Dr. Sarah: present app-based CBT research.
Dr. James: discuss screen time concerns.
Dr. Maria: analyze virtual vs face-to-face connection.
Dr. David: consider medication management remotely.
Dr. Lisa: address trauma processing needs.
Dr. Michael: evaluate mindfulness app effectiveness.""",

    'work_life': """A patient reports work stress triggering relapses.
Dr. Sarah: suggest boundary-setting strategies.
Dr. James: recommend burnout prevention.
Dr. Maria: explore work-identity patterns.
Dr. David: discuss stress neurochemistry.
Dr. Lisa: identify trauma-stress links.
Dr. Michael: teach workplace mindfulness.""",

    'depression': """Discuss depression-addiction relationship.
Dr. Sarah: explain behavioral activation.
Dr. James: advocate lifestyle mood regulation.
Dr. Maria: analyze psychological function.
Dr. David: discuss neurotransmitter imbalances.
Dr. Lisa: explore depressive trauma origins.
Dr. Michael: present mindfulness for depression.""",

    'child_psychology': """Early intervention for teenage compulsive pornography use.
Dr. Sarah: discuss age-appropriate CBT.
Dr. James: emphasize family systems.
Dr. Maria: explore developmental psychology.
Dr. David: consider adolescent brain development.
Dr. Lisa: assess childhood trauma.
Dr. Michael: teach teen mindfulness.""",

    'sleep': """Patient reports sleep disturbances triggering late-night relapses.
Dr. Sarah: suggest CBT-I techniques.
Dr. James: recommend natural sleep remedies.
Dr. Maria: explore psychological insomnia causes.
Dr. David: discuss sleep neurochemistry.
Dr. Lisa: address trauma-related nightmares.
Dr. Michael: teach bedtime meditation.""",

    'self_esteem': """User reports low self-esteem as addiction trigger.
Dr. Sarah: suggest cognitive reframing.
Dr. James: recommend self-compassion practices.
Dr. Maria: explore self-worth origins.
Dr. David: discuss shame neurochemistry.
Dr. Lisa: address shame-based trauma.
Dr. Michael: teach loving-kindness meditation.""",

    'relapse_prevention': """Patient seeks long-term relapse prevention strategies.
Dr. Sarah: propose relapse prevention plans.
Dr. James: advocate lifestyle accountability.
Dr. Maria: analyze trigger patterns.
Dr. David: discuss craving neuroplasticity.
Dr. Lisa: process relapse trauma.
Dr. Michael: teach urge surfing techniques."""
}


def map_agent_to_persona(agent_name):
    if 'Sarah' in agent_name:
        return 'sarah'
    elif 'James' in agent_name:
        return 'james'
    elif 'Maria' in agent_name:
        return 'maria'
    return 'sarah'

OPENAI_API_KEY='replace the key here '

import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Configure OpenAI
config_list = [{'model': 'gpt-4o-mini', 'api_key': OPENAI_API_KEY}]
llm_config = {
    "cache_seed": 42,
    "temperature": 0.7,
    "config_list": config_list,
    "timeout": 120,
}

# 6 Specialized Agent Prompts
agent_prompts = {
    'sarah': """You are Dr. Sarah Chen, CBT practitioner specializing in addiction recovery.
Keep responses 3-5 sentences. Focus on behavioral interventions, cognitive restructuring, and evidence-based techniques.""",

    'james': """You are Dr. James Williams, holistic healer emphasizing mind-body integration.
Keep responses 3-5 sentences. Advocate for mindfulness, breathwork, somatic practices, and nervous system regulation.""",

    'maria': """You are Dr. Maria Rodriguez, analytical psychologist with psychodynamic training.
Keep responses 3-5 sentences. Explore unconscious patterns, attachment styles, and developmental history.""",

    'david': """You are Dr. David Thompson, addiction psychiatrist specializing in neurochemistry.
Keep responses 3-5 sentences. Discuss brain chemistry, dopamine pathways, neuroplasticity, and pharmacological interventions when appropriate.""",

    'lisa': """You are Dr. Lisa Park, trauma-informed therapist with EMDR certification.
Keep responses 3-5 sentences. Focus on trauma processing, emotional regulation, and nervous system healing.""",

    'michael': """You are Dr. Michael Chen, mindfulness-based relapse prevention specialist.
Keep responses 3-5 sentences. Teach urge surfing, acceptance strategies, and meditation-based coping mechanisms."""
}


def create_debate_agents():
    """Create 6 specialized AutoGen agents"""
    user_proxy = UserProxyAgent(
        name="user",
        system_message="Human participant",
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    sarah = AssistantAgent(name="sarah", system_message=agent_prompts['sarah'], llm_config=llm_config)
    james = AssistantAgent(name="james", system_message=agent_prompts['james'], llm_config=llm_config)
    maria = AssistantAgent(name="maria", system_message=agent_prompts['maria'], llm_config=llm_config)
    david = AssistantAgent(name="david", system_message=agent_prompts['david'], llm_config=llm_config)
    lisa = AssistantAgent(name="lisa", system_message=agent_prompts['lisa'], llm_config=llm_config)
    michael = AssistantAgent(name="michael", system_message=agent_prompts['michael'], llm_config=llm_config)

    return user_proxy, sarah, james, maria, david, lisa, michael


def state_transition(last_speaker, groupchat):
    """Control speaker rotation: Sarah -> James -> Maria -> David -> Lisa -> Michael"""

    if last_speaker.name == "user":
        return groupchat.agents[1]  # sarah

    agent_order = ['sarah', 'james', 'maria', 'david', 'lisa', 'michael']

    try:
        current_index = agent_order.index(last_speaker.name)
        next_index = (current_index + 1) % len(agent_order)

        if len(groupchat.messages) >= groupchat.max_round - 1:
            return None  # End gracefully

        return groupchat.agents[next_index + 1]  # +1 to skip user_proxy
    except ValueError:
        return None


# ==================== Agent Debate Functions ====================





# Replace the run_debate_async function
def run_debate_async(session_id, initial_prompt, selected_agents):
    """Updated debate runner with dynamic agent selection"""
    if session_id not in active_debates:
        print(f"❌ Session {session_id} not found")
        return

    debate_session = active_debates[session_id]
    print(f"✓ Starting {len(selected_agents)}-agent debate for {session_id}")
    print(f"✓ Selected agents: {selected_agents}")

    try:
        # Create only selected agents
        user_proxy = UserProxyAgent(
            name="user",
            system_message="Human participant",
            code_execution_config=False,
            human_input_mode="NEVER",
        )

        agents_dict = {}
        for agent_key in selected_agents:
            agents_dict[agent_key] = AssistantAgent(
                name=agent_key,
                system_message=agent_prompts[agent_key],
                llm_config=llm_config
            )

        print(f"✓ {len(agents_dict)} agents created: {list(agents_dict.keys())}")

        class DebateCapture:
            def __init__(self, session_id, selected_agents):
                self.session_id = session_id
                self.selected_agents = selected_agents
                self.current_speaker = None
                self.message_buffer = []

            def process_line(self, line):
                line = line.strip()
                if not line or line.startswith('---'):
                    return

                if ' (to chat_manager):' in line:
                    speaker = line.split(' (to')[0].strip()
                    # Only process messages from selected agents
                    if speaker in self.selected_agents:
                        if self.current_speaker and self.message_buffer:
                            self.emit_message(self.current_speaker, ' '.join(self.message_buffer))
                            self.message_buffer = []
                        self.current_speaker = speaker
                    return

                if self.current_speaker:
                    self.message_buffer.append(line)

            def emit_message(self, speaker, content):
                if not content.strip():
                    return

                msg = {
                    'speaker': speaker,
                    'text': content.strip(),
                    'timestamp': datetime.now().isoformat(),
                    'speaker_name': personas_map[speaker]['name']
                }

                debate_session['messages'].append(msg)
                print(f"✓ Emitting: {speaker} - {content[:50]}...")
                socketio.emit('debate_message', msg, room=self.session_id, namespace='/')
                time.sleep(2)

            def finalize(self):
                if self.current_speaker and self.message_buffer:
                    self.emit_message(self.current_speaker, ' '.join(self.message_buffer))

        capture = DebateCapture(session_id, selected_agents)
        old_stdout = sys.stdout
        captured_output = StringIO()

        class TeeOutput:
            def write(self, text):
                old_stdout.write(text)
                captured_output.write(text)
                for line in text.split('\n'):
                    capture.process_line(line)
                return len(text)

            def flush(self):
                old_stdout.flush()
                captured_output.flush()

        sys.stdout = TeeOutput()

        try:
            # Dynamic state transition based on selected agents
            def state_transition_dynamic(last_speaker, groupchat):
                if last_speaker.name == "user":
                    return groupchat.agents[1]  # First selected agent

                try:
                    current_index = selected_agents.index(last_speaker.name)
                    next_index = (current_index + 1) % len(selected_agents)

                    if len(groupchat.messages) >= groupchat.max_round - 1:
                        return None

                    return groupchat.agents[next_index + 1]  # +1 to skip user_proxy
                except ValueError:
                    return None

            # Build agents list: user_proxy + selected agents
            agent_list = [user_proxy] + [agents_dict[key] for key in selected_agents]

            groupchat = GroupChat(
                agents=agent_list,
                messages=[],
                max_round=len(selected_agents) * 3,  # 3 rounds per agent
                speaker_selection_method=state_transition_dynamic,
                allow_repeat_speaker=False,
            )
            manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
            user_proxy.initiate_chat(manager, message=initial_prompt)
            print("✓ Chat completed")
        finally:
            sys.stdout = old_stdout
            capture.finalize()

    except Exception as e:
        print(f"❌ Debate Error: {e}")
        import traceback
        traceback.print_exc()
        socketio.emit('debate_error', {'error': f"Debate failed: {str(e)}"}, room=session_id)



@app.route('/api/agents/start_debate', methods=['POST'])
def start_agent_debate_local():
    """Start agent debate with selected agents"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    topic = data.get('topic')
    debate_session_id = data.get('session_id', f"debate_{datetime.now().timestamp()}")
    selected_agents = data.get('selected_agents', ['sarah', 'james', 'maria', 'david', 'lisa', 'michael'])

    print(f"🔍 DEBUG - Received topic: '{topic}'")
    print(f"🔍 DEBUG - Selected agents: {selected_agents}")
    print(f"🔍 DEBUG - Topic in prompts? {topic in topic_prompts}")

    if topic not in topic_prompts:
        return jsonify({'error': f'Invalid topic: {topic}'}), 400

    if len(selected_agents) < 2:
        return jsonify({'error': 'At least 2 agents required'}), 400

    if len(selected_agents) > 6:
        return jsonify({'error': 'Maximum 6 agents allowed'}), 400

    active_debates[debate_session_id] = {
        'topic': topic,
        'messages': [],
        'is_active': True,
        'started_at': datetime.now().isoformat(),
        'selected_agents': selected_agents  # Store selected agents
    }

    # Start debate with selected agents
    thread = threading.Thread(
        target=run_debate_async,
        args=(debate_session_id, topic_prompts[topic], selected_agents)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'session_id': debate_session_id,
        'topic': topic,
        'agent_count': len(selected_agents)
    })



@app.route('/api/agents/inject_user_message', methods=['POST'])
def inject_user_message_local():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    debate_session_id = data.get('session_id')
    message = data.get('message')

    if debate_session_id not in active_debates:
        return jsonify({'error': 'Session not found'}), 404

    debate_session = active_debates[debate_session_id]

    # Display user message
    user_msg = {
        'speaker': 'user',
        'text': message,
        'timestamp': datetime.now().isoformat(),
        'speaker_name': 'You'
    }
    debate_session['messages'].append(user_msg)
    socketio.emit('debate_message', user_msg, room=debate_session_id)

    # Restart debate with user's message in context
    prompt = f"[User interrupts]: {message}\n\nEach therapist briefly respond to the user's question, then continue the debate."
    thread = threading.Thread(target=run_debate_async, args=(debate_session_id, prompt))
    thread.daemon = True
    thread.start()

    return jsonify({'success': True})

@app.route('/api/agents/pause_debate', methods=['POST'])
def pause_debate_local():
    data = request.get_json()
    debate_session_id = data.get('session_id')
    if debate_session_id in active_debates:
        active_debates[debate_session_id]['is_active'] = False
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404


@app.route('/api/agents/resume_debate', methods=['POST'])
def resume_debate_local():
    data = request.get_json()
    debate_session_id = data.get('session_id')
    if debate_session_id in active_debates:
        active_debates[debate_session_id]['is_active'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404


# ==================== SocketIO Events ====================
#
# @socketio.on('join_debate')
# def handle_join(data):
#     debate_session_id = data.get('session_id')
#     if debate_session_id:
#         join_room(debate_session_id)
#         emit('joined', {'session_id': debate_session_id})




# Fix the SocketIO join handler
@socketio.on('join_debate')
def handle_join(data):
    debate_session_id = data.get('session_id')
    if debate_session_id:
        join_room(debate_session_id)
        print(f"✓ Client joined room: {debate_session_id} (SID: {request.sid})")
        # Send confirmation back to the specific client
        emit('joined', {'session_id': debate_session_id})

        # Also send any existing messages to the newly joined client
        if debate_session_id in active_debates:
            existing_messages = active_debates[debate_session_id].get('messages', [])
            for msg in existing_messages:
                emit('debate_message', msg)


@socketio.on('leave_debate')
def handle_leave(data):
    debate_session_id = data.get('session_id')
    if debate_session_id:
        leave_room(debate_session_id)


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Add this debugging endpoint
@app.route('/api/agents/debug', methods=['GET'])
def debug_agents():
    """Debug agent system status"""
    return jsonify({
        'active_debates': list(active_debates.keys()),
        'debate_details': {
            session_id: {
                'topic': session['topic'],
                'message_count': len(session['messages']),
                'is_active': session['is_active']
            }
            for session_id, session in active_debates.items()
        }
    })


@app.route('/api/agents/test_emit', methods=['POST'])
def test_emit():
    """Test Socket.IO emission"""
    data = request.get_json()
    session_id = data.get('session_id', 'test_room')

    test_msg = {
        'speaker': 'sarah',
        'text': 'This is a test message from Dr. Sarah Chen!',
        'timestamp': datetime.now().isoformat(),
        'speaker_name': 'Dr. Sarah Chen'
    }

    socketio.emit('debate_message', test_msg, room=session_id)
    print(f"✓ Test message emitted to room: {session_id}")

    return jsonify({
        'success': True,
        'message': 'Test message sent',
        'room': session_id
    })


@app.route('/api/agents/get_messages', methods=['GET'])
def get_debate_messages():
    """Get all messages for a debate session (polling fallback)"""
    session_id = request.args.get('session_id')

    if not session_id or session_id not in active_debates:
        return jsonify({'success': False, 'error': 'Session not found'}), 404

    messages = active_debates[session_id].get('messages', [])

    return jsonify({
        'success': True,
        'session_id': session_id,
        'messages': messages,
        'count': len(messages)
    })



@app.route('/api/debug/session', methods=['GET'])
def debug_session():
    """Debug session status"""
    return jsonify({
        'has_session': 'user_id' in session,
        'user_id': session.get('user_id'),
        'session_keys': list(session.keys())
    })
# ==================== Initialize ====================
if __name__ == '__main__':
    init_db()
    print("NeuroShield Flask Backend Starting...")
    print("Database initialized")
    print("ML model loaded")
    print("Server running on http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)  # Changed from app.run to socketio.run