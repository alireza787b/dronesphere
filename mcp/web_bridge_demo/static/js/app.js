// DroneSphere Pro - Enhanced JavaScript Application

// Global variables
let telemetryInterval = null;
let isConnected = false;
// == Telemetry polling ==========================================
const TELEMETRY_POLL_MS      = 3_000;   // 2 s
const TELEMETRY_GRACE_FAILS = 6;       // how many misses before "Disconnected"
let missedTelemetry          = 3;      // consecutive failures

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DroneSphere Pro initializing...');

    // Initialize theme
    initializeTheme();

    // Initialize chat
    initializeChat();

    // Start telemetry updates
    startTelemetryUpdates();

    // Set welcome time
    document.getElementById('welcomeTime').textContent = new Date().toLocaleTimeString();

    // Show welcome toast after a short delay
    setTimeout(() => {
        showToast('🚁 DroneSphere Pro Ready! Connecting to drone systems...', 'success');
    }, 1000);
});

// Theme Management
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
    updateThemeIcon();
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon();
    showToast(`Theme changed to ${newTheme} mode`, 'success');
}

function updateThemeIcon() {
    const theme = document.body.getAttribute('data-theme');
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Chat Functionality
function initializeChat() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');

    // Add event listeners
    chatInput.addEventListener('keydown', handleKeyPress);
    chatInput.addEventListener('input', autoResize);
    sendButton.addEventListener('click', sendMessage);

    // Focus on input
    chatInput.focus();
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(event) {
    const textarea = event.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function setCommand(command) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = command;
        chatInput.focus();
        // Trigger resize
        chatInput.dispatchEvent(new Event('input'));
    }
}

async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const message = chatInput.value.trim();

    if (!message) return;

    console.log('Sending message:', message);

    // Add user message
    addMessage(message, 'user');

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Disable send button and show loading
    sendButton.disabled = true;
    sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    addTypingIndicator();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, target_drone: 1 })
        });

        const result = await response.json();
        console.log('Chat response:', result);

        removeTypingIndicator();

        // Add assistant response with personality
        const personalizedMessage = personalizeResponse(result.message);
        addMessage(personalizedMessage, 'assistant', result.success);

        // Update telemetry if available
        if (result.telemetry) {
            updateTelemetry(result.telemetry);
        }

        // Show toast notification
        if (result.success) {
            if (result.message.includes('executed successfully')) {
                showToast('✅ Command executed successfully!', 'success');
            }
        } else if (result.blocked_for_safety) {
            showToast('⚠️ Safety first! Command blocked for your protection', 'error');
        }

    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator();
        addMessage('😕 Oops! Connection lost. Please check if the drone system is running.', 'assistant', false);
        showToast('Connection error - Check system status', 'error');
    } finally {
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
    }
}

function personalizeResponse(message) {
    // Add friendly touches to make responses feel more natural
    const greetings = ['Great!', 'Excellent!', 'Perfect!', 'Got it!', 'Roger that!'];
    const randomGreeting = greetings[Math.floor(Math.random() * greetings.length)];

    // Add personality based on content
    if (message.includes('✅') && message.includes('executed')) {
        return `${randomGreeting} ${message}`;
    }

    return message;
}

