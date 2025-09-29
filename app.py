from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration - From .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_HISTORY_FILE = "chat_history.json"
SITE_URL = os.getenv("SITE_URL", "https://ai-1-itlj.onrender.com")

# Initialize OpenAI client for OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENAI_API_KEY,
)

# Emergency keywords
EMERGENCY_KEYWORDS = [
    "chest pain", "difficulty breathing", "shortness of breath", "severe pain",
    "unconscious", "heart attack", "stroke", "bleeding heavily",
    "सीने में दर्द", "सांस लेने में दिक्कत", "बेहोशी", "तेज दर्द"
]

def load_chat_history():
    """Load chat history from local file"""
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_chat_history(history):
    """Save chat history to local file"""
    try:
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving chat history: {e}")

def detect_emergency(text):
    """Check if message contains emergency keywords"""
    return any(keyword.lower() in text.lower() for keyword in EMERGENCY_KEYWORDS)

def get_gpt_response(user_input, chat_history):
    """Get response from OpenRouter API using OpenAI library"""
    messages = [{"role": "system", "content": "You are a friendly healthcare assistant who can speak English, Hindi, and Punjabi. Provide helpful health advice but always remind users to consult doctors for serious issues. Keep responses concise and caring."}]
    
    # Add last 6 messages for context
    for chat in chat_history[-6:]:
        if chat.get("user"):
            messages.append({"role": "user", "content": chat["user"]})
        if chat.get("bot"):
            messages.append({"role": "assistant", "content": chat["bot"]})
    
    messages.append({"role": "user", "content": user_input})

    try:
        print(f"🔄 Sending request to OpenRouter...")
        print(f"🌐 Site: {SITE_URL}")
        print(f"🔑 Key: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'NOT SET'}...")
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": "Healthcare Assistant"
            },
            model="openai/gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=400
        )
        
        response_text = completion.choices[0].message.content.strip()
        print(f"✅ Success! Response: {response_text[:100]}...")
        return response_text
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        
        # Handle specific errors
        if "401" in error_msg or "authentication" in error_msg.lower():
            return "⚠️ API authentication failed. Please check your OpenRouter API key."
        elif "402" in error_msg or "credit" in error_msg.lower():
            return "⚠️ API credits exhausted. Please add credits to your OpenRouter account."
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return "⚠️ Too many requests. Please wait a moment and try again."
        elif "timeout" in error_msg.lower():
            return "⚠️ Request timed out. Please try again."
        else:
            return f"⚠️ Something went wrong, please try again."


