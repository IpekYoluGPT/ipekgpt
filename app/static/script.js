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
    maxMessageLength: 400
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
    recaptchaContainer: document.getElementById('recaptchaContainer'),
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
        // Loading overlay disabled - user requested removal
        // elements.loadingOverlay.classList.add('active');
        addTypingIndicator();
    } else {
        // elements.loadingOverlay.classList.remove('active');
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
    // Convert markdown-like formatting to HTML
    let formatted = content
        // Headers: ### h3, ## h2, # h1 (must be at start of line)
        .replace(/^### (.*)$/gm, '<h4>$1</h4>')
        .replace(/^## (.*)$/gm, '<h3>$1</h3>')
        .replace(/^# (.*)$/gm, '<h2>$1</h2>')
        // Bold: **text** or __text__
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        // Italic: *text* or _text_
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/_([^_]+)_/g, '<em>$1</em>')
        // URLs: Convert to clickable links
        .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>')
        // Bullet points
        .replace(/^[\s]*[-•*]\s+(.*)$/gm, '<li>$1</li>')
        // Numbered lists
        .replace(/^[\s]*(\d+)\.\s+(.*)$/gm, '<li>$2</li>')
        // Line breaks (but not after headers)
        .replace(/<\/h[234]>\n/g, '</h4>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap in paragraphs (but not headers)
    formatted = `<p>${formatted}</p>`;

    // Clean up empty paragraphs around headers
    formatted = formatted.replace(/<p>(<h[234]>)/g, '$1');
    formatted = formatted.replace(/(<\/h[234]>)<\/p>/g, '$1');
    formatted = formatted.replace(/<p><\/p>/g, '');

    // Wrap list items in ul
    formatted = formatted.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');

    return formatted;
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
    errorDiv.innerHTML = `<div class="error-message">${message}</div>`;
    elements.chatBox.appendChild(errorDiv);
    scrollToBottom();
}

function scrollToBottom() {
    elements.chatBox.scrollTo({
        top: elements.chatBox.scrollHeight,
        behavior: 'smooth'
    });
}

function updateRateLimitInfo(remaining) {
    if (remaining !== undefined) {
        elements.rateLimitInfo.textContent = `Günlük kalan istek: ${remaining}`;
    }
}

// ============================================================================
// reCAPTCHA Functions
// ============================================================================

function loadRecaptcha(siteKey) {
    if (!siteKey) return;

    // Create script element
    const script = document.createElement('script');
    script.src = `https://www.google.com/recaptcha/api.js?render=${siteKey}`;
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

    // Clear input
    elements.messageInput.value = '';
    autoResizeTextarea();

    // Add user message to chat
    addMessage(message, true);

    setLoading(true);

    try {
        // Get reCAPTCHA token if enabled
        const recaptchaToken = await getRecaptchaToken();

        // Send message to API
        const response = await api.sendMessage(state.sessionId, message, recaptchaToken);

        // Add assistant response
        addMessage(response.response, false, response.message_id);

        // Update rate limit info
        const rateLimitStatus = await api.getRateLimitStatus();
        updateRateLimitInfo(rateLimitStatus.remaining);

    } catch (error) {
        console.error('Error sending message:', error);

        if (error.message === 'RATE_LIMIT_EXCEEDED') {
            addErrorMessage('Günlük istek limitine ulaşıldı. Lütfen yarın tekrar deneyin.');
        } else {
            addErrorMessage(`Bir hata oluştu: ${error.message}`);
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
    const currentLength = elements.messageInput.value.length;
    const maxLength = state.maxMessageLength;

    elements.charCounter.textContent = `${currentLength} / ${maxLength}`;

    // Remove all classes first
    elements.charCounter.classList.remove('warning', 'limit');

    // Add appropriate class based on character count
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
    // Send button click
    elements.sendButton.addEventListener('click', sendMessage);

    // Exit button click - reload page to start new session
    elements.exitButton.addEventListener('click', () => {
        if (confirm('Oturumdan çıkmak istediğinize emin misiniz?')) {
            window.location.reload();
        }
    });

    // Enter key to send (Shift+Enter for new line)
    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea and update character counter
    elements.messageInput.addEventListener('input', () => {
        autoResizeTextarea();
        updateCharCounter();
    });

    // Initialize character counter
    updateCharCounter();
}

async function init() {
    console.log('🚀 Initializing İpekGPT...');

    try {
        // Get configuration
        const config = await api.getConfig();
        state.recaptchaEnabled = config.recaptcha_enabled;
        state.maxMessageLength = config.max_message_length || 400;

        // Update textarea maxlength
        elements.messageInput.setAttribute('maxlength', state.maxMessageLength);

        // Load reCAPTCHA if enabled
        if (state.recaptchaEnabled && config.recaptcha_site_key) {
            loadRecaptcha(config.recaptcha_site_key);
        }

        // Create session
        const session = await api.createSession();
        state.sessionId = session.session_id;
        console.log('✅ Session created:', state.sessionId);

        // Get rate limit status
        const rateLimitStatus = await api.getRateLimitStatus();
        updateRateLimitInfo(rateLimitStatus.remaining);

        // Setup event listeners
        setupEventListeners();

        // Focus on input
        elements.messageInput.focus();

        console.log('✅ İpekGPT initialized successfully!');

    } catch (error) {
        console.error('❌ Initialization error:', error);
        addErrorMessage('Sistem başlatılırken bir hata oluştu. Lütfen sayfayı yenileyin.');
    }
}

// Start initialization when DOM is ready
document.addEventListener('DOMContentLoaded', init);
