/**
 * NeuroShield Frontend Application
 * Handles UI interactions and API calls
 * Coach Tab = 1-on-1 Support | Multi-AI Tab = Separate 3-Agent Debate
 */
let selectedAgents = ['sarah', 'james', 'maria', 'david', 'lisa', 'michael']; // Default: all 6

let eegChart;
let isStreaming = false;
let streamInterval;
let breathingInterval;

// Multi-AI Agent State (separate from coach)
let agentSocket = null;
let agentSessionId = null;
let agentTopic = null;
let agentHistory = [];
let agentSpeed = 1;
let agentPaused = false;

// Updated personas for 6 agents
const personas = {
    sarah: {
        name: "Dr. Sarah Chen",
        icon: "fa-user-md",
        color: "#3b82f6",
        className: "persona-sarah",
        avatar: "👩‍⚕️",
        role: "CBT Expert"
    },
    james: {
        name: "Dr. James Williams",
        icon: "fa-spa",
        color: "#10b981",
        className: "persona-james",
        avatar: "🧘‍♂️",
        role: "Holistic Healer"
    },
    maria: {
        name: "Dr. Maria Rodriguez",
        icon: "fa-brain",
        color: "#8b5cf6",
        className: "persona-maria",
        avatar: "👩‍🔬",
        role: "Psychologist"
    },
    david: {
        name: "Dr. David Thompson",
        icon: "fa-pills",
        color: "#ef4444",
        className: "persona-david",
        avatar: "👨‍⚕️",
        role: "Psychiatrist"
    },
    lisa: {
        name: "Dr. Lisa Park",
        icon: "fa-heart",
        color: "#f59e0b",
        className: "persona-lisa",
        avatar: "👩‍⚕️",
        role: "Trauma Specialist"
    },
    michael: {
        name: "Dr. Michael Chen",
        icon: "fa-om",
        color: "#06b6d4",
        className: "persona-michael",
        avatar: "🧘",
        role: "Mindfulness Expert"
    }
};

// Replace the topic prompts section
const topicDescriptions = {
    'anxiety': {
        title: 'Treating Anxiety',
        description: 'Compare CBT, medication, holistic, and trauma-informed approaches',
        icon: '😰',
        duration: '8 min',
        category: 'Clinical'
    },
    'digital_therapy': {
        title: 'Digital vs In-Person',
        description: 'The effectiveness of online therapy for addiction recovery',
        icon: '💻',
        duration: '9 min',
        category: 'Technology'
    },
    'work_life': {
        title: 'Work-Life Balance',
        description: 'Managing work stress to prevent relapses',
        icon: '⚖️',
        duration: '8 min',
        category: 'Lifestyle'
    },
    'depression': {
        title: 'Depression & Addiction',
        description: 'Understanding the depression-addiction connection',
        icon: '💬',
        duration: '10 min',
        category: 'Clinical'
    },
    'child_psychology': {
        title: 'Teen Early Intervention',
        description: 'Age-appropriate approaches for adolescents',
        icon: '👶',
        duration: '8 min',
        category: 'Pediatric'
    },
    'sleep': {
        title: 'Sleep & Recovery',
        description: 'Addressing sleep disturbances triggering relapses',
        icon: '😴',
        duration: '7 min',
        category: 'Sleep'
    },
    'self_esteem': {
        title: 'Self-Esteem & Recovery',
        description: 'Addressing low self-worth as a trigger',
        icon: '💪',
        duration: '8 min',
        category: 'Psychology'
    },
    'relapse_prevention': {
        title: 'Relapse Prevention',
        description: 'Sustainable strategies for maintaining recovery',
        icon: '🛡️',
        duration: '9 min',
        category: 'Recovery'
    }
};




// ============================================
// PART 3: Update renderParticipants Function
// ============================================

// Replace the existing renderParticipants function
function renderParticipants() {
    const container = $('#participantsSidebar');
    container.html('<h6>Participants</h6>');

    // Only render selected agents
    selectedAgents.forEach(agentKey => {
        const persona = personas[agentKey];
        container.append(`
            <div class="participant-item active" data-agent="${agentKey}">
                <div class="participant-avatar" style="background: ${persona.color};">${persona.avatar}</div>
                <div class="participant-info">
                    <div class="participant-name">${persona.name.replace('Dr. ', '')}</div>
                    <div class="participant-role">${persona.role}</div>
                </div>
                <div class="status-dot"></div>
            </div>
        `);
    });

    // Add user
    container.append(`
        <div class="participant-item">
            <div class="participant-avatar" style="background: #4f46e5;">👤</div>
            <div class="participant-info">
                <div class="participant-name">You</div>
                <div class="participant-role">Participant</div>
            </div>
            <div class="status-dot"></div>
        </div>
    `);
}