@app.route('/')
def home():
    """Main page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        print(f"💬 User: {user_message}")
        
        # Load chat history
        chat_history = load_chat_history()
        
        # Check for emergency
        is_emergency = detect_emergency(user_message)
        
        if is_emergency:
            bot_response = "🚨 This may be an emergency! Please seek urgent medical help immediately:\n\n📞 Call 102 (Ambulance)\n📞 Call 108 (Emergency)\n🏥 Visit nearest hospital\n\nYour safety is the priority!"
        else:
            # Get AI response
            bot_response = get_gpt_response(user_message, chat_history)
        
        print(f"🤖 Bot: {bot_response[:100]}...")
        
        # Create chat entry
        chat_entry = {
            'user': user_message,
            'bot': bot_response,
            'timestamp': datetime.now().isoformat(),
            'is_emergency': is_emergency
        }
        
        # Add to history and save
        chat_history.append(chat_entry)
        save_chat_history(chat_history)
        
        return jsonify({
            'response': bot_response,
            'is_emergency': is_emergency,
            'timestamp': chat_entry['timestamp']
        })
        
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/api/history')
def get_history():
    """Get chat history"""
    history = load_chat_history()
    return jsonify(history)

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    """Clear chat history"""
    try:
        save_chat_history([])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_api():
    """Test endpoint"""
    return jsonify({
        'status': 'ok',
        'site_url': SITE_URL,
        'api_key_set': bool(OPENAI_API_KEY),
        'api_key_prefix': OPENAI_API_KEY[:20] if OPENAI_API_KEY else None,
        'model': 'openai/gpt-4o-mini'
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create simple HTML template
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏥 Healthcare Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Arial', sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }

        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
        }

        .header h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }

        .header p {
            font-size: 14px;
            opacity: 0.9;
        }

        .warning {
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            text-align: center;
            border-bottom: 2px solid #ffeaa7;
        }

        .chat-area {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            max-height: 60vh;
        }

        .message {
            margin-bottom: 20px;
            clear: both;
        }

        .message.user {
            text-align: right;
        }

        .message-bubble {
            display: inline-block;
            max-width: 80%;
            padding: 12px 18px;
            border-radius: 20px;
            word-wrap: break-word;
        }

        .message.user .message-bubble {
            background: #3498db;
            color: white;
            border-bottom-right-radius: 5px;
        }

        .message.bot .message-bubble {
            background: #ecf0f1;
            color: #2c3e50;
            border-bottom-left-radius: 5px;
        }

        .message.emergency .message-bubble {
            background: #e74c3c;
            color: white;
        }

        .message-time {
            font-size: 11px;
            opacity: 0.6;
            margin-top: 5px;
        }

        .input-area {
            background: white;
            padding: 20px;
            border-top: 1px solid #eee;
        }

        .input-container {
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }

        #messageInput {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #ddd;
            border-radius: 25px;
            font-size: 16px;
            resize: none;
            min-height: 45px;
            max-height: 100px;
            outline: none;
        }

        #messageInput:focus {
            border-color: #3498db;
        }

        .send-btn {
            background: #3498db;
            color: white;
            border: none;
            width: 45px;
            height: 45px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .send-btn:hover {
            background: #2980b9;
        }

        .send-btn:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
        }

        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }

        .clear-btn {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
        }

        .clear-btn:hover {
            background: #c0392b;
        }

        .typing {
            display: none;
            color: #7f8c8d;
            font-style: italic;
            padding: 10px 18px;
        }

        .welcome {
            text-align: center;
            padding: 40px 20px;
            color: #7f8c8d;
        }

        .welcome h2 {
            color: #2c3e50;
            margin-bottom: 15px;
        }

        .welcome ul {
            text-align: left;
            max-width: 300px;
            margin: 20px auto;
        }

        @media (max-width: 600px) {
            .container {
                margin: 0;
                height: 100vh;
            }
            
            .message-bubble {
                max-width: 90%;
            }
            
            .header h1 {
                font-size: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Healthcare Assistant</h1>
            <p>Your friendly health companion - English, Hindi, Punjabi</p>
        </div>
        
        <div class="warning">
            ⚠️ This provides general advice only. For emergencies, seek immediate medical help!
        </div>
        
        <div class="chat-area" id="chatArea">
            <div class="welcome" id="welcome">
                <h2>👋 Hello!</h2>
                <p>I'm your healthcare assistant. I can help you with:</p>
                <ul>
                    <li>Understanding symptoms</li>
                    <li>General health advice</li>
                    <li>When to see a doctor</li>
                    <li>Wellness tips</li>
                </ul>
                <p><strong>What's your name? Let's get started!</strong></p>
            </div>
            
            <div class="typing" id="typing">
                Healthcare assistant is typing...
            </div>
        </div>
        
        <div class="input-area">
            <div class="controls">
                <button class="clear-btn" onclick="clearChat()">🗑️ Clear Chat</button>
            </div>
            <div class="input-container">
                <textarea 
                    id="messageInput" 
                    placeholder="Type your health question here..."
                    onkeydown="handleKeyPress(event)"
                ></textarea>
                <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                    ➤
                </button>
            </div>
        </div>
    </div>

    <script>
        // Auto-resize textarea
        document.getElementById('messageInput').addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });

        // Handle Enter key
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        // Send message
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Hide welcome message
            document.getElementById('welcome').style.display = 'none';
            
            // Disable send button
            const sendBtn = document.getElementById('sendBtn');
            sendBtn.disabled = true;
            
            // Add user message
            addMessage(message, 'user');
            
            // Clear input
            input.value = '';
            input.style.height = 'auto';
            
            // Show typing indicator
            showTyping();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    addMessage(data.response, 'bot', data.is_emergency);
                } else {
                    addMessage('Sorry, something went wrong. Please try again.', 'bot');
                }
                
            } catch (error) {
                console.error('Error:', error);
                addMessage('Connection error. Please check your internet and try again.', 'bot');
            }
            
            // Hide typing and enable send button
            hideTyping();
            sendBtn.disabled = false;
        }

        // Add message to chat
        function addMessage(content, sender, isEmergency = false) {
            const chatArea = document.getElementById('chatArea');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}${isEmergency ? ' emergency' : ''}`;
            
            const time = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    ${content}
                </div>
                <div class="message-time">${time}</div>
            `;
            
            chatArea.appendChild(messageDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }

        // Show typing indicator
        function showTyping() {
            document.getElementById('typing').style.display = 'block';
            document.getElementById('chatArea').scrollTop = document.getElementById('chatArea').scrollHeight;
        }

        // Hide typing indicator
        function hideTyping() {
            document.getElementById('typing').style.display = 'none';
        }

        // Clear chat
        async function clearChat() {
            if (confirm('Clear all chat history?')) {
                try {
                    await fetch('/api/clear_history', { method: 'POST' });
                    location.reload();
                } catch (error) {
                    alert('Failed to clear chat');
                }
            }
        }

        // Load chat history on page load
        async function loadHistory() {
            try {
                const response = await fetch('/api/history');
                const history = await response.json();
                
                if (history.length > 0) {
                    document.getElementById('welcome').style.display = 'none';
                    
                    history.forEach(chat => {
                        if (chat.user) {
                            addMessage(chat.user, 'user');
                        }
                        if (chat.bot) {
                            addMessage(chat.bot, 'bot', chat.is_emergency);
                        }
                    });
                } else {
                    // Auto-start conversation
                    setTimeout(() => {
                        addMessage("Hello! I'm your healthcare assistant. What's your name?", 'bot');
                    }, 1000);
                }
            } catch (error) {
                console.error('Failed to load history:', error);
            }
        }

        // Load history when page loads
        document.addEventListener('DOMContentLoaded', loadHistory);
    </script>
</body>
</html>'''
    
    # Write the HTML template to file
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("=" * 60)
    print("🏥 Healthcare Assistant Starting...")
    print("=" * 60)
    print(f"🌐 Local: http://localhost:5000")
    print(f"🌐 Deployed: {SITE_URL}")
    print(f"🔑 API Key: {OPENAI_API_KEY[:20] if OPENAI_API_KEY else 'NOT SET'}...")
    print(f"🤖 Model: openai/gpt-4o-mini")
    print(f"💾 Chat History: {CHAT_HISTORY_FILE}")
    print(f"🧪 Test Endpoint: {SITE_URL}/api/test")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
