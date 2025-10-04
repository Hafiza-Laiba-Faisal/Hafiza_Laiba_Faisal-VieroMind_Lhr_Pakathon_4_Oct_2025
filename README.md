
---

# 🧠 HealTalk — AI-Powered Recovery Support Platform



![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**HealTalk** is an AI-driven mental health and recovery support platform that combines EEG-based emotional state detection, multi-agent therapy discussions, and an AI support coach — built to assist users in their emotional healing journey.

---

## 🚀 Core Features

* 🧠 **EEG-Based Brain State Detection** – Identifies focused, triggered, or relaxed states in real-time.
* 💬 **Multi-Agent AI Therapy Roundtable** – Six AI therapists with distinct specializations discuss and recommend approaches.
* 🤖 **AI Support Coach (24/7)** – Personalized emotional and behavioral guidance via OpenRouter GPT models.
* 📅 **Daily Streak Tracking** – Keeps users motivated on their recovery progress.
* 📓 **Digital Journal** – Records emotions, triggers, and personal reflections.
* 🆘 **Emergency Help Tools** – Breathing guidance and calming interventions.

---

## 🧩 AI Therapist Roles

| Name                | Specialization               |
| ------------------- | ---------------------------- |
| Dr. Sarah Chen      | Cognitive Behavioral Therapy |
| Dr. James Williams  | Holistic Healing             |
| Dr. Maria Rodriguez | Psychodynamic Therapy        |
| Dr. David Thompson  | Psychiatry & Neuroscience    |
| Dr. Lisa Park       | Trauma & EMDR                |
| Dr. Michael Chen    | Mindfulness & Meditation     |

---

## 🛠️ Tech Stack

**Backend:**

* Flask (Python)
* Flask-SocketIO (Real-time communication)
* SQLite (Local database)
* AutoGen (Multi-agent orchestration)
* OpenRouter GPT (AI dialogue system)

**Frontend:**

* Bootstrap 5
* Chart.js
* jQuery
* Socket.IO (WebSocket communication)

---

## ⚙️ Installation

```bash
# 1. Clone repository
git clone https://github.com/Hafiza-Laiba-Faisal/Hafiza_Laiba_Faisal-VieroMind_Lhr_Pakathon_4_Oct_2025.git
cd HealTalk

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate   # (Windows: venv\Scripts\activate)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Access at: **[http://localhost:5000](http://localhost:5000)**

---

## 🧠 API Overview

| Endpoint                   | Method   | Description                |
| -------------------------- | -------- | -------------------------- |
| `/api/login`               | POST     | User login                 |
| `/api/register`            | POST     | New user registration      |
| `/api/nlp/message`         | POST     | Chat with AI Support Coach |
| `/api/agents/start_debate` | POST     | Begin AI therapy debate    |
| `/api/user/streak`         | GET/POST | View or update streak      |
| `/api/journal`             | GET/POST | Manage journal entries     |

---

## 📊 EEG Integration (Optional)

* Upload `.npy` EEG files
* Signal classified as **Focused**, **Triggered**, or **Relaxed**
* Visualized in real-time charts
* Helps correlate emotional states with recovery progress

---

## 🧘 Ethical Note

HealTalk is a **supportive, educational tool** — not a replacement for professional therapy or treatment.
All data is anonymized, encrypted, and used responsibly.

---

## 📢 Acknowledgments

* **AutoGen Framework** by Microsoft Research
* **OpenRouter** for GPT model integration
* **VieroMind Pakathon 2025** organizing team

---



**Developed by:** Hafiza Laiba Faisal
**Project:** HealTalk
**Mission:** “Empowering recovery through AI-driven emotional support.”

---

Would you like me to make a **shorter hackathon summary version** (for GitHub description or submission form) too?