// Initialize on page load
$(document).ready(function() {
    initEEGChart();
    loadStreak();
    loadJournalEntries();
    initMultiAgentSocket();
    setupMultiAgentControls();

const journalForm = $('#journalForm');
if (journalForm.length) {
    journalForm.on('submit', handleJournalSubmit);
}
    $('#chatInput').on('keypress', function(e) {
        if (e.which === 13) sendMessage();
    });
    $('#multiagentInput').on('keypress', function(e) {
        if (e.which === 13) sendMultiAgentMessage();
    });
});

// ==================== Multi-AI WebSocket (Port 5000) ====================

function initMultiAgentSocket() {
    agentSocket = io('http://localhost:5000', {
        withCredentials: true,
        transports: ['websocket', 'polling'] // Ensure both transports are supported
    });

    agentSocket.on('connect', () => {
        console.log('✓ Multi-AI Socket connected, ID:', agentSocket.id);
    });

    agentSocket.on('debate_message', (data) => {
        console.log('📥 Debate message received:', data);
        displayMultiAgentMessage(data);
    });

    agentSocket.on('debate_error', (err) => {
        console.error('❌ Debate error:', err);
        showError('Multi-AI error: ' + err.error);
    });

    agentSocket.on('joined', (data) => {
        console.log('✓ Joined debate room:', data.session_id);
        // Ensure the frontend stores the session ID
        agentSessionId = data.session_id;
    });

    agentSocket.on('connect_error', (error) => {
        console.error('❌ Socket connection error:', error);
        showError('Socket connection failed: ' + error.message);
    });

    agentSocket.on('disconnect', () => {
        console.warn('⚠ Socket disconnected');
    });
}

// Add to app.js
let messagePollingInterval = null;

function startMessagePolling(sessionId) {
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
    }

    let lastMessageCount = 0;

    messagePollingInterval = setInterval(async () => {
        try {
            console.log(`📬 Polling for messages in session: ${sessionId}`);
            const response = await fetch(`/api/agents/get_messages?session_id=${sessionId}`, {
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.success && data.messages.length > lastMessageCount) {
                console.log(`📬 Found ${data.messages.length - lastMessageCount} new messages`);
                const newMessages = data.messages.slice(lastMessageCount);
                newMessages.forEach(msg => {
                    console.log('📥 Polled message:', msg.text.substring(0, 50) + '...');
                    displayMultiAgentMessage(msg);
                });
                lastMessageCount = data.messages.length;
            }
        } catch (error) {
            console.error('❌ Polling error:', error);
        }
    }, 3000);
}
function stopMessagePolling() {
    if (messagePollingInterval) {
        clearInterval(messagePollingInterval);
        messagePollingInterval = null;
    }
}

// function setupMultiAgentControls() {
//     $('#topicSelect').on('change', startMultiAgentDebate);
//     $('#pauseBtn').on('click', toggleMultiAgentPause);
//     $('#restartBtn').on('click', restartMultiAgentDebate);
//     $('#speedControl').on('change', updateMultiAgentSpeed);
//     $('#exportJSON').on('click', () => exportMultiAgentTranscript('json'));
//     $('#exportTXT').on('click', () => exportMultiAgentTranscript('txt'));
// }

function setupMultiAgentControls() {
    // Controls are now handled via onclick in HTML
    console.log('Multi-agent controls ready');
}

// Replace the startMultiAgentDebate function
async function startMultiAgentDebate() {
    const topic = $('#topicSelect').val();
    if (!topic) return;

    agentHistory = [];
    $('#multiagentContainer').html('<div class="message message-coach">Starting debate on: ' + topic + '...</div>');
    agentPaused = false;

    // Generate session ID
    agentSessionId = `debate_${Date.now()}`;
    agentTopic = topic;

    // Join the room
    console.log('📍 Joining room:', agentSessionId);
    agentSocket.emit('join_debate', { session_id: agentSessionId });

    // Wait for join confirmation
    await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            console.warn('⚠️ Join confirmation timeout');
            showError('Failed to join debate room');
            reject(new Error('Join timeout'));
        }, 5000);

        agentSocket.once('joined', (data) => {
            clearTimeout(timeout);
            console.log('✅ Joined room confirmed:', data.session_id);
            resolve();
        });
    });

    // Start the debate
    try {
        const response = await fetch('/api/agents/start_debate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({ topic, session_id: agentSessionId })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to start debate');
        }

        $('#pauseBtn, #restartBtn, #exportBtn').prop('disabled', false);
        $('#pauseBtn').html('<i class="fas fa-pause"></i> Pause');
        showSuccess('Multi-AI debate started!');
        console.log('✅ Debate started with session ID:', agentSessionId);

        // Start polling as a fallback
        startMessagePolling(agentSessionId);
    } catch (error) {
        console.error('❌ Failed to start debate:', error);
        showError('Failed to start debate: ' + error.message);
    }
}


