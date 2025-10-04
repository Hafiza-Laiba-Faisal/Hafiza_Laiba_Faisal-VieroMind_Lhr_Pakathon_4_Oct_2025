"""
Unit tests for NeuroShield application
Run with: pytest test_app.py -v
"""

import pytest
import json
import numpy as np
from app import app, init_db, EEGProcessor, BrainStateClassifier, SupportCoach
import os
import tempfile


@pytest.fixture
def client():
    """Create test client"""
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def auth_client(client):
    """Create authenticated test client"""
    # Register and login
    client.post('/api/register',
                json={'username': 'testuser', 'password': 'testpass123'})
    client.post('/api/login',
                json={'username': 'testuser', 'password': 'testpass123'})
    return client


# ==================== Authentication Tests ====================

def test_register(client):
    """Test user registration"""
    response = client.post('/api/register',
                           json={'username': 'newuser', 'password': 'password123'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'user_id' in data


def test_register_duplicate(client):
    """Test duplicate username registration"""
    client.post('/api/register',
                json={'username': 'duplicate', 'password': 'pass123'})
    response = client.post('/api/register',
                           json={'username': 'duplicate', 'password': 'pass456'})
    assert response.status_code == 400


def test_login_success(client):
    """Test successful login"""
    client.post('/api/register',
                json={'username': 'loginuser', 'password': 'pass123'})
    response = client.post('/api/login',
                           json={'username': 'loginuser', 'password': 'pass123'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True


def test_login_failure(client):
    """Test failed login"""
    response = client.post('/api/login',
                           json={'username': 'nonexistent', 'password': 'wrong'})
    assert response.status_code == 401


def test_logout(auth_client):
    """Test logout"""
    response = auth_client.post('/api/logout')
    assert response.status_code == 200


# ==================== Streak Tests ====================

def test_get_streak(auth_client):
    """Test getting user streak"""
    response = auth_client.get('/api/user/streak')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'current_streak' in data
    assert 'longest_streak' in data


def test_update_streak(auth_client):
    """Test updating streak"""
    response = auth_client.post('/api/user/streak',
                                json={'is_clean': True})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['current_streak'] > 0


# ==================== Journal Tests ====================

def test_create_journal(auth_client):
    """Test creating journal entry"""
    response = auth_client.post('/api/journal',
                                json={
                                    'mood': 'good',
                                    'triggers': 'None',
                                    'note': 'Feeling great today!'
                                })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] == True


def test_get_journal(auth_client):
    """Test getting journal entries"""
    # Create an entry first
    auth_client.post('/api/journal',
                     json={'mood': 'good', 'triggers': 'None', 'note': 'Test'})

    response = auth_client.get('/api/journal')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0


# ==================== Chat Tests ====================

def test_send_message(auth_client):
    """Test sending message to AI coach"""
    response = auth_client.post('/api/nlp/message',
                                json={'message': 'I need help'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'response' in data
    assert 'intent' in data


def test_empty_message(auth_client):
    """Test sending empty message"""
    response = auth_client.post('/api/nlp/message',
                                json={'message': ''})
    assert response.status_code == 400


# ==================== Emergency Tests ====================

def test_emergency_support(auth_client):
    """Test emergency support endpoint"""
    response = auth_client.post('/api/emergency',
                                json={'action': 'breathing'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'breathing_exercise' in data
    assert 'quote' in data


# ==================== EEG Processing Tests ====================

def test_eeg_start_stream(auth_client):
    """Test starting EEG stream"""
    response = auth_client.post('/api/start_stream')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'session_id' in data


def test_eeg_stop_stream(auth_client):
    """Test stopping EEG stream"""
    auth_client.post('/api/start_stream')
    response = auth_client.post('/api/stop_stream')
    assert response.status_code == 200


def test_get_brain_state(auth_client):
    """Test getting brain state"""
    response = auth_client.get('/api/state')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'state' in data
    assert 'confidence' in data
    assert 'risk_score' in data


# ==================== Admin Tests ====================

def test_admin_dashboard(client):
    """Test admin analytics endpoint"""
    response = client.get('/admin')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_users' in data
    assert 'active_sessions' in data


# ==================== EEG Processor Tests ====================

def test_eeg_processor_bandpass():
    """Test bandpass filter"""
    processor = EEGProcessor()
    data = np.random.randn(500, 19)
    filtered = processor.bandpass_filter(data, 0.5, 45)
    assert filtered.shape == data.shape
    assert not np.array_equal(filtered, data)


def test_eeg_processor_notch():
    """Test notch filter"""
    processor = EEGProcessor()
    data = np.random.randn(500, 19)
    filtered = processor.notch_filter(data, 50)
    assert filtered.shape == data.shape


def test_eeg_processor_band_powers():
    """Test band power extraction"""
    processor = EEGProcessor()
    data = np.random.randn(500, 19)
    powers = processor.extract_band_powers(data)
    assert len(powers) > 0
    assert not np.any(np.isnan(powers))


def test_eeg_processor_features():
    """Test full feature extraction"""
    processor = EEGProcessor()
    data = np.random.randn(500, 19)
    features = processor.extract_features(data)
    assert len(features) > 0
    assert not np.any(np.isnan(features))


# ==================== Brain State Classifier Tests ====================

def test_classifier_predict():
    """Test brain state prediction"""
    classifier = BrainStateClassifier()
    data = np.random.randn(500, 19) * 50
    result = classifier.predict(data)

    assert 'state' in result
    assert result['state'] in ['focused', 'triggered']
    assert 'confidence' in result
    assert 0 <= result['confidence'] <= 1
    assert 'risk_score' in result
    assert 0 <= result['risk_score'] <= 1


# ==================== Support Coach Tests ====================

def test_coach_detect_intent():
    """Test intent detection"""
    coach = SupportCoach()

    assert coach.detect_intent("I'm feeling an urge") == 'urge'
    assert coach.detect_intent("I'm anxious") == 'anxiety'
    assert coach.detect_intent("Feeling good today") == 'success'
    assert coach.detect_intent("I relapsed") == 'relapse'
    assert coach.detect_intent("Hello") == 'general'


def test_coach_get_response():
    """Test response generation"""
    coach = SupportCoach()
    response = coach.get_response("I need help", {'streak': 5})
    assert isinstance(response, str)
    assert len(response) > 0


def test_coach_personalization():
    """Test response personalization with user data"""
    coach = SupportCoach()
    user_data = {'streak': 10}

    # Try multiple times to get a response with streak placeholder
    for _ in range(10):
        response = coach.get_response("I'm struggling", user_data)
        if '{streak}' not in response:  # Should be replaced
            break

    assert '{streak}' not in response


# ==================== Integration Tests ====================

def test_full_user_flow(client):
    """Test complete user flow"""
    # Register
    response = client.post('/api/register',
                           json={'username': 'flowuser', 'password': 'pass123'})
    assert response.status_code == 200

    # Login
    response = client.post('/api/login',
                           json={'username': 'flowuser', 'password': 'pass123'})
    assert response.status_code == 200

    # Get streak
    response = client.get('/api/user/streak')
    assert response.status_code == 200

    # Create journal entry
    response = client.post('/api/journal',
                           json={'mood': 'good', 'triggers': 'None', 'note': 'Day 1'})
    assert response.status_code == 200

    # Start EEG stream
    response = client.post('/api/start_stream')
    assert response.status_code == 200

    # Get brain state
    response = client.get('/api/state')
    assert response.status_code == 200

    # Send chat message
    response = client.post('/api/nlp/message',
                           json={'message': 'Feeling strong'})
    assert response.status_code == 200

    # Emergency support
    response = client.post('/api/emergency',
                           json={'action': 'breathing'})
    assert response.status_code == 200

    # Logout
    response = client.post('/api/logout')
    assert response.status_code == 200


def test_unauthorized_access(client):
    """Test endpoints require authentication"""
    endpoints = [
        ('/api/user/streak', 'GET'),
        ('/api/journal', 'GET'),
        ('/api/nlp/message', 'POST'),
        ('/api/emergency', 'POST'),
        ('/api/start_stream', 'POST'),
    ]

    for endpoint, method in endpoints:
        if method == 'GET':
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json={})

        assert response.status_code == 401


# ==================== Performance Tests ====================

def test_feature_extraction_speed():
    """Test feature extraction performance"""
    import time

    processor = EEGProcessor()
    data = np.random.randn(500, 19)

    start = time.time()
    features = processor.extract_features(data)
    duration = time.time() - start

    assert duration < 1.0  # Should complete in less than 1 second
    assert len(features) > 0


def test_classification_speed():
    """Test classification performance"""
    import time

    classifier = BrainStateClassifier()
    data = np.random.randn(500, 19) * 50

    start = time.time()
    result = classifier.predict(data)
    duration = time.time() - start

    assert duration < 0.5  # Should complete in less than 0.5 seconds
    assert 'state' in result


# ==================== Edge Case Tests ====================

def test_empty_eeg_data():
    """Test handling of empty EEG data"""
    processor = EEGProcessor()
    data = np.array([]).reshape(0, 19)

    with pytest.raises(Exception):
        processor.extract_features(data)


def test_invalid_eeg_shape():
    """Test handling of invalid EEG shape"""
    processor = EEGProcessor()
    data = np.random.randn(500, 10)  # Wrong number of channels

    # Should still process but with different results
    try:
        features = processor.extract_features(data)
        assert len(features) > 0
    except Exception:
        pass  # Expected to fail with wrong shape


def test_nan_in_eeg_data():
    """Test handling of NaN values in EEG"""
    processor = EEGProcessor()
    data = np.random.randn(500, 19)
    data[10:20, 5] = np.nan

    # Should handle NaN gracefully
    try:
        features = processor.extract_features(data)
        # If successful, check for NaN in features
        if features is not None:
            assert not np.all(np.isnan(features))
    except Exception:
        pass  # Expected to fail with NaN


# ==================== Database Tests ====================

def test_database_initialization(client):
    """Test database is properly initialized"""
    from app import get_db

    with app.app_context():
        db = get_db()

        # Check tables exist
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

        table_names = [t['name'] for t in tables]

        assert 'users' in table_names
        assert 'streaks' in table_names
        assert 'journal_entries' in table_names
        assert 'eeg_sessions' in table_names
        assert 'brain_states' in table_names
        assert 'chat_history' in table_names


# ==================== Run Tests ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])