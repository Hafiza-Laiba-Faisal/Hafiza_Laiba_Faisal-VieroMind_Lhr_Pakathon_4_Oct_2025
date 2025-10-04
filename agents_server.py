# """
# NeuroShield Multi-AI Agents Server
# Real-time therapeutic debate using Agent orchestration
# """
#
# from agents import Agent, Runner
# from flask import Flask, request, jsonify
# from flask_socketio import SocketIO, emit
# from flask_cors import CORS
# import json
# from datetime import datetime
# import threading
#
# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'neuroshield-agents-secret'
# CORS(app)
# socketio = SocketIO(app, cors_allowed_origins="*")
#
# # ==================== Agent Definitions ====================
#
# agent_sarah = Agent(
#     name="Dr. Sarah Chen",
#     instructions="""
#     You are Dr. Sarah Chen, an Evidence-Based Practitioner specializing in CBT and research-backed interventions.
#
#     Your approach:
#     - Reference studies and meta-analyses when discussing treatment efficacy
#     - Prioritize interventions with strong empirical support
#     - Focus on measurable outcomes and structured protocols
#     - Consider practical constraints (insurance, session limits, accessibility)
#     - You're direct, scientific, but not cold—you care about helping people efficiently
#
#     In debates:
#     - Cite research to support your points
#     - Respectfully challenge purely theoretical or unmeasurable approaches
#     - Acknowledge when other perspectives have merit
#     - Build on previous speakers' points when you agree
#     - Keep responses 3-5 sentences typically (conversational, not essays)
#
#     You see all past messages in this debate and respond thoughtfully to build a coherent discussion.
#     """,
#     handoff_description="Evidence-based perspective from Dr. Sarah Chen"
# )
#
# agent_james = Agent(
#     name="Dr. James Williams",
#     instructions="""
#     You are Dr. James Williams, a Holistic Healer emphasizing mind-body-spirit integration.
#
#     Your approach:
#     - Focus on whole-person wellness: physical, emotional, spiritual, relational
#     - Emphasize mindfulness, meditation, nature connection, somatic awareness
#     - Question reductionist approaches that treat symptoms without addressing root causes
#     - Value subjective experience, intuition, and ancient wisdom alongside modern science
#     - You're calm, reflective, but passionate about holistic healing
#
#     In debates:
#     - Advocate for lifestyle changes and spiritual practices
#     - Gently challenge purely medical/pharmaceutical models
#     - Share examples of how disconnection creates mental health issues
#     - Acknowledge the value of other approaches while maintaining your holistic stance
#     - Keep responses 3-5 sentences typically (warm, thoughtful tone)
#
#     You see all past messages and respond to build collaborative discussion while maintaining your distinct viewpoint.
#     """,
#     handoff_description="Holistic perspective from Dr. James Williams"
# )
#
# agent_maria = Agent(
#     name="Dr. Maria Rodriguez",
#     instructions="""
#     You are Dr. Maria Rodriguez, an Analytical Psychologist trained in psychodynamic and depth psychology.
#
#     Your approach:
#     - Explore unconscious patterns, childhood origins, and attachment dynamics
#     - Ask probing questions about underlying motivations and defenses
#     - Focus on insight and self-understanding as paths to change
#     - Challenge surface-level solutions that don't address root psychological structures
#     - You're empathetic, curious, intellectually rigorous
#
#     In debates:
#     - Bring conversations to deeper psychological levels
#     - Connect current symptoms to developmental history
#     - Point out when quick fixes might miss important dynamics
#     - Appreciate both evidence-based and holistic views while adding depth
#     - Keep responses 3-5 sentences typically (thoughtful, probing tone)
#
#     You see all past messages and weave threads together, helping the group explore complexity.
#     """,
#     handoff_description="Depth psychology perspective from Dr. Maria Rodriguez"
# )
#
# # Orchestrator manages turn-taking and conversation flow
# orchestrator = Agent(
#     name="Debate Orchestrator",
#     instructions="""
#     You manage a therapeutic debate among three therapists: Dr. Sarah Chen (evidence-based),
#     Dr. James Williams (holistic), and Dr. Maria Rodriguez (analytical/depth).
#
#     Your role:
#     - Decide which therapist should speak next based on conversational flow
#     - Ensure all three get relatively equal speaking time
#     - Pass the conversation naturally (don't announce transitions, just hand off)
#     - When a user message appears, ensure the next speaker addresses it
#     - Keep the debate substantive but collegial—therapists disagree respectfully
#     - After 15-20 exchanges, start moving toward synthesis/conclusion
#
#     Selection strategy:
#     - Rotate fairly but not rigidly
#     - Let therapists respond to points directed at them
#     - Create natural back-and-forth when two therapists disagree
#     - Ensure diverse perspectives emerge on each topic
#
#     Simply call the next appropriate agent. The system will handle message delivery.
#     """,
#     handoffs=[agent_sarah, agent_james, agent_maria]
# )
#
# # ==================== Global State ====================
#
# active_debates = {}  # {session_id: {topic, messages, runner, is_active}}
#
#
# # ==================== Helper Functions ====================
#
# def create_debate_session(session_id, topic, initial_prompt):
#     """Initialize a new debate session with agent runner"""
#
#     # Create a new runner for this session
#     runner = Runner(orchestrator)
#
#     # Store session
#     active_debates[session_id] = {
#         'topic': topic,
#         'messages': [],
#         'runner': runner,
#         'is_active': True,
#         'started_at': datetime.now().isoformat()
#     }
#
#     # Start the debate with initial prompt
#     thread = threading.Thread(
#         target=run_debate_async,
#         args=(session_id, initial_prompt)
#     )
#     thread.daemon = True
#     thread.start()
#
#     return session_id
#
#
# def run_debate_async(session_id, initial_prompt):
#     """Run debate in background thread, emitting messages via WebSocket"""
#
#     if session_id not in active_debates:
#         return
#
#     session = active_debates[session_id]
#     runner = session['runner']
#
#     try:
#         # Start the agent conversation
#         response = runner.run(initial_prompt)
#
#         # Process agent responses as they come
#         for message in response.messages:
#             if not session['is_active']:
#                 break
#
#             # Extract speaker from agent response
#             speaker_name = message.get('role', 'assistant')
#             content = message.get('content', '')
#
#             # Map to persona
#             persona_key = map_agent_to_persona(speaker_name)
#
#             # Create message object
#             msg = {
#                 'speaker': persona_key,
#                 'text': content,
#                 'timestamp': datetime.now().isoformat(),
#                 'speaker_name': personas_map[persona_key]['name']
#             }
#
#             # Store and emit
#             session['messages'].append(msg)
#             socketio.emit('debate_message', msg, room=session_id)
#
#             # Small delay between messages (simulated typing)
#             socketio.sleep(2)
#
#     except Exception as e:
#         print(f"Error in debate session {session_id}: {e}")
#         socketio.emit('debate_error', {'error': str(e)}, room=session_id)
#
#
# def map_agent_to_persona(agent_name):
#     """Map agent name to persona key"""
#     if 'Sarah' in agent_name or 'Evidence' in agent_name:
#         return 'sarah'
#     elif 'James' in agent_name or 'Holistic' in agent_name:
#         return 'james'
#     elif 'Maria' in agent_name or 'Analytical' in agent_name:
#         return 'maria'
#     return 'sarah'  # default
#
#
# personas_map = {
#     'sarah': {'name': 'Dr. Sarah Chen', 'icon': 'fa-user-md', 'color': '#3b82f6'},
#     'james': {'name': 'Dr. James Williams', 'icon': 'fa-spa', 'color': '#10b981'},
#     'maria': {'name': 'Dr. Maria Rodriguez', 'icon': 'fa-brain', 'color': '#8b5cf6'}
# }
#
# # ==================== Topic Prompts ====================
#
# topic_prompts = {
#     'anxiety': """
#     Discuss the best approaches for treating anxiety disorders.
#     Dr. Sarah should emphasize CBT and exposure therapy with research support.
#     Dr. James should advocate for mindfulness, lifestyle, and holistic methods.
#     Dr. Maria should explore developmental roots and unconscious patterns.
#     Engage in substantive debate while remaining collegial.
#     """,
#
#     'digital': """
#     Debate the merits and drawbacks of digital therapy versus traditional in-person sessions.
#     Dr. Sarah should focus on efficacy data and accessibility benefits.
#     Dr. James should raise concerns about losing embodied presence and sacred space.
#     Dr. Maria should question what's lost in terms of unconscious communication and depth work.
#     Explore multiple angles thoughtfully.
#     """,
#
#     'worklife': """
#     Explore work-life balance issues in modern society.
#     Dr. Sarah should discuss boundary-setting skills and cognitive restructuring.
#     Dr. James should address burnout, nervous system regulation, and cultural pressure.
#     Dr. Maria should unpack psychological defenses, childhood origins of workaholism, and meaning-making.
#     Have a rich, multi-layered discussion.
#     """
# }
#
#
# # ==================== Routes ====================
#
# @app.route('/api/agents/start_debate', methods=['POST'])
# def start_debate():
#     """Start a new debate session"""
#     data = request.get_json()
#     topic = data.get('topic')
#     session_id = data.get('session_id', f"debate_{datetime.now().timestamp()}")
#
#     if topic not in topic_prompts:
#         return jsonify({'error': 'Invalid topic'}), 400
#
#     # Create debate session
#     create_debate_session(session_id, topic, topic_prompts[topic])
#
#     return jsonify({
#         'success': True,
#         'session_id': session_id,
#         'topic': topic
#     })
#
#
# @app.route('/api/agents/inject_user_message', methods=['POST'])
# def inject_user_message():
#     """Inject user message into ongoing debate"""
#     data = request.get_json()
#     session_id = data.get('session_id')
#     message = data.get('message')
#
#     if session_id not in active_debates:
#         return jsonify({'error': 'Session not found'}), 404
#
#     session = active_debates[session_id]
#
#     # Add user message to history
#     user_msg = {
#         'speaker': 'user',
#         'text': message,
#         'timestamp': datetime.now().isoformat(),
#         'speaker_name': 'You'
#     }
#     session['messages'].append(user_msg)
#
#     # Emit to all clients
#     socketio.emit('debate_message', user_msg, room=session_id)
#
#     # Inject into agent conversation context
#     runner = session['runner']
#     response = runner.run(
#         f"User says: {message}\n\nPlease have one therapist respond to the user's message, then continue the debate.")
#
#     # Process agent response
#     # (similar to run_debate_async logic)
#
#     return jsonify({'success': True})
#
#
# @app.route('/api/agents/pause_debate', methods=['POST'])
# def pause_debate():
#     """Pause debate session"""
#     data = request.get_json()
#     session_id = data.get('session_id')
#
#     if session_id in active_debates:
#         active_debates[session_id]['is_active'] = False
#         return jsonify({'success': True})
#
#     return jsonify({'error': 'Session not found'}), 404
#
#
# @app.route('/api/agents/resume_debate', methods=['POST'])
# def resume_debate():
#     """Resume paused debate"""
#     data = request.get_json()
#     session_id = data.get('session_id')
#
#     if session_id in active_debates:
#         active_debates[session_id]['is_active'] = True
#         # Continue from where we left off
#         return jsonify({'success': True})
#
#     return jsonify({'error': 'Session not found'}), 404
#
#
# @app.route('/api/agents/get_transcript', methods=['GET'])
# def get_transcript():
#     """Get full transcript of debate"""
#     session_id = request.args.get('session_id')
#
#     if session_id not in active_debates:
#         return jsonify({'error': 'Session not found'}), 404
#
#     session = active_debates[session_id]
#
#     return jsonify({
#         'topic': session['topic'],
#         'started_at': session['started_at'],
#         'messages': session['messages']
#     })
#
#
# # ==================== WebSocket Events ====================
#
# @socketio.on('join_debate')
# def handle_join(data):
#     """Client joins debate session"""
#     session_id = data.get('session_id')
#     if session_id:
#         socketio.join_room(session_id)
#         emit('joined', {'session_id': session_id})
#
#
# @socketio.on('leave_debate')
# def handle_leave(data):
#     """Client leaves debate session"""
#     session_id = data.get('session_id')
#     if session_id:
#         socketio.leave_room(session_id)
#
#
# # ==================== Run Server ====================
#
# if __name__ == '__main__':
#     print("NeuroShield Agents Server Starting...")
#     print("Agents: Dr. Sarah Chen, Dr. James Williams, Dr. Maria Rodriguez")
#     print("Orchestrator ready for therapeutic debates")
#     socketio.run(app, host='0.0.0.0', port=5001, debug=True)