// function displayMultiAgentMessage(msg) {
//     console.log('📥 Displaying message:', {
//         speaker: msg.speaker,
//         text: msg.text.substring(0, 50) + '...',
//         timestamp: msg.timestamp
//     });
//
//     const persona = msg.speaker === 'user' ? null : personas[msg.speaker];
//
//     if (msg.speaker !== 'user') {
//         if (!agentPaused) {
//             showMultiAgentTyping(persona || personas.sarah);
//             setTimeout(() => {
//                 hideMultiAgentTyping();
//                 appendMultiAgentMessage(msg, persona);
//             }, 1500 / agentSpeed);
//         } else {
//             appendMultiAgentMessage(msg, persona);
//         }
//     } else {
//         appendMultiAgentMessage(msg, null);
//     }
// }

// Update message display to handle all 6 agents
function displayMultiAgentMessage(msg) {
    console.log('📥 Displaying message:', {
        speaker: msg.speaker,
        text: msg.text.substring(0, 50) + '...',
        timestamp: msg.timestamp
    });

    const persona = msg.speaker === 'user' ? null : personas[msg.speaker];

    if (!persona && msg.speaker !== 'user') {
        console.warn('Unknown speaker:', msg.speaker);
        return;
    }

    if (msg.speaker !== 'user') {
        if (!agentPaused) {
            showMultiAgentTyping(persona);
            setTimeout(() => {
                hideMultiAgentTyping();
                appendMultiAgentMessage(msg, persona);
                highlightActiveParticipant(msg.speaker);
            }, 1500 / agentSpeed);
        } else {
            appendMultiAgentMessage(msg, persona);
        }
    } else {
        appendMultiAgentMessage(msg, null);
    }
}

function highlightActiveParticipant(agentKey) {
    $('.participant-item').removeClass('speaking');
    $(`.participant-item[data-agent="${agentKey}"]`).addClass('speaking');

    setTimeout(() => {
        $('.participant-item').removeClass('speaking');
    }, 2000);
}


function appendMultiAgentMessage(msg, persona) {
    const container = $('#multiagentContainer');
    const messageDiv = $('<div>').addClass('message');

    if (persona) {
        messageDiv.addClass(`message-ai ${persona.className}`);
        messageDiv.html(`
            <div class="avatar" style="background: ${persona.color};">${persona.avatar}</div>
            <div class="content">
                <div class="persona-header">${persona.name}</div>
                <div class="text">${msg.text}</div>
                <div class="timestamp">${new Date(msg.timestamp).toLocaleTimeString()}</div>
            </div>
        `);
    } else {
        messageDiv.addClass('message message-user');
        messageDiv.html(`
            <div>${msg.text}</div>
            <div class="timestamp">${new Date(msg.timestamp).toLocaleTimeString()}</div>
        `);
    }

    console.log('Appending message to DOM:', msg.text.substring(0, 50) + '...');
    container.append(messageDiv);
    container.scrollTop(container[0].scrollHeight);
    agentHistory.push(msg);
}


function showMultiAgentTyping(persona) {
    $('#agentTyping').remove();
    $('#multiagentContainer').append(`
        <div class="typing-indicator" id="agentTyping">
            <div class="avatar" style="background: ${persona.color};">${persona.avatar}</div>
            <div>
                <div class="typing-dots"><span></span><span></span><span></span></div>
            </div>
        </div>
    `);
    $('#multiagentContainer').scrollTop($('#multiagentContainer')[0].scrollHeight);
}

function hideMultiAgentTyping() {
    $('#agentTyping').remove();
}

async function sendMultiAgentMessage() {
    const input = $('#multiagentInput');
    const message = input.val().trim();

    if (!message) return;

    if (!agentSessionId) {
        showError('Please select a topic first');
        return;
    }

    // Clear input immediately
    input.val('');

    try {
        const response = await fetch('/api/agents/inject_user_message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({
                session_id: agentSessionId,
                message: message
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to send message');
        }

        // Add user badge if not present
        if (!$('.participant-badge.user-badge').length) {
            $('#participantList').append(`
                <div class="participant-badge user-badge active">
                    <i class="fas fa-user" style="color: #4f46e5;"></i><span>You</span>
                </div>
            `);
        }

        console.log('User message sent successfully');
    } catch (error) {
        console.error('Failed to send message:', error);
        showError('Failed to send message: ' + error.message);
    }
}

