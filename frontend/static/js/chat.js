// RocBot Chat Interface - JavaScript

const API_URL = 'http://localhost:8000';

// State
let isWaitingForResponse = false;
let messageCount = 0;
let conversationId = 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('RocBot initialized! 🌸');
    console.log('Conversation ID:', conversationId);
    focusInput();
});

// Handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSend();
    }
}

// Handle send button click
function handleSend() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    
    if (!message || isWaitingForResponse) {
        return;
    }
    
    sendMessage(message);
    input.value = '';
}

// Send message to API with streaming
async function sendMessage(message) {
    if (isWaitingForResponse) return;
    
    messageCount++;
    if (messageCount === 1) {
        hideWelcomeMessage();
        hideSuggestions();
    }
    
    addUserMessage(message);
    showTypingIndicator();
    
    isWaitingForResponse = true;
    disableInput();
    
    try {
        await streamChatResponse(message);
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        addBotMessage("Oops! I'm having trouble connecting right now. Please make sure the API server is running on port 8000. 🤖", []);
    } finally {
        isWaitingForResponse = false;
        enableInput();
        focusInput();
    }
}

// Stream chat response using Fetch API with a reader
async function streamChatResponse(message) {
    const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message: message,
            conversation_id: conversationId,
            max_sources: 5
        })
    });
    
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    
    hideTypingIndicator();
    
    const chatFeed = document.getElementById('chatFeed');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'bot-message';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = '';
    messageDiv.appendChild(bubble);
    chatFeed.appendChild(messageDiv);
    
    let sources = [];
    let fullAnswer = '';
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.type === 'sources') {
                        sources = data.data;
                    } else if (data.type === 'token') {
                        fullAnswer += data.data;
                        bubble.innerHTML = formatText(fullAnswer);
                        scrollToBottom();
                    } else if (data.type === 'done') {
                        addSourcesToMessage(messageDiv, sources);
                        scrollToBottom();
                    } else if (data.type === 'complete') {
                        console.log('Streaming complete');
                    }
                } catch (e) {
                    // console.log('Non-JSON line:', line);
                }
            }
        }
    }
}

// Format text (handles markdown-like bolding and new lines)
function formatText(text) {
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
}

function addSourcesToMessage(messageDiv, sources) {
    const relevantSources = sources.slice(0, 3);
    if (relevantSources.length > 0) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';
        relevantSources.forEach(source => {
            const sourceLink = document.createElement('a');
            sourceLink.className = 'source-link';
            sourceLink.href = source.url;
            sourceLink.target = '_blank';
            sourceLink.rel = 'noopener noreferrer';
            
            const icon = document.createElement('span');
            icon.className = 'source-icon';
            icon.textContent = getSourceIcon(source.source);
            
            const text = document.createElement('span');
            text.textContent = source.title;
            
            sourceLink.appendChild(icon);
            sourceLink.appendChild(text);
            sourcesDiv.appendChild(sourceLink);
        });
        messageDiv.appendChild(sourcesDiv);
    }
}

function sendSuggestion(button) {
    const message = button.textContent;
    sendMessage(message);
}

function addUserMessage(message) {
    const chatFeed = document.getElementById('chatFeed');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'user-message';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = message;
    messageDiv.appendChild(bubble);
    chatFeed.appendChild(messageDiv);
    scrollToBottom();
}

function addBotMessage(answer, sources = []) {
    const chatFeed = document.getElementById('chatFeed');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'bot-message';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = formatText(answer);
    messageDiv.appendChild(bubble);
    if (sources && sources.length > 0) {
        addSourcesToMessage(messageDiv, sources);
    }
    chatFeed.appendChild(messageDiv);
    scrollToBottom();
}

function getSourceIcon(source) {
    const icons = {'cityofrochester': '🏛️', 'eventbrite': '🎉', 'meetup': '👥'};
    return icons[source] || '🌐';
}

function showTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'block';
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'none';
}

function hideWelcomeMessage() {
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) welcome.style.display = 'none';
}

function hideSuggestions() {
    const suggestions = document.getElementById('suggestions');
    if (suggestions) suggestions.classList.add('hidden');
}

function toggleQuickActions() {
    const quickActions = document.getElementById('quickActions');
    const suggestions = document.getElementById('suggestions');
    if (quickActions.style.display === 'none' || !quickActions.style.display) {
        quickActions.style.display = 'grid';
        suggestions.classList.add('hidden');
    } else {
        quickActions.style.display = 'none';
        if (messageCount === 0) {
            suggestions.classList.remove('hidden');
        }
    }
}

function disableInput() {
    document.getElementById('userInput').disabled = true;
    document.querySelector('.send-btn').disabled = true;
    document.querySelector('.menu-btn').disabled = true;
}

function enableInput() {
    document.getElementById('userInput').disabled = false;
    document.querySelector('.send-btn').disabled = false;
    document.querySelector('.menu-btn').disabled = false;
}

function focusInput() {
    document.getElementById('userInput').focus();
}

function scrollToBottom() {
    const chatContainer = document.querySelector('.chat-container');
    setTimeout(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 100);
}

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});