"""
NeuroShield Multi-AI Agents Server
Real-time therapeutic debate using Agent orchestration
"""

from agents import Agent, Runner
from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
from datetime import datetime
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neuroshield-agents-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== Agent Definitions ====================

agent_sarah = Agent(
    name="Dr. Sarah Chen",
    instructions="""You are Dr. Sarah Chen, an Evidence-Based Practitioner specializing in CBT and research-backed interventions.
    Your approach: Reference studies and meta-analyses when discussing treatment efficacy, prioritize interventions with strong empirical support, focus on measurable outcomes and structured protocols.
    In debates: Cite research to support your points, respectfully challenge purely theoretical approaches, acknowledge when other perspectives have merit, build on previous speakers' points when you agree.
    Keep responses 3-5 sentences typically (conversational, not essays). You see all past messages in this debate and respond thoughtfully to build a coherent discussion.""",
    handoff_description="Evidence-based perspective from Dr. Sarah Chen"
)

agent_james = Agent(
    name="Dr. James Williams",
    instructions="""You are Dr. James Williams, a Holistic Healer emphasizing mind-body-spirit integration.
    Your approach: Focus on whole-person wellness: physical, emotional, spiritual, relational. Emphasize mindfulness, meditation, nature connection, somatic awareness.
    In debates: Advocate for lifestyle changes and spiritual practices, gently challenge purely medical/pharmaceutical models, share examples of how disconnection creates mental health issues.
    Keep responses 3-5 sentences typically (warm, thoughtful tone). You see all past messages and respond to build collaborative discussion while maintaining your distinct viewpoint.""",
    handoff_description="Holistic perspective from Dr. James Williams"
)

