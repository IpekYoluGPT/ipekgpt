/**
 * İpekGPT Chat Interface - Enhanced Frontend JavaScript
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
    maxMessageLength: 300,
    isOnline: navigator.onLine,
    darkMode: localStorage.getItem('darkMode') === 'true'
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
    charCounter: document.getElementById('charCounter'),
    newChatBtn: document.getElementById('newChatBtn'),
    darkModeBtn: document.getElementById('darkModeBtn'),
    offlineBanner: document.getElementById('offlineBanner'),
    suggestedQuestions: document.getElementById('suggestedQuestions')
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
// Theme Management
// ============================================================================

function initTheme() {
    if (state.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

function toggleDarkMode() {
    state.darkMode = !state.darkMode;
    localStorage.setItem('darkMode', state.darkMode);

    if (state.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
}

// ============================================================================
// Offline Detection
// ============================================================================

function updateOnlineStatus() {
    state.isOnline = navigator.onLine;

    if (state.isOnline) {
        elements.offlineBanner.classList.remove('active');
        document.body.classList.remove('offline');
    } else {
        elements.offlineBanner.classList.add('active');
        document.body.classList.add('offline');
    }
}

// ============================================================================
// Time Formatting
// ============================================================================

function formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

function getCurrentTime() {
    return formatTime(new Date());
}

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
        <div class="message-avatar">
            <img src="/static/logo.png" alt="İpekGPT">
        </div>
        <div class="message-body">
            <div class="typing-indicator">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span class="typing-text">İpekGPT yazıyor...</span>
            </div>
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

function addMessage(content, isUser, messageId = null, streaming = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;

    const timestamp = getCurrentTime();
    const formattedContent = formatMessage(content);
    const avatarHtml = isUser
        ? `<div class="message-avatar">
               <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                   <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2"/>
                   <path d="M4 20C4 16.6863 7.58172 14 12 14C16.4183 14 20 16.6863 20 20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
               </svg>
           </div>`
        : `<div class="message-avatar">
               <img src="/static/logo.png" alt="İpekGPT">
           </div>`;

    const copyButtonHtml = !isUser ? `
        <button class="copy-btn" title="Kopyala" data-content="${escapeHtml(content)}">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="2"/>
                <path d="M5 15H4C2.89543 15 2 14.1046 2 13V4C2 2.89543 2.89543 2 4 2H13C14.1046 2 15 2.89543 15 4V5" stroke="currentColor" stroke-width="2"/>
            </svg>
        </button>
    ` : '';

    messageDiv.innerHTML = `
        ${avatarHtml}
        <div class="message-body">
            <div class="message-content${streaming ? ' streaming-cursor' : ''}">
                ${formattedContent}
                ${copyButtonHtml}
            </div>
            ${!isUser && messageId ? createFeedbackButtons(messageId) : ''}
            <span class="message-time">${timestamp}</span>
        </div>
    `;

    elements.chatBox.appendChild(messageDiv);
    scrollToBottom();

    // Add event listeners
    if (!isUser && messageId) {
        const feedbackBtns = messageDiv.querySelectorAll('.feedback-btn');
        feedbackBtns.forEach(btn => {
            btn.addEventListener('click', handleFeedbackClick);
        });
    }

    // Add copy button listener
    const copyBtn = messageDiv.querySelector('.copy-btn');
    if (copyBtn) {
        copyBtn.addEventListener('click', handleCopyClick);
    }

    return messageDiv;
}

// Streaming message effect with live formatting
async function addStreamingMessage(content, messageId = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';

    const timestamp = getCurrentTime();

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <img src="/static/logo.png" alt="İpekGPT">
        </div>
        <div class="message-body">
            <div class="message-content streaming-cursor">
            </div>
            <span class="message-time">${timestamp}</span>
        </div>
    `;

    elements.chatBox.appendChild(messageDiv);

    const contentEl = messageDiv.querySelector('.message-content');

    // Stream the content character by character with live formatting
    let displayedText = '';
    let index = 0;
    const streamSpeed = 12; // ms per character
    const formatUpdateInterval = 3; // Update formatting every N characters

    await new Promise(resolve => {
        const streamInterval = setInterval(() => {
            if (index < content.length) {
                displayedText += content[index];
                index++;

                // Update formatted content periodically for smoother performance
                if (index % formatUpdateInterval === 0 || index === content.length) {
                    contentEl.innerHTML = formatMessage(displayedText);
                }
                scrollToBottom();
            } else {
                clearInterval(streamInterval);
                resolve();
            }
        }, streamSpeed);
    });

    // After streaming complete, finalize content with copy button
    contentEl.classList.remove('streaming-cursor');
    contentEl.innerHTML = formatMessage(content) + `
        <button class="copy-btn" title="Kopyala" data-content="${escapeHtml(content)}">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" stroke-width="2"/>
                <path d="M5 15H4C2.89543 15 2 14.1046 2 13V4C2 2.89543 2.89543 2 4 2H13C14.1046 2 15 2.89543 15 4V5" stroke="currentColor" stroke-width="2"/>
            </svg>
        </button>
    `;

    // Add feedback buttons if messageId exists
    if (messageId) {
        const messageBody = messageDiv.querySelector('.message-body');
        const timeSpan = messageBody.querySelector('.message-time');
        const feedbackDiv = document.createElement('div');
        feedbackDiv.innerHTML = createFeedbackButtons(messageId);
        messageBody.insertBefore(feedbackDiv.firstElementChild, timeSpan);

        const feedbackBtns = messageDiv.querySelectorAll('.feedback-btn');
        feedbackBtns.forEach(btn => {
            btn.addEventListener('click', handleFeedbackClick);
        });
    }

    // Re-attach copy listener
    const newCopyBtn = messageDiv.querySelector('.copy-btn');
    if (newCopyBtn) {
        newCopyBtn.addEventListener('click', handleCopyClick);
    }

    return messageDiv;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/"/g, '&quot;');
}

async function handleCopyClick(event) {
    const btn = event.currentTarget;
    const content = btn.dataset.content;

    try {
        await navigator.clipboard.writeText(content);
        btn.classList.add('copied');

        // Show checkmark briefly
        const originalSvg = btn.innerHTML;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 6L9 17L4 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;

        setTimeout(() => {
            btn.innerHTML = originalSvg;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

function formatMessage(content) {
    let text = content.trim().replace(/\r\n/g, '\n');
    const lines = text.split('\n');
    let html = '';
    let inList = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

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

    if (inList) {
        html += '</ul>';
    }

    return html;
}

function formatInline(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        .replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
        .replace(/_([^_]+)_/g, '<em>$1</em>')
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

    container.querySelectorAll('.feedback-btn').forEach(b => b.classList.remove('active'));
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
    errorDiv.innerHTML = `
        <div class="message-avatar">
            <img src="/static/logo.png" alt="İpekGPT">
        </div>
        <div class="message-body">
            <div class="error-message">${message}</div>
            <span class="message-time">${getCurrentTime()}</span>
        </div>
    `;
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

function hideSuggestedQuestions() {
    if (elements.suggestedQuestions) {
        elements.suggestedQuestions.classList.add('hidden');
    }
}

// ============================================================================
// New Chat Function
// ============================================================================

async function startNewChat() {
    // Clear chat box except welcome message
    const messages = elements.chatBox.querySelectorAll('.message:not(:first-child), .suggested-questions');
    messages.forEach(msg => msg.remove());

    // Re-add suggested questions
    const suggestionsHtml = `
        <div class="suggested-questions" id="suggestedQuestions">
            <button class="suggestion-btn" data-question="İpek Yolu hakkında bilgi verir misin?">
                🏛️ İpek Yolu hakkında bilgi ver
            </button>
            <button class="suggestion-btn" data-question="Hangi programlar düzenleniyor?">
                📚 Programlar nelerdir?
            </button>
            <button class="suggestion-btn" data-question="Eğitimlere nasıl başvurabilirim?">
                ✍️ Başvuru nasıl yapılır?
            </button>
            <button class="suggestion-btn" data-question="Merkez nerede bulunuyor?">
                📍 Merkez nerede?
            </button>
        </div>
    `;
    elements.chatBox.insertAdjacentHTML('beforeend', suggestionsHtml);
    elements.suggestedQuestions = document.getElementById('suggestedQuestions');
    setupSuggestionListeners();

    // Create new session
    try {
        const session = await api.createSession();
        state.sessionId = session.session_id;
        state.messages = [];
        console.log('New session created:', state.sessionId);
    } catch (error) {
        console.error('Failed to create new session:', error);
    }

    elements.messageInput.focus();
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

async function sendMessage(messageText = null) {
    const message = messageText || elements.messageInput.value.trim();

    if (!message || state.isLoading) return;

    // Check if online
    if (!state.isOnline) {
        addErrorMessage('Bağlantı yok. Lütfen internet bağlantınızı kontrol edin.');
        return;
    }

    // Clear input and reset counter
    elements.messageInput.value = '';
    autoResizeTextarea();
    updateCharCounter();

    // Hide suggested questions on first message
    hideSuggestedQuestions();

    // Add user message to chat
    addMessage(message, true);

    setLoading(true);

    try {
        const recaptchaToken = await getRecaptchaToken();
        const response = await api.sendMessage(state.sessionId, message, recaptchaToken);

        // Use streaming for the response
        await addStreamingMessage(response.response, response.message_id);

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
        elements.messageInput.focus();
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

function setupSuggestionListeners() {
    const suggestionBtns = document.querySelectorAll('.suggestion-btn');
    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const question = btn.dataset.question;
            sendMessage(question);
        });
    });
}

function setupEventListeners() {
    elements.sendButton.addEventListener('click', () => sendMessage());

    elements.exitButton.addEventListener('click', () => {
        window.location.href = 'https://ipekyolugkm.com.tr/';
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

    // New Chat button
    elements.newChatBtn.addEventListener('click', startNewChat);

    // Dark Mode toggle
    elements.darkModeBtn.addEventListener('click', toggleDarkMode);

    // Suggested Questions
    setupSuggestionListeners();

    // Online/Offline events
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);

    // Sayfa tıklamalarında input'a focus'u koru
    document.addEventListener('click', (e) => {
        // Butonlara veya özel elementlere tıklanmadıysa input'a odaklan
        const isButton = e.target.closest('button');
        const isLink = e.target.closest('a');
        const isInput = e.target.closest('input, textarea');
        
        if (!isButton && !isLink && !isInput && !state.isLoading) {
            elements.messageInput.focus();
        }
    });

    updateCharCounter();
}

async function init() {
    console.log('Initializing IpekGPT...');

    // Initialize theme
    initTheme();

    // Check online status
    updateOnlineStatus();

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