async function toggleMultiAgentPause() {
    agentPaused = !agentPaused;
    const endpoint = agentPaused ? 'pause_debate' : 'resume_debate';

    try {
        await fetch(`/api/agents/${endpoint}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({ session_id: agentSessionId })
        });

        $('#pauseBtn').html(agentPaused ? '<i class="fas fa-play"></i> Resume' : '<i class="fas fa-pause"></i> Pause');
    } catch (error) {
        console.error('Failed to toggle pause:', error);
    }
}

function restartMultiAgentDebate() {
    if (agentTopic && agentSessionId) {
        agentSocket.emit('leave_debate', { session_id: agentSessionId });
        $('#topicSelect').val(agentTopic).trigger('change');
    }
}
// In your frontend code
fetch('/api/state', {
    method: 'GET',
    credentials: 'include',  // ← Critical for session cookies
    headers: {
        'Content-Type': 'application/json'
    }
})

function updateMultiAgentSpeed() {
    agentSpeed = parseFloat($('#speedControl').val());
}

function exportMultiAgentTranscript(format) {
    const data = {
        topic: $('#topicSelect option:selected').text(),
        started_at: new Date().toISOString(),
        messages: agentHistory
    };
    let content, filename, type;

    if (format === 'json') {
        content = JSON.stringify(data, null, 2);
        filename = `debate_${agentTopic}_${Date.now()}.json`;
        type = 'application/json';
    } else {
        content = `Multi-AI Therapist Debate\nTopic: ${data.topic}\n\n`;
        agentHistory.forEach(m => {
            content += `[${new Date(m.timestamp).toLocaleTimeString()}] ${m.speaker_name || 'User'}:\n${m.text}\n\n`;
        });
        filename = `debate_${agentTopic}_${Date.now()}.txt`;
        type = 'text/plain';
    }

    const blob = new Blob([content], {type});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    showSuccess('Transcript exported!');
}

// ==================== EEG Visualization ====================

function initEEGChart() {
    const ctx = document.getElementById('eegChart').getContext('2d');
    const initialData = Array(50).fill(0);

    eegChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(50).fill(''),
            datasets: [{
                label: 'EEG Signal',
                data: initialData,
                borderColor: '#10b981',
                borderWidth: 2,
                fill: false,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: { beginAtZero: true, max: 100, grid: { color: '#374151' }, ticks: { color: '#10b981' } },
                x: { grid: { display: false }, ticks: { display: false } }
            },
            plugins: { legend: { display: false } },
            animation: { duration: 0 }
        }
    });
}

function updateEEGChart() {
    const newValue = Math.random() * 100;
    eegChart.data.datasets[0].data.shift();
    eegChart.data.datasets[0].data.push(newValue);
    eegChart.update();
}

// ==================== Streaming Control ====================

$('#toggleStream').click(function() {
    isStreaming ? stopStream() : startStream();
});

function startStream() {
    isStreaming = true;
    $('#toggleStream').html('<i class="fas fa-stop"></i> Stop Stream');
    $.post('/api/start_stream', function(response) { console.log('Stream started:', response); });
    streamInterval = setInterval(function() { updateEEGChart(); updateBrainState(); }, 1000);
}

function stopStream() {
    isStreaming = false;
    $('#toggleStream').html('<i class="fas fa-play"></i> Start Stream');
    clearInterval(streamInterval);
    $.post('/api/stop_stream', function(response) { console.log('Stream stopped:', response); });
}

// ==================== Brain State ====================

function updateBrainState() {
    $.get('/api/state', function(response) {
        const { state, confidence, risk_score } = response;
        $('#stateText').text(state.toUpperCase());
        $('#confidence').text((confidence * 100).toFixed(0) + '%');
        const stateCard = $('#brainState');
        stateCard.removeClass('state-focused state-triggered state-relaxed').addClass('state-' + state);
        if (state === 'triggered' && risk_score > 0.7) showRiskAlert(risk_score);
    }).fail(() => console.log('Demo mode'));
}

function showRiskAlert(riskScore) {
    if (!$('#riskAlert').length) {
        const alert = $(`
            <div id="riskAlert" class="alert alert-warning alert-dismissible fade show position-fixed" 
                 style="top: 20px; right: 20px; z-index: 9999; max-width: 300px;">
                <strong>High Risk Detected</strong><br>Risk Score: ${(riskScore * 100).toFixed(0)}%<br>
                <small>Consider taking a break or using the emergency button.</small>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);
        $('body').append(alert);
        setTimeout(() => $('#riskAlert').alert('close'), 10000);
    }
}