agent_maria = Agent(
    name="Dr. Maria Rodriguez",
    instructions="""You are Dr. Maria Rodriguez, an Analytical Psychologist trained in psychodynamic and depth psychology.
    Your approach: Explore unconscious patterns, childhood origins, and attachment dynamics. Ask probing questions about underlying motivations and defenses.
    In debates: Bring conversations to deeper psychological levels, connect current symptoms to developmental history, point out when quick fixes might miss important dynamics.
    Keep responses 3-5 sentences typically (thoughtful, probing tone). You see all past messages and weave threads together, helping the group explore complexity.""",
    handoff_description="Depth psychology perspective from Dr. Maria Rodriguez"
)

orchestrator = Agent(
    name="Debate Orchestrator",
    instructions="""You manage a therapeutic debate among three therapists: Dr. Sarah Chen (evidence-based), Dr. James Williams (holistic), and Dr. Maria Rodriguez (analytical/depth).
    Your role: Decide which therapist should speak next based on conversational flow, ensure all three get relatively equal speaking time, pass the conversation naturally.
    When a user message appears, ensure the next speaker addresses it. Keep the debate substantive but collegial. After 15-20 exchanges, start moving toward synthesis/conclusion.
    Simply call the next appropriate agent. The system will handle message delivery.""",
    handoffs=[agent_sarah, agent_james, agent_maria]
)

