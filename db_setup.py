"""
Database Setup Script for NeuroShield
Creates and initializes SQLite database with sample data
"""

import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import random

DATABASE = 'neuroshield.db'


def create_database():
    """Create database and all tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       username
                       TEXT
                       UNIQUE
                       NOT
                       NULL,
                       password_hash
                       TEXT
                       NOT
                       NULL,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       anonymous_id
                       TEXT
                       UNIQUE,
                       consent_research
                       BOOLEAN
                       DEFAULT
                       0
                   )
                   ''')

    # Streaks table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS streaks
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER
                       NOT
                       NULL,
                       current_streak
                       INTEGER
                       DEFAULT
                       0,
                       longest_streak
                       INTEGER
                       DEFAULT
                       0,
                       last_check_in
                       DATE,
                       total_clean_days
                       INTEGER
                       DEFAULT
                       0,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   ''')

    # Journal entries table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS journal_entries
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER
                       NOT
                       NULL,
                       entry_date
                       DATE
                       NOT
                       NULL,
                       mood
                       TEXT,
                       triggers
                       TEXT,
                       note
                       TEXT,
                       created_at
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   ''')

    # EEG sessions table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS eeg_sessions
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER
                       NOT
                       NULL,
                       session_start
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       session_end
                       TIMESTAMP,
                       avg_risk_score
                       REAL,
                       triggered_count
                       INTEGER
                       DEFAULT
                       0,
                       focused_count
                       INTEGER
                       DEFAULT
                       0,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   ''')

    # Brain states table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS brain_states
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       session_id
                       INTEGER
                       NOT
                       NULL,
                       timestamp
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       state
                       TEXT
                       NOT
                       NULL,
                       confidence
                       REAL
                       NOT
                       NULL,
                       risk_score
                       REAL,
                       FOREIGN
                       KEY
                   (
                       session_id
                   ) REFERENCES eeg_sessions
                   (
                       id
                   )
                       )
                   ''')

    # Chat history table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS chat_history
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER
                       NOT
                       NULL,
                       message
                       TEXT
                       NOT
                       NULL,
                       sender
                       TEXT
                       NOT
                       NULL,
                       timestamp
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   ''')

    # Emergency events table
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS emergency_events
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER
                       NOT
                       NULL,
                       timestamp
                       TIMESTAMP
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       action_taken
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       user_id
                   ) REFERENCES users
                   (
                       id
                   )
                       )
                   ''')

    conn.commit()
    conn.close()
    print("✓ Database tables created successfully")


def populate_sample_data():
    """Add sample data for demo purposes"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create demo user
    demo_password = generate_password_hash('demo123')
    cursor.execute('''
                   INSERT
                   OR IGNORE INTO users (username, password_hash, anonymous_id, consent_research)
        VALUES (?, ?, ?, ?)
                   ''', ('demo_user', demo_password, 'anon_demo001', 1))

    user_id = cursor.lastrowid or 1

    # Add streak data
    cursor.execute('''
                   INSERT
                   OR IGNORE INTO streaks (user_id, current_streak, longest_streak, total_clean_days, last_check_in)
        VALUES (?, ?, ?, ?, ?)
                   ''', (user_id, 7, 14, 45, datetime.now().date()))

    # Add sample journal entries
    moods = ['great', 'good', 'neutral', 'struggling']
    triggers = ['None', 'Stress', 'Boredom', 'Social Media', 'Loneliness']

    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).date()
        cursor.execute('''
                       INSERT INTO journal_entries (user_id, entry_date, mood, triggers, note)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (
                           user_id,
                           date,
                           random.choice(moods),
                           random.choice(triggers),
                           f"Day {7 - i} - Feeling {random.choice(['strong', 'motivated', 'challenged', 'determined'])}"
                       ))

    # Add sample EEG sessions
    for i in range(3):
        session_start = datetime.now() - timedelta(hours=i * 24)
        session_end = session_start + timedelta(minutes=30)

        cursor.execute('''
                       INSERT INTO eeg_sessions (user_id, session_start, session_end, avg_risk_score, triggered_count,
                                                 focused_count)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', (user_id, session_start, session_end, random.uniform(0.2, 0.4), random.randint(2, 5),
                             random.randint(15, 25)))

        session_id = cursor.lastrowid

        # Add brain states for this session
        for j in range(20):
            timestamp = session_start + timedelta(minutes=j * 1.5)
            state = random.choice(['focused', 'focused', 'focused', 'triggered'])  # More focused than triggered
            confidence = random.uniform(0.7, 0.95)
            risk_score = random.uniform(0.1, 0.5) if state == 'focused' else random.uniform(0.6, 0.9)

            cursor.execute('''
                           INSERT INTO brain_states (session_id, timestamp, state, confidence, risk_score)
                           VALUES (?, ?, ?, ?, ?)
                           ''', (session_id, timestamp, state, confidence, risk_score))

    # Add sample chat history
    sample_conversations = [
        ('user', 'I had a tough day today'),
        ('coach', 'I hear you. What made today challenging?'),
        ('user', 'Feeling stressed about work'),
        ('coach', 'Stress is a common trigger. Let\'s do a quick breathing exercise together.'),
    ]

    for sender, message in sample_conversations:
        cursor.execute('''
                       INSERT INTO chat_history (user_id, message, sender, timestamp)
                       VALUES (?, ?, ?, ?)
                       ''', (user_id, message, sender, datetime.now() - timedelta(hours=2)))

    # Add sample emergency events
    for i in range(3):
        cursor.execute('''
                       INSERT INTO emergency_events (user_id, timestamp, action_taken)
                       VALUES (?, ?, ?)
                       ''', (user_id, datetime.now() - timedelta(days=i * 2), 'breathing_exercise'))

    conn.commit()
    conn.close()
    print("✓ Sample data populated successfully")


def reset_database():
    """Drop all tables and recreate"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    tables = ['users', 'streaks', 'journal_entries', 'eeg_sessions',
              'brain_states', 'chat_history', 'emergency_events']

    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')

    conn.commit()
    conn.close()
    print("✓ Database reset complete")


def show_stats():
    """Display database statistics"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)

    tables = [
        ('Users', 'users'),
        ('Streaks', 'streaks'),
        ('Journal Entries', 'journal_entries'),
        ('EEG Sessions', 'eeg_sessions'),
        ('Brain States', 'brain_states'),
        ('Chat Messages', 'chat_history'),
        ('Emergency Events', 'emergency_events')
    ]

    for name, table in tables:
        count = cursor.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        print(f"{name:20s}: {count:5d} records")

    print("=" * 50 + "\n")

    conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Resetting database...")
        reset_database()

    print("Creating database structure...")
    create_database()

    print("Populating with sample data...")
    populate_sample_data()

    show_stats()

    print("\n✓ Database setup complete!")
    print("\nDemo credentials:")
    print("  Username: demo_user")
    print("  Password: demo123")
    print("\nStart the Flask app with: python app.py")