// ==================== Streak Management ====================

function loadStreak() {
    $.get('/api/user/streak', function(response) {
        const { current_streak, longest_streak, total_clean_days } = response;
        $('#streakBadge').text(current_streak);
        $('#currentStreak').text(current_streak + ' days');
        $('#longestStreak').text(longest_streak + ' days');
        $('#totalDays').text(total_clean_days + ' days');
        $('#modalStreak').text(current_streak);
    }).fail(() => console.log('Demo mode'));
}

// ==================== Journal ====================

function handleJournalSubmit(e) {
    e.preventDefault();
    const formData = {
        mood: $('[name="mood"]').val(),
        triggers: $('[name="triggers"]').val(),
        note: $('[name="note"]').val(),
        date: new Date().toISOString().split('T')[0]
    };
    $.ajax({
        url: '/api/journal',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function() {
            showSuccess('Journal entry saved!');
            $('#journalForm')[0].reset();
            loadJournalEntries();
        },
        error: () => showError('Failed to save entry')
    });
}

function loadJournalEntries() {
    $.get('/api/journal', function(entries) {
        const container = $('#journalEntries');
        container.empty();
        if (entries.length === 0) {
            container.html('<p class="text-muted">No entries yet. Start journaling today!</p>');
            return;
        }
        entries.forEach(entry => {
            container.append(`
                <div class="border-start border-primary border-4 ps-3 py-2 mb-3">
                    <div class="d-flex justify-content-between">
                        <small class="text-muted">${entry.entry_date}</small>
                        <span class="badge bg-secondary">${entry.mood}</span>
                    </div>
                    <p class="mb-1 mt-2"><strong>Triggers:</strong> ${entry.triggers || 'None'}</p>
                    <p class="mb-0">${entry.note}</p>
                </div>
            `);
        });
    });
}

// ==================== AI Coach Chat (1-on-1 Support) ====================

function sendMessage() {
    const input = $('#chatInput');
    const message = input.val().trim();
    if (!message) return;

    addMessageToChat(message, 'user');
    input.val('');

    $.ajax({
        url: '/api/nlp/message',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ message }),
        success: function(response) { addMessageToChat(response.response, 'coach'); },
        error: function() {
            const demoResponses = [
                "That's completely normal. Take a deep breath and remember why you started this journey.",
                "You're doing great! Your commitment shows real strength. Keep going!",
                "When you feel an urge, try the breathing exercise or write in your journal.",
                "Every day clean is a victory. You're building a healthier future.",
                "I'm here for you 24/7. What's on your mind right now?"
            ];
            setTimeout(() => addMessageToChat(demoResponses[Math.floor(Math.random() * demoResponses.length)], 'coach'), 500);
        }
    });
}

function addMessageToChat(text, sender) {
    const container = $('#chatContainer');
    const messageClass = sender === 'user' ? 'message-user ms-auto' : 'message-coach';
    container.append(`<div class="message ${messageClass}">${text}</div>`);
    container.scrollTop(container[0].scrollHeight);
}

// ==================== Emergency Support ====================

function showEmergency() {
    $.post('/api/emergency', { action: 'breathing' });
    $('#emergencyModal').modal('show');
    startBreathingCycle();
}

function startBreathingCycle() {
    const phases = ['INHALE (4s)', 'HOLD (4s)', 'EXHALE (6s)', 'HOLD (2s)'];
    const durations = [4000, 4000, 6000, 2000];
    let currentPhase = 0;
    function updatePhase() {
        $('#breathingPhase').text(phases[currentPhase]);
        currentPhase = (currentPhase + 1) % phases.length;
    }
    if (breathingInterval) clearInterval(breathingInterval);
    updatePhase();
    breathingInterval = setInterval(updatePhase, durations[currentPhase % durations.length]);
}

$('#emergencyModal').on('hidden.bs.modal', function() {
    if (breathingInterval) {
        clearInterval(breathingInterval);
        breathingInterval = null;
    }
});

// ==================== Navigation ====================

function activateTab(tabId) {
    $(`a[href="#${tabId}"]`).tab('show');
}

// ==================== Notifications ====================

function showSuccess(message) { showNotification(message, 'success'); }
function showError(message) { showNotification(message, 'danger'); }

function showNotification(message, type) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 9999; max-width: 350px;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('body').append(alertHtml);
    setTimeout(() => $('.alert').alert('close'), 5000);
}


// agentSocket.on('debate_message', (data) => {
//     console.log('📥 RAW MESSAGE RECEIVED:', JSON.stringify(data, null, 2));
//     displayMultiAgentMessage(data);
// });



