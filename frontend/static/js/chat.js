// RocBot Chat Interface - JavaScript

const API_URL = 'http://localhost:8000';

// State
let isWaitingForResponse = false;
let messageCount = 0;
let conversationId = generateConversationId();  // Unique ID for this session

// Generate unique conversation ID
function generateConversationId() {
    return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

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
    
    // Increment message count
    messageCount++;
    
    // Hide welcome message and suggestions after first message
    if (messageCount === 1) {
        hideWelcomeMessage();
        hideSuggestions();
    }
    
    // Add user message to chat
    addUserMessage(message);
    
    // Show typing indicator
    showTypingIndicator();
    
    // Disable input
    isWaitingForResponse = true;
    disableInput();
    
    try {
        // Use streaming endpoint
        await streamChatResponse(message);
        
    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        addBotMessage(
            "Oops! I'm having trouble connecting right now. Please make sure the API server is running on port 8000. 🤖",
            []
        );
    } finally {
        // Re-enable input
        isWaitingForResponse = false;
        enableInput();
        focusInput();
    }
}

// Stream chat response using Server-Sent Events
async function streamChatResponse(message) {
    const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            conversation_id: conversationId,
            max_sources: 5
        })
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    // Hide typing indicator
    hideTypingIndicator();
    
    // Create bot message bubble (empty at first)
    const chatFeed = document.getElementById('chatFeed');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'bot-message';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = '';  // Start empty
    
    messageDiv.appendChild(bubble);
    chatFeed.appendChild(messageDiv);
    
    let sources = [];
    let fullAnswer = '';
    
    // Read the stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        // Decode the chunk
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6);
                
                try {
                    const parsed = JSON.parse(data);
                    
                    if (parsed.type === 'sources') {
                        // Store sources for later
                        sources = parsed.data;
                        
                    } else if (parsed.type === 'token') {
                        // Append token to answer
                        fullAnswer += parsed.data;
                        bubble.innerHTML = formatText(fullAnswer);
                        scrollToBottom();
                        
                    } else if (parsed.type === 'done') {
                        // Add sources at the end
                        if (sources && sources.length > 0) {
                            addSourcesToMessage(messageDiv, sources);
                        }
                        scrollToBottom();
                        
                    } else if (parsed.type === 'complete') {
                        // Streaming complete
                        console.log('Streaming complete');
                    }
                    
                } catch (e) {
                    // Not JSON, skip
                    console.log('Non-JSON line:', line);
                }
            }
        }
    }
}

// Format text (preserve line breaks)
function formatText(text) {
    return text.replace(/\n/g, '<br>');
}

// Add sources to existing message
function addSourcesToMessage(messageDiv, sources) {
    // Filter sources - only show relevant ones
    const relevantSources = sources.filter(source => {
        const genericTitles = ['homepage', 'contact us', 'volunteer opportunities'];
        return !genericTitles.includes(source.title.toLowerCase());
    }).slice(0, 3);
    
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

// Send suggestion chip
function sendSuggestion(button) {
    const message = button.textContent;
    sendMessage(message);
}

// Add user message bubble
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

// Add bot message bubble (for non-streaming fallback)
function addBotMessage(answer, sources = []) {
    const chatFeed = document.getElementById('chatFeed');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'bot-message';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Format answer (preserve line breaks)
    const formattedAnswer = answer.replace(/\n/g, '<br>');
    bubble.innerHTML = formattedAnswer;
    
    messageDiv.appendChild(bubble);
    
    // Add sources if available
    if (sources && sources.length > 0) {
        addSourcesToMessage(messageDiv, sources);
    }
    
    chatFeed.appendChild(messageDiv);
    scrollToBottom();
}

// Get icon for source type
function getSourceIcon(source) {
    const icons = {
        'cityofrochester': '🏛️',
        'eventbrite': '🎉',
        'meetup': '👥'
    };
    return icons[source] || '🌐';
}

// Show/hide typing indicator
function showTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'block';
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    indicator.style.display = 'none';
}

// Hide welcome message
function hideWelcomeMessage() {
    const welcome = document.getElementById('welcomeMessage');
    if (welcome) {
        welcome.style.display = 'none';
    }
}

// Hide suggestions
function hideSuggestions() {
    const suggestions = document.getElementById('suggestions');
    if (suggestions) {
        suggestions.classList.add('hidden');
    }
}

// Toggle quick actions menu
function toggleQuickActions() {
    const quickActions = document.getElementById('quickActions');
    const suggestions = document.getElementById('suggestions');
    
    if (quickActions.style.display === 'none' || !quickActions.style.display) {
        quickActions.style.display = 'grid';
        suggestions.classList.add('hidden');
    } else {
        quickActions.style.display = 'none';
        // Only show suggestions if no messages yet
        if (messageCount === 0) {
            suggestions.classList.remove('hidden');
        }
    }
}

// Input controls
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

// Scroll to bottom of chat
function scrollToBottom() {
    const chatContainer = document.querySelector('.chat-container');
    setTimeout(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }, 100);
}

// Error handling for fetch
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});