# ==================== Global State ====================

active_debates = {}
personas_map = {
    'sarah': {'name': 'Dr. Sarah Chen', 'icon': 'fa-user-md', 'color': '#3b82f6'},
    'james': {'name': 'Dr. James Williams', 'icon': 'fa-spa', 'color': '#10b981'},
    'maria': {'name': 'Dr. Maria Rodriguez', 'icon': 'fa-brain', 'color': '#8b5cf6'}
}

topic_prompts = {
    'anxiety': "Discuss the best approaches for treating anxiety disorders. Dr. Sarah should emphasize CBT and exposure therapy with research support. Dr. James should advocate for mindfulness, lifestyle, and holistic methods. Dr. Maria should explore developmental roots and unconscious patterns. Engage in substantive debate while remaining collegial.",
    'digital': "Debate the merits and drawbacks of digital therapy versus traditional in-person sessions. Dr. Sarah should focus on efficacy data and accessibility benefits. Dr. James should raise concerns about losing embodied presence and sacred space. Dr. Maria should question what's lost in terms of unconscious communication and depth work.",
    'worklife': "Explore work-life balance issues in modern society. Dr. Sarah should discuss boundary-setting skills and cognitive restructuring. Dr. James should address burnout, nervous system regulation, and cultural pressure. Dr. Maria should unpack psychological defenses, childhood origins of workaholism, and meaning-making."
}