agentSocket.on('disconnect', () => {
    console.warn('⚠️ Socket disconnected');
});

agentSocket.on('connect_error', (error) => {
    console.error('❌ Connection error:', error);
});

// Add to the top of app.js, right after initMultiAgentSocket()
window.debugSocket = function() {
    console.log('Socket Status:', {
        connected: agentSocket.connected,
        id: agentSocket.id,
        active_session: agentSessionId,
        history_length: agentHistory.length
    });
};

window.testSocketEmit = async function() {
    try {
        const response = await fetch('/api/agents/test_emit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({ session_id: agentSessionId || 'test_room' })
        });

        const data = await response.json();
        console.log('Test emit result:', data);
    } catch (error) {
        console.error('Test emit failed:', error);
    }
};

// Enhanced message handler with detailed logging
agentSocket.on('debate_message', (data) => {
    console.log('📥 RAW MESSAGE RECEIVED:', {
        speaker: data.speaker,
        text: data.text.substring(0, 100),
        timestamp: data.timestamp,
        full_data: data
    });
    displayMultiAgentMessage(data);
});

window.testSocketConnection = async function() {
    console.log('🧪 Testing socket connection...');

    // Test 1: Check if socket is connected
    console.log('Socket connected:', agentSocket.connected);
    console.log('Socket ID:', agentSocket.id);

    // Test 2: Try joining a test room
    const testRoom = 'test_room_' + Date.now();
    console.log('Joining test room:', testRoom);
    agentSocket.emit('join_debate', { session_id: testRoom });

    // Test 3: Request a test message from backend
    try {
        const response = await fetch('/api/agents/test_emit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({ session_id: testRoom })
        });

        const data = await response.json();
        console.log('✅ Test emit response:', data);
        showSuccess('Test message sent! Check console for details.');
    } catch (error) {
        console.error('❌ Test failed:', error);
        showError('Test failed: ' + error.message);
    }
};

// Add these functions to your existing app.js

// Topic selection and navigation
function selectDebateTopic(topicId, topicTitle, description, duration, category) {
    // Hide topic selection, show chat
    $('#topicSelectionView').hide();
    $('#chatView').show();

    // Update display
    $('#currentTopicDisplay').text(topicTitle);

    // Store topic info
    agentTopic = topicId;

    // Start the debate
    startDebateWithTopic(topicId, topicTitle);
}

// Updated selectRandomTopic function with all 8 topics
// function selectRandomTopic() {
//     const topics = [
//         {id: 'anxiety', title: 'Treating Anxiety'},
//         {id: 'digital_therapy', title: 'Digital vs In-Person'},
//         {id: 'work_life', title: 'Work-Life Balance'},
//         {id: 'depression', title: 'Depression & Addiction'},
//         {id: 'child_psychology', title: 'Teen Early Intervention'},
//         {id: 'sleep', title: 'Sleep & Recovery'},
//         {id: 'self_esteem', title: 'Self-Esteem & Recovery'},
//         {id: 'relapse_prevention', title: 'Relapse Prevention'}
//     ];
//
//     const random = topics[Math.floor(Math.random() * topics.length)];
//     selectDebateTopic(random.id, random.title, '', '6 min', 'Random');
// }

// Update selectRandomTopic for all 8 topics
function selectRandomTopic() {
    const topicKeys = Object.keys(topicDescriptions);
    const randomKey = topicKeys[Math.floor(Math.random() * topicKeys.length)];
    const topic = topicDescriptions[randomKey];
    selectDebateTopic(randomKey, topic.title, topic.description, topic.duration, topic.category);
}


// Initialize participants when chat view is shown
function showChatView() {
    $('#topicSelectionView').hide();
    $('#chatView').show();
    renderParticipants();
}


// Keep selectDebateTopic as is (already correct)
function selectDebateTopic(topicId, topicTitle, description, duration, category) {
    console.log('Selecting topic:', topicId, topicTitle);

    // Hide topic selection, show chat
    $('#topicSelectionView').hide();
    $('#chatView').show();

    // Update display
    $('#currentTopicDisplay').text(topicTitle);

    // Store topic info
    agentTopic = topicId;

    // Start the debate
    startDebateWithTopic(topicId, topicTitle);
}



// ============================================
// PART 4: Update startDebateWithTopic Function
// ============================================

