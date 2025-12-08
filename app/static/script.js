/**
 * İpekGPT Chat Interface - Frontend JavaScript
 */

// ============================================================================
// State Management
// ============================================================================

const state = {
    sessionId: null,
    recaptchaEnabled: false,
    recaptchaSiteKey: null,
    isLoading: false,
    messages: [],
    maxMessageLength: 300
};

// ============================================================================
// DOM Elements
// ============================================================================

const elements = {
    chatBox: document.getElementById('chatBox'),
    messageInput: document.getElementById('messageInput'),
    sendButton: document.getElementById('sendButton'),
    exitButton: document.getElementById('exitButton'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    rateLimitInfo: document.getElementById('rateLimitInfo'),
    recaptchaContainer: document.getElementById('recaptchaContainer') || null,
    charCounter: document.getElementById('charCounter')
};

// ============================================================================
// API Functions
// ============================================================================

const api = {
    baseUrl: '',

    async getConfig() {
        const response = await fetch(`${this.baseUrl}/api/config`);
        return response.json();
    },

    async createSession() {
        const response = await fetch(`${this.baseUrl}/api/session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        return response.json();
    },

    async sendMessage(sessionId, message, recaptchaToken = null) {
        const body = {
            session_id: sessionId,
            message: message
        };

        if (recaptchaToken) {
            body.recaptcha_token = recaptchaToken;
        }

        const response = await fetch(`${this.baseUrl}/ipekgpt/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.status === 429) {
            throw new Error('RATE_LIMIT_EXCEEDED');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Request failed');
        }

        return response.json();
    },

    async submitFeedback(messageId, rating) {
        const response = await fetch(`${this.baseUrl}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message_id: messageId,
                rating: rating
            })
        });
        return response.json();
    },

    async getRateLimitStatus() {
        const response = await fetch(`${this.baseUrl}/api/rate-limit`);
        return response.json();
    }
};

// ============================================================================
// UI Functions
// ============================================================================

function setLoading(isLoading) {
    state.isLoading = isLoading;
    elements.sendButton.disabled = isLoading;
    elements.messageInput.disabled = isLoading;

    if (isLoading) {
        addTypingIndicator();
    } else {
        removeTypingIndicator();
    }
}

function addTypingIndicator() {
    const existingIndicator = document.querySelector('.typing-indicator-container');
    if (existingIndicator) return;

    const indicator = document.createElement('div');
    indicator.className = 'message assistant-message typing-indicator-container';
    indicator.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    elements.chatBox.appendChild(indicator);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.querySelector('.typing-indicator-container');
    if (indicator) {
        indicator.remove();
    }
}

function addMessage(content, isUser, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;

    // Process markdown-like formatting
    const formattedContent = formatMessage(content);

    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        ${!isUser && messageId ? createFeedbackButtons(messageId) : ''}
    `;

    elements.chatBox.appendChild(messageDiv);
    scrollToBottom();

    // Add event listeners to feedback buttons
    if (!isUser && messageId) {
        const feedbackBtns = messageDiv.querySelectorAll('.feedback-btn');
        feedbackBtns.forEach(btn => {
            btn.addEventListener('click', handleFeedbackClick);
        });
    }

    return messageDiv;
}

function formatMessage(content) {
    // Trim and normalize
    let text = content.trim().replace(/\r\n/g, '\n');

    // Split into lines
    const lines = text.split('\n');
    let html = '';
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

        // Skip empty lines
        if (line.trim() === '') {
            if (inList) {
                html += '</ul>';
                inList = false;
            }
            continue;
        }

        // Headers
        if (line.match(/^### /)) {
            if (inList) { html += '</ul>'; inList = false; }
            html += '<h4>' + formatInline(line.slice(4)) + '</h4>';
            continue;
        }
        if (line.match(/^## /)) {
            if (inList) { html += '</ul>'; inList = false; }
            html += '<h3>' + formatInline(line.slice(3)) + '</h3>';
            continue;
        }
        if (line.match(/^# /)) {
            if (inList) { html += '</ul>'; inList = false; }
            html += '<h2>' + formatInline(line.slice(2)) + '</h2>';
            continue;
        }

        // List items
        const bulletMatch = line.match(/^[\s]*[-•*]\s+(.*)$/);
        const numberedMatch = line.match(/^[\s]*\d+\.\s+(.*)$/);

        if (bulletMatch || numberedMatch) {
            if (!inList) {
                html += '<ul>';
                inList = true;
            }
            const itemContent = bulletMatch ? bulletMatch[1] : numberedMatch[1];
            html += '<li>' + formatInline(itemContent) + '</li>';
            continue;
        }

        // Regular text
        if (inList) {
            html += '</ul>';
            inList = false;
        }
        html += '<p>' + formatInline(line) + '</p>';
    }

    // Close any open list
    if (inList) {
        html += '</ul>';
    }

    return html;
}

function formatInline(text) {
    return text
        // Bold: **text** or __text__
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        // Italic: *text* or _text_
        .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
        .replace(/_([^_]+)_/g, '<em>$1</em>')
        // URLs
        .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

function createFeedbackButtons(messageId) {
    return `
        <div class="feedback-container">
            <button class="feedback-btn positive" data-message-id="${messageId}" data-rating="1" title="Yararlı">
                👍
            </button>
            <button class="feedback-btn negative" data-message-id="${messageId}" data-rating="-1" title="Yararlı değil">
                👎
            </button>
        </div>
    `;
}

async function handleFeedbackClick(event) {
    const btn = event.currentTarget;
    const messageId = parseInt(btn.dataset.messageId);
    const rating = parseInt(btn.dataset.rating);
    const container = btn.closest('.feedback-container');

    // Remove active state from all buttons in this container
    container.querySelectorAll('.feedback-btn').forEach(b => b.classList.remove('active'));

    // Add active state to clicked button
    btn.classList.add('active');

    try {
        await api.submitFeedback(messageId, rating);
    } catch (error) {
        console.error('Failed to submit feedback:', error);
    }
}

function addErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message assistant-message';
    errorDiv.innerHTML = '<div class="error-message">' + message + '</div>';
    elements.chatBox.appendChild(errorDiv);
    scrollToBottom();
}

function scrollToBottom() {
    setTimeout(() => {
        elements.chatBox.scrollTo({
            top: elements.chatBox.scrollHeight,
            behavior: 'smooth'
        });
    }, 100);
}

function updateRateLimitInfo(remaining) {
    if (remaining !== undefined) {
        elements.rateLimitInfo.textContent = 'Günlük kalan istek: ' + remaining;
    }
}

// ============================================================================
// reCAPTCHA Functions
// ============================================================================

function loadRecaptcha(siteKey) {
    if (!siteKey) return;

    const script = document.createElement('script');
    script.src = 'https://www.google.com/recaptcha/api.js?render=' + siteKey;
    script.async = true;
    script.defer = true;
    document.head.appendChild(script);

    state.recaptchaSiteKey = siteKey;
}

async function getRecaptchaToken() {
    if (!state.recaptchaEnabled || !state.recaptchaSiteKey) {
        return null;
    }

    try {
        return await grecaptcha.execute(state.recaptchaSiteKey, { action: 'chat' });
    } catch (error) {
        console.error('reCAPTCHA error:', error);
        return null;
    }
}

// ============================================================================
// Message Handling
// ============================================================================

async function sendMessage() {
    const message = elements.messageInput.value.trim();

    if (!message || state.isLoading) return;

    // Clear input and reset counter
    elements.messageInput.value = '';
    autoResizeTextarea();
    updateCharCounter();

    // Add user message to chat
    addMessage(message, true);

    setLoading(true);

    try {
        const recaptchaToken = await getRecaptchaToken();
        const response = await api.sendMessage(state.sessionId, message, recaptchaToken);
        addMessage(response.response, false, response.message_id);

        const rateLimitStatus = await api.getRateLimitStatus();
        updateRateLimitInfo(rateLimitStatus.remaining);

    } catch (error) {
        console.error('Error sending message:', error);

        if (error.message === 'RATE_LIMIT_EXCEEDED') {
            addErrorMessage('Günlük istek limitine ulaşıldı. Lütfen yarın tekrar deneyin.');
        } else {
            addErrorMessage('Bir hata oluştu: ' + error.message);
        }
    } finally {
        setLoading(false);
    }
}

// ============================================================================
// Textarea Auto-resize
// ============================================================================

function autoResizeTextarea() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

function updateCharCounter() {
    // Ensure we have the charCounter element
    if (!elements.charCounter) {
        elements.charCounter = document.getElementById('charCounter');
    }
    if (!elements.charCounter) return;

    const currentLength = elements.messageInput.value.length;
    const maxLength = state.maxMessageLength;

    elements.charCounter.textContent = currentLength + ' / ' + maxLength;

    elements.charCounter.classList.remove('warning', 'limit');

    if (currentLength >= maxLength) {
        elements.charCounter.classList.add('limit');
    } else if (currentLength >= maxLength * 0.8) {
        elements.charCounter.classList.add('warning');
    }
}

// ============================================================================
// Event Listeners
// ============================================================================

function setupEventListeners() {
    elements.sendButton.addEventListener('click', sendMessage);

    elements.exitButton.addEventListener('click', () => {
        window.location.href = 'https://ipekyolugkm.com/';
    });

    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    elements.messageInput.addEventListener('input', () => {
        autoResizeTextarea();
        updateCharCounter();
    });

    updateCharCounter();
}

async function init() {
    console.log('Initializing IpekGPT...');

    try {
        const config = await api.getConfig();
        state.recaptchaEnabled = config.recaptcha_enabled;
        state.maxMessageLength = config.max_message_length || 400;

        elements.messageInput.setAttribute('maxlength', state.maxMessageLength);

        if (state.recaptchaEnabled && config.recaptcha_site_key) {
            loadRecaptcha(config.recaptcha_site_key);
        }

        const session = await api.createSession();
        state.sessionId = session.session_id;
        console.log('Session created:', state.sessionId);

        const rateLimitStatus = await api.getRateLimitStatus();
        updateRateLimitInfo(rateLimitStatus.remaining);

        setupEventListeners();
        elements.messageInput.focus();

        console.log('IpekGPT initialized successfully!');

    } catch (error) {
        console.error('Initialization error:', error);
        addErrorMessage('Sistem başlatılırken bir hata oluştu. Lütfen sayfayı yenileyin.');
    }
}

document.addEventListener('DOMContentLoaded', init);