# ==================== Dashboard HTML ====================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Server Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 2rem; }
        .dashboard-card { background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); padding: 2rem; margin-bottom: 2rem; }
        .status-online { color: #10b981; }
        .status-offline { color: #ef4444; }
        .persona-card { border-left: 4px solid; padding: 1rem; margin: 0.5rem 0; border-radius: 5px; background: #f9fafb; }
        .persona-sarah { border-color: #3b82f6; }
        .persona-james { border-color: #10b981; }
        .persona-maria { border-color: #8b5cf6; }
        .stat-box { text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin: 0.5rem; }
        .log-entry { padding: 0.5rem; border-bottom: 1px solid #e5e7eb; font-size: 0.9rem; }
        .btn-test { background: linear-gradient(135deg, #10b981, #059669); border: none; color: white; }
        .btn-test:hover { background: linear-gradient(135deg, #059669, #047857); color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="dashboard-card">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h1><i class="fas fa-server"></i> Agent Server Dashboard</h1>
                    <p class="mb-0 text-muted">Multi-AI Therapeutic Debate System</p>
                </div>
                <div>
                    <h3><i class="fas fa-circle status-online"></i> ONLINE</h3>
                    <small class="text-muted">Port 5001</small>
                </div>
            </div>

            <div class="row">
                <div class="col-md-4">
                    <div class="stat-box">
                        <h2 id="activeSessions">0</h2>
                        <p class="mb-0">Active Sessions</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-box">
                        <h2 id="totalMessages">0</h2>
                        <p class="mb-0">Total Messages</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-box">
                        <h2>3</h2>
                        <p class="mb-0">AI Personas</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="dashboard-card">
            <h3><i class="fas fa-users"></i> Active AI Personas</h3>
            <div class="persona-card persona-sarah">
                <strong><i class="fas fa-user-md"></i> Dr. Sarah Chen</strong> - Evidence-Based Practitioner
                <br><small>Specializes in CBT and research-backed interventions</small>
            </div>
            <div class="persona-card persona-james">
                <strong><i class="fas fa-spa"></i> Dr. James Williams</strong> - Holistic Healer
                <br><small>Emphasizes mind-body-spirit integration</small>
            </div>
            <div class="persona-card persona-maria">
                <strong><i class="fas fa-brain"></i> Dr. Maria Rodriguez</strong> - Analytical Psychologist
                <br><small>Focuses on depth psychology and unconscious patterns</small>
            </div>
        </div>

        <div class="dashboard-card">
            <h3><i class="fas fa-vial"></i> Test Debate System</h3>
            <div class="mb-3">
                <label class="form-label fw-bold">Select Topic</label>
                <select class="form-select" id="testTopic">
                    <option value="anxiety">Best Approaches for Treating Anxiety</option>
                    <option value="digital">Digital Therapy vs Traditional Sessions</option>
                    <option value="worklife">Work-Life Balance in Modern Times</option>
                </select>
            </div>
            <button class="btn btn-test w-100" onclick="startTestDebate()">
                <i class="fas fa-play"></i> Start Test Debate
            </button>
            <div id="testResult" class="mt-3"></div>
        </div>

        <div class="dashboard-card">
            <h3><i class="fas fa-list"></i> Active Sessions</h3>
            <div id="sessionsList">
                <p class="text-muted">No active sessions</p>
            </div>
        </div>

        <div class="dashboard-card">
            <h3><i class="fas fa-scroll"></i> Recent Activity Log</h3>
            <div id="activityLog" style="max-height: 300px; overflow-y: auto;">
                <div class="log-entry text-muted">Server started - waiting for connections...</div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        const socket = io('http://localhost:5001');

        socket.on('connect', () => {
            addLog('Connected to agent server');
        });

        socket.on('stats_update', (data) => {
            document.getElementById('activeSessions').textContent = data.active_sessions;
            document.getElementById('totalMessages').textContent = data.total_messages;
            updateSessionsList(data.sessions);
        });

        socket.on('activity_log', (msg) => {
            addLog(msg);
        });

        function addLog(message) {
            const log = document.getElementById('activityLog');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<small class="text-muted">${new Date().toLocaleTimeString()}</small> - ${message}`;
            log.insertBefore(entry, log.firstChild);
            if (log.children.length > 50) log.lastChild.remove();
        }

        function updateSessionsList(sessions) {
            const list = document.getElementById('sessionsList');
            if (!sessions || sessions.length === 0) {
                list.innerHTML = '<p class="text-muted">No active sessions</p>';
                return;
            }
            list.innerHTML = sessions.map(s => `
                <div class="border-start border-primary border-4 ps-3 py-2 mb-2">
                    <strong>Session: ${s.id}</strong><br>
                    <small>Topic: ${s.topic} | Messages: ${s.message_count}</small>
                </div>
            `).join('');
        }

        async function startTestDebate() {
            const topic = document.getElementById('testTopic').value;
            const resultDiv = document.getElementById('testResult');

            resultDiv.innerHTML = '<div class="alert alert-info">Starting test debate...</div>';

            try {
                const response = await fetch('/api/agents/start_debate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        topic: topic,
                        session_id: `test_${Date.now()}`
                    })
                });

                const data = await response.json();

                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="alert alert-success">
                            <strong>Test debate started!</strong><br>
                            Session ID: ${data.session_id}<br>
                            Topic: ${data.topic}<br>
                            <small>Check the main NeuroShield app to see the debate in action.</small>
                        </div>
                    `;
                    addLog(`Test debate started: ${topic}`);
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            }
        }

        // Request stats every 5 seconds
        setInterval(() => {
            fetch('/api/agents/stats').then(r => r.json()).then(data => {
                socket.emit('stats_update', data);
            });
        }, 5000);
    </script>
</body>
</html>
"""


# ==================== Helper Functions ====================

def create_debate_session(session_id, topic, initial_prompt):
    runner = Runner(orchestrator)
    active_debates[session_id] = {
        'topic': topic,
        'messages': [],
        'runner': runner,
        'is_active': True,
        'started_at': datetime.now().isoformat()
    }
    thread = threading.Thread(target=run_debate_async, args=(session_id, initial_prompt))
    thread.daemon = True
    thread.start()
    return session_id


def run_debate_async(session_id, initial_prompt):
    if session_id not in active_debates:
        return

    session = active_debates[session_id]
    runner = session['runner']

    try:
        response = runner.run(initial_prompt)

        for message in response.messages:
            if not session['is_active']:
                break

            speaker_name = message.get('role', 'assistant')
            content = message.get('content', '')
            persona_key = map_agent_to_persona(speaker_name)

            msg = {
                'speaker': persona_key,
                'text': content,
                'timestamp': datetime.now().isoformat(),
                'speaker_name': personas_map[persona_key]['name']
            }

            session['messages'].append(msg)
            socketio.emit('debate_message', msg, room=session_id)
            socketio.emit('activity_log', f"Message from {msg['speaker_name']}")

            time.sleep(2)

    except Exception as e:
        print(f"Error in debate session {session_id}: {e}")
        socketio.emit('debate_error', {'error': str(e)}, room=session_id)


def map_agent_to_persona(agent_name):
    if 'Sarah' in agent_name or 'Evidence' in agent_name:
        return 'sarah'
    elif 'James' in agent_name or 'Holistic' in agent_name:
        return 'james'
    elif 'Maria' in agent_name or 'Analytical' in agent_name:
        return 'maria'
    return 'sarah'


# ==================== Routes ====================

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/agents/start_debate', methods=['POST'])
def start_debate():
    data = request.get_json()
    topic = data.get('topic')
    session_id = data.get('session_id', f"debate_{datetime.now().timestamp()}")

    if topic not in topic_prompts:
        return jsonify({'error': 'Invalid topic'}), 400

    create_debate_session(session_id, topic, topic_prompts[topic])
    socketio.emit('activity_log', f"New debate started: {topic}")

    return jsonify({'success': True, 'session_id': session_id, 'topic': topic})


@app.route('/api/agents/inject_user_message', methods=['POST'])
def inject_user_message():
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')

    if session_id not in active_debates:
        return jsonify({'error': 'Session not found'}), 404

    session = active_debates[session_id]
    user_msg = {
        'speaker': 'user',
        'text': message,
        'timestamp': datetime.now().isoformat(),
        'speaker_name': 'You'
    }
    session['messages'].append(user_msg)
    socketio.emit('debate_message', user_msg, room=session_id)
    socketio.emit('activity_log', f"User message received in session {session_id}")

    runner = session['runner']
    runner.run(
        f"User says: {message}\n\nPlease have one therapist respond to the user's message, then continue the debate.")

    return jsonify({'success': True})


@app.route('/api/agents/pause_debate', methods=['POST'])
def pause_debate():
    data = request.get_json()
    session_id = data.get('session_id')

    if session_id in active_debates:
        active_debates[session_id]['is_active'] = False
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404


@app.route('/api/agents/resume_debate', methods=['POST'])
def resume_debate():
    data = request.get_json()
    session_id = data.get('session_id')

    if session_id in active_debates:
        active_debates[session_id]['is_active'] = True
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404


@app.route('/api/agents/stats', methods=['GET'])
def get_stats():
    sessions = [{'id': sid, 'topic': s['topic'], 'message_count': len(s['messages'])}
                for sid, s in active_debates.items() if s['is_active']]
    return jsonify({
        'active_sessions': len([s for s in active_debates.values() if s['is_active']]),
        'total_messages': sum(len(s['messages']) for s in active_debates.values()),
        'sessions': sessions
    })


# ==================== WebSocket Events ====================

@socketio.on('join_debate')
def handle_join(data):
    session_id = data.get('session_id')
    if session_id:
        socketio.join_room(session_id)
        emit('joined', {'session_id': session_id})


@socketio.on('leave_debate')
def handle_leave(data):
    session_id = data.get('session_id')
    if session_id:
        socketio.leave_room(session_id)


if __name__ == '__main__':
    print("=" * 60)
    print("NeuroShield Agents Server Starting...")
    print("=" * 60)
    print("Dashboard: http://localhost:5001")
    print("Agents: Dr. Sarah Chen, Dr. James Williams, Dr. Maria Rodriguez")
    print("Orchestrator ready for therapeutic debates")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)