// Replace the existing startDebateWithTopic function
async function startDebateWithTopic(topicId, topicTitle) {
    agentHistory = [];
    $('#multiagentContainer').html(`<div class="message message-coach">Starting ${selectedAgents.length}-agent roundtable on: ${topicTitle}...</div>`);
    agentPaused = false;
    agentSessionId = `debate_${Date.now()}`;

    showChatView(); // Initialize participants (will show only selected agents)

    console.log('Joining room:', agentSessionId);
    console.log('Selected agents:', selectedAgents);

    agentSocket.emit('join_debate', { session_id: agentSessionId });

    await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            console.warn('Join confirmation timeout');
            showError('Failed to join debate room');
            reject(new Error('Join timeout'));
        }, 5000);

        agentSocket.once('joined', (data) => {
            clearTimeout(timeout);
            console.log('Joined room confirmed:', data.session_id);
            resolve();
        });
    });

    try {
        const response = await fetch('/api/agents/start_debate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({
                topic: topicId,
                session_id: agentSessionId,
                selected_agents: selectedAgents  // Send selected agents to backend
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to start debate');
        }

        $('#pauseBtn').prop('disabled', false);
        showSuccess(`${selectedAgents.length}-Agent roundtable started!`);
        console.log('Debate started with session ID:', agentSessionId);

        startMessagePolling(agentSessionId);
    } catch (error) {
        console.error('Failed to start debate:', error);
        showError('Failed to start debate: ' + error.message);
        backToTopics();
    }
}


function backToTopics() {
    // Stop current debate
    if (agentSessionId) {
        agentSocket.emit('leave_debate', { session_id: agentSessionId });
        stopMessagePolling();
    }

    // Clear state
    agentHistory = [];
    agentSessionId = null;
    agentTopic = null;
    agentPaused = false;

    // Clear chat
    $('#multiagentContainer').empty();

    // Show topic selection
    $('#chatView').hide();
    $('#topicSelectionView').show();
}

let selectedExportFormat = 'txt';

function showExportModal() {
    $('#exportModal').addClass('active');
}

function closeExportModal() {
    $('#exportModal').removeClass('active');
}

function selectExportFormat(format) {
    selectedExportFormat = format;
    $('.export-format-option').css('border-color', 'transparent');
    $(event.currentTarget).css('border-color', '#4f46e5');
}

function executeExport() {
    const includeTimestamps = $('#includeTimestamps').is(':checked');
    const includeUserMessages = $('#includeUserMessages').is(':checked');

    const data = {
        topic: $('#currentTopicDisplay').text(),
        started_at: new Date().toISOString(),
        messages: agentHistory.filter(m => includeUserMessages || m.speaker !== 'user')
    };

    let content, filename, type;

    if (selectedExportFormat === 'json') {
        content = JSON.stringify(data, null, 2);
        filename = `debate_${agentTopic}_${Date.now()}.json`;
        type = 'application/json';
    } else if (selectedExportFormat === 'pdf') {
        showError('PDF export coming soon! Use TXT or JSON for now.');
        return;
    } else {
        content = `Multi-AI Therapist Debate\nTopic: ${data.topic}\n\n`;
        data.messages.forEach(m => {
            const timestamp = includeTimestamps ? `[${new Date(m.timestamp).toLocaleTimeString()}] ` : '';
            content += `${timestamp}${m.speaker_name || 'User'}:\n${m.text}\n\n`;
        });
        filename = `debate_${agentTopic}_${Date.now()}.txt`;
        type = 'text/plain';
    }

    const blob = new Blob([content], {type});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);

    showSuccess('Transcript exported successfully!');
    closeExportModal();
}

// Topic selection functions
function selectDebateTopic(topicId, topicTitle, description, duration, category) {
    $('#topicSelectionView').hide();
    $('#chatView').show();
    $('#currentTopicDisplay').text(topicTitle);
    agentTopic = topicId;
    startDebateWithTopic(topicId, topicTitle);
}

function selectRandomTopic() {
    const topics = [
        {id: 'anxiety', title: 'Treating Anxiety'},
        {id: 'digital_therapy', title: 'Digital vs In-Person'},
        {id: 'work_life', title: 'Work-Life Balance'},
        {id: 'depression', title: 'Depression Treatment'},
        {id: 'child_psychology', title: 'Child Psychology'},
        {id: 'sleep', title: 'Sleep Disorders'}
    ];
    const random = topics[Math.floor(Math.random() * topics.length)];
    selectDebateTopic(random.id, random.title, '', '6 min', 'Random');
}

function backToTopics() {
    if (agentSessionId) {
        agentSocket.emit('leave_debate', { session_id: agentSessionId });
        stopMessagePolling();
    }
    agentHistory = [];
    agentSessionId = null;
    agentTopic = null;
    agentPaused = false;
    $('#multiagentContainer').empty();
    $('#chatView').hide();
    $('#topicSelectionView').show();
}


// Add this new variable at the top with other state variables

