import requests

s = requests.Session()

# 1. Register user
register_url = "http://127.0.0.1:5000/api/register"
register_payload = {"username": "testuser", "password": "testpass"}
r = s.post(register_url, json=register_payload)
print("Register:", r.json())

# 2. Login
login_url = "http://127.0.0.1:5000/api/login"
login_payload = {"username": "testuser", "password": "testpass"}
r = s.post(login_url, json=login_payload)
print("Login:", r.json())

# 3. Send chat message
chat_url = "http://127.0.0.1:5000/api/nlp/message"
chat_payload = {"message": "I feel anxious"}
r = s.post(chat_url, json=chat_payload)
print("Chat:", r.json())