function addMessage(content, type, success = true) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + type;

    // Convert markdown-style formatting
    content = formatMessage(content);

    messageDiv.innerHTML = `
        <div class="message-bubble">
            <div class="message-content">${content}</div>
        </div>
        <div class="message-time">
            <i class="far fa-clock"></i>
            <span>${new Date().toLocaleTimeString()}</span>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessage(content) {
    // Basic markdown formatting
    content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/\n/g, '<br>');

    // Convert bullet points to proper lists
    const lines = content.split('<br>');
    let inList = false;
    let formattedLines = [];

    lines.forEach(line => {
        if (line.trim().startsWith('•')) {
            if (!inList) {
                formattedLines.push('<ul>');
                inList = true;
            }
            formattedLines.push('<li>' + line.trim().substring(1).trim() + '</li>');
        } else {
            if (inList && line.trim() === '') {
                formattedLines.push('</ul>');
                inList = false;
            }
            formattedLines.push(line);
        }
    });

    if (inList) {
        formattedLines.push('</ul>');
    }

    content = formattedLines.join('<br>').replace(/<br><ul>/g, '<ul>').replace(/<\/ul><br>/g, '</ul>');

    // Add safety indicators with emojis
    if (content.includes('SAFETY CHECK') && content.includes('✅')) {
        content += '<div class="safety-indicator safe"><i class="fas fa-check-circle"></i> All Systems Go!</div>';
    } else if (content.includes('SAFETY ALERT') || content.includes('🚨')) {
        content += '<div class="safety-indicator warning"><i class="fas fa-exclamation-triangle"></i> Safety Protocol Activated</div>';
    }

    return content;
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant typing';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-bubble">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function startTelemetryUpdates() {
  fetchTelemetry();                                  // first hit ASAP
  telemetryInterval = setInterval(fetchTelemetry, TELEMETRY_POLL_MS);
}

async function fetchTelemetry() {
  // --- (optional) give each request a 1.5 s timeout ---------------
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), 3_500);

  try {
    const res = await fetch('/api/drone-telemetry', { signal: controller.signal });
    clearTimeout(t);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const telem = await res.json();
    if (telem.error) throw new Error(telem.error);

    // ----------------------- SUCCESS ------------------------------
    missedTelemetry = 0;                 // reset grace counter
    if (!isConnected) setConnectionStatus(true);
    updateTelemetry(telem);
  } catch (err) {
    clearTimeout(t);
    console.error('Telemetry fetch failed', err);

    // ----------------------- FAILURE ------------------------------
    missedTelemetry += 1;
    if (missedTelemetry >= TELEMETRY_GRACE_FAILS && isConnected) {
      setConnectionStatus(false);        // only after N consecutive misses
    }
  }
}

function updateTelemetry(telemetry) {
    console.log('Updating telemetry:', telemetry);

    // Battery with color coding
    const battery = telemetry.battery?.remaining_percent;
    if (battery !== undefined && !isNaN(battery)) {
        const batteryValue = document.getElementById('batteryValue');
        const batteryProgress = document.getElementById('batteryProgress');

        batteryValue.textContent = Math.round(battery);
        batteryProgress.style.width = battery + '%';

        // Dynamic color based on battery level
        if (battery < 20) {
            batteryProgress.className = 'progress-fill warning';
            batteryValue.style.color = '#ef4444';
        } else if (battery < 50) {
            batteryProgress.style.background = 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)';
            batteryValue.style.color = '#f59e0b';
        } else {
            batteryProgress.className = 'progress-fill';
            batteryValue.style.color = '#10b981';
        }
    }

    // Position with animation
    const position = telemetry.position;
    if (position) {
        if (position.latitude !== undefined && !isNaN(position.latitude)) {
            animateValue('latValue', position.latitude.toFixed(6));
        }
        if (position.longitude !== undefined && !isNaN(position.longitude)) {
            animateValue('lonValue', position.longitude.toFixed(6));
        }
        if (position.altitude !== undefined && !isNaN(position.altitude)) {
            animateValue('altitudeValue', position.altitude.toFixed(1));
        }

        // Update relative altitude with visual feedback
        const relAlt = position.relative_altitude;
        if (relAlt !== undefined && !isNaN(relAlt)) {
            const droneIcon = document.getElementById('droneIcon');
            const normalizedAlt = Math.min(relAlt / 50, 1);
            droneIcon.style.bottom = (10 + normalizedAlt * 80) + '%';
            droneIcon.style.transform = `translateX(-50%) scale(${1 + normalizedAlt * 0.2})`;
        }
    }

    // Voltage with warning
    const voltage = telemetry.battery?.voltage;
    if (voltage !== undefined && !isNaN(voltage)) {
        const voltageValue = document.getElementById('voltageValue');
        voltageValue.textContent = voltage.toFixed(1);

        // Voltage warning (assuming 4S battery)
        if (voltage < 14.0) {
            voltageValue.style.color = '#ef4444';
        } else if (voltage < 15.0) {
            voltageValue.style.color = '#f59e0b';
        } else {
            voltageValue.style.color = '#10b981';
        }
    }

    // Flight Mode with status
    if (telemetry.flight_mode) {
        const flightModeValue = document.getElementById('flightModeValue');
        flightModeValue.textContent = telemetry.flight_mode;

        // Update status badges based on telemetry
        updateStatusBadges(telemetry);
    }
}

function animateValue(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (element && element.textContent !== newValue) {
        element.style.transition = 'color 0.3s ease';
        element.style.color = '#6366f1';
        element.textContent = newValue;
        setTimeout(() => {
            element.style.color = '';
        }, 300);
    }
}

function setConnectionStatus(connected) {
    const wasConnected = isConnected;
    isConnected = connected;

    const connectionStatus = document.getElementById('connectionStatus');
    const telemetryStatus = document.getElementById('telemetryStatus');

    if (connected) {
        connectionStatus.classList.add('active');
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> <span>Connected</span>';

        telemetryStatus.classList.add('active');
        telemetryStatus.innerHTML = '<i class="fas fa-satellite-dish"></i> <span>Live Data</span>';

        // Show connection restored message only if previously disconnected
        if (!wasConnected && wasConnected !== null) {
            showToast('✅ Connection restored!', 'success');
        }
    } else {
        connectionStatus.classList.remove('active');
        connectionStatus.classList.add('warning');
        connectionStatus.innerHTML = '<i class="fas fa-exclamation-circle"></i> <span>Disconnected</span>';

        telemetryStatus.classList.remove('active');
        telemetryStatus.classList.add('warning');
        telemetryStatus.innerHTML = '<i class="fas fa-satellite-dish"></i> <span>No Signal</span>';

        // Reset telemetry values
        document.getElementById('batteryValue').textContent = '--';
        document.getElementById('altitudeValue').textContent = '--';
        document.getElementById('latValue').textContent = '--';
        document.getElementById('lonValue').textContent = '--';
        document.getElementById('voltageValue').textContent = '--';
        document.getElementById('flightModeValue').textContent = '--';

        // Only show disconnection message if previously connected
        if (wasConnected) {
            showToast('⚠️ Connection lost - Attempting to reconnect...', 'error');
        }
    }
}

function updateStatusBadges(telemetry) {
    const safetyStatus = document.getElementById('safetyStatus');

    // Update safety status based on battery
    const battery = telemetry.battery?.remaining_percent;
    if (battery < 20) {
        safetyStatus.classList.remove('active');
        safetyStatus.classList.add('warning');
        safetyStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> <span>Low Battery</span>';
    } else {
        safetyStatus.classList.remove('warning');
        safetyStatus.classList.add('active');
        safetyStatus.innerHTML = '<i class="fas fa-shield-alt"></i> <span>Safety Active</span>';
    }
}

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${type === 'success' ? 'fa-check' : 'fa-exclamation'}"></i>
        </div>
        <div>${message}</div>
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideUp 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Export functions for global access (needed for onclick handlers)
window.toggleTheme = toggleTheme;
window.setCommand = setCommand;
window.sendMessage = sendMessage;