// Add these functions to app.js

function showAgentSelector(topicId, topicTitle, description, duration, category) {
    // Store topic info temporarily
    window.pendingTopic = { topicId, topicTitle, description, duration, category };

    // Build agent selector modal
    const modalHtml = `
        <div class="modal fade" id="agentSelectorModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content" style="border-radius: 20px;">
                    <div class="modal-header" style="background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white;">
                        <div>
                            <h5 class="modal-title">Select Therapists</h5>
                            <small>Choose 2-6 experts for: ${topicTitle}</small>
                        </div>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body p-4">
                        <p class="text-muted mb-3">
                            <i class="fas fa-info-circle"></i> Select at least 2 therapists to participate in the discussion
                        </p>
                        <div class="row g-3" id="agentCheckboxes">
                            ${Object.entries(personas).map(([key, persona]) => `
                                <div class="col-md-6">
                                    <div class="agent-selector-card ${selectedAgents.includes(key) ? 'selected' : ''}" 
                                         onclick="toggleAgentSelection('${key}')">
                                        <input type="checkbox" 
                                               id="agent_${key}" 
                                               ${selectedAgents.includes(key) ? 'checked' : ''}
                                               style="display: none;">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="agent-avatar" style="background: ${persona.color}; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">
                                                ${persona.avatar}
                                            </div>
                                            <div class="flex-grow-1">
                                                <h6 class="mb-0">${persona.name}</h6>
                                                <small class="text-muted">${persona.role}</small>
                                            </div>
                                            <i class="fas fa-check-circle" style="font-size: 1.5rem; color: ${persona.color};"></i>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        <div class="mt-3 text-center">
                            <small class="text-muted">
                                <span id="selectedCount">${selectedAgents.length}</span> of 6 therapists selected
                            </small>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="confirmAgentSelection()">
                            <i class="fas fa-check"></i> Start Discussion
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if present
    $('#agentSelectorModal').remove();

    // Add modal to page
    $('body').append(modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('agentSelectorModal'));
    modal.show();
}

// Around line 820, fix the toggleAgentSelection validation:
function toggleAgentSelection(agentKey) {
    const index = selectedAgents.indexOf(agentKey);
    const card = $(`.agent-selector-card:has(#agent_${agentKey})`);
    const checkbox = $(`#agent_${agentKey}`);

    if (index > -1) {
        if (selectedAgents.length > 2) {
            selectedAgents.splice(index, 1);
            card.removeClass('selected');
            checkbox.prop('checked', false);
        } else {
            alert('You must select at least 2 therapists');
            return; // Add return
        }
    } else {
        if (selectedAgents.length < 6) {
            selectedAgents.push(agentKey);
            card.addClass('selected');
            checkbox.prop('checked', true);
        } else {
            alert('Maximum 6 therapists allowed');
            return; // Add return
        }
    }

    $('#selectedCount').text(selectedAgents.length);
}
function confirmAgentSelection() {
    // Validate selection
    if (selectedAgents.length < 2) {
        showError('Please select at least 2 therapists');
        return;
    }

    if (selectedAgents.length > 6) {
        showError('Maximum 6 therapists allowed');
        return;
    }

    console.log('Confirmed agents:', selectedAgents);

    // Close modal
    const modalElement = document.getElementById('agentSelectorModal');
    if (modalElement) {
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        if (modalInstance) {
            modalInstance.hide();
        }
    }

    // Start debate with selected topic and agents
    if (window.pendingTopic) {
        const topic = window.pendingTopic;
        selectDebateTopic(topic.topicId, topic.topicTitle, topic.description, topic.duration, topic.category);
    } else {
        showError('No topic selected');
    }
}

// Get currently selected agents
function getSelectedAgents() {
    return selectedAgents;
}

// ==================== Auto-update ====================

setInterval(() => {
    if (!isStreaming) updateBrainState();
}, 30000);

setInterval(function() {
    if (!isStreaming) {
        const states = ['focused', 'focused', 'focused', 'relaxed', 'triggered'];
        const randomState = states[Math.floor(Math.random() * states.length)];
        const confidence = 0.7 + Math.random() * 0.3;
        $('#stateText').text(randomState.toUpperCase());
        $('#confidence').text((confidence * 100).toFixed(0) + '%');
        $('#brainState').removeClass('state-focused state-triggered state-relaxed').addClass('state-' + randomState);
    }
}, 15000);


// Make functions globally accessible
window.showAgentSelector = showAgentSelector;
window.toggleAgentSelection = toggleAgentSelection;
window.confirmAgentSelection = confirmAgentSelection;
window.getSelectedAgents = getSelectedAgents;