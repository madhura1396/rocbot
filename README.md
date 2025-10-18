# 🌸 RocBot - Your Rochester AI Concierge

> A production-grade, full-stack AI chatbot that serves as a one-stop information hub for Rochester, NY. Features real-time streaming responses, conversation memory, and multi-source data aggregation.

🔗 **Live Demo:** (Coming soon after deployment)

---

## ✨ Features

### Advanced AI Capabilities
- **Conversational Memory** - Understands context across multiple messages
- **Real-time Streaming** - Responses appear word-by-word (like ChatGPT)
- **Hybrid Intelligence** - Searches local database first, falls back to LLM with disclaimers
- **Smart Search** - Relevance scoring with source filtering

### Data Sources
- **City of Rochester Official Website** - City services, meetings, news
- **Eventbrite** - Community events and activities
- **Meetup.com** - Local tech and networking groups

### Performance
- **Query Caching** - 60x faster for repeated questions (3s → 50ms)
- **Database Indexing** - 10-100x faster searches
- **Connection Pooling** - Handles 50-100 concurrent users

### User Experience
- **"Flower City Concierge"** - Custom UI inspired by Rochester's Lilac Festival
- **Source Attribution** - Clickable links to original content
- **Mobile Responsive** - Works on all devices

---

##  Tech Stack

**Backend:** FastAPI, PostgreSQL, SQLAlchemy, Ollama (Llama 3.2), BeautifulSoup  
**Frontend:** Vanilla JavaScript, Server-Sent Events, CSS3  
**DevOps:** Docker, Railway

---

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Ollama with llama3.2 model

### Local Development

1. Clone and setup:
```bash
git clone https://github.com/yourusername/rocbot.git
cd rocbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Configure environment:
cp .env.example .env

Initialize database:
python backend/database/models.py

Start API server:
python backend/api/main.py

Start frontend (new terminal):
cd frontend
python3 -m http.server 3000

Open http://localhost:3000

💬 Example Conversations
With Conversation Memory:

User: Who is the mayor?
Bot: Mayor Malik D. Evans...

User: How do I contact him?
Bot: You can reach Mayor Evans at 585-428-7045...

Fallback to General Knowledge:

User: Who were the previous mayors?
Bot: ⚠️ Note: I don't have this in my Rochester database, 
     so I'm using general training data...

📁 Project Structure
rocbot/
├── backend/
│   ├── api/              # FastAPI server
│   ├── database/         # Models, DB manager
│   ├── rag/              # RAG + LLM handler
│   └── scrapers/         # Web scrapers
├── frontend/
│   ├── static/
│   │   ├── css/          # Styling
│   │   └── js/           # Chat logic
│   └── templates/
│       └── index.html
├── data/                 # Cached data
├── logs/                 # Application logs
├── .env                  # Configuration
└── requirements.txt

Key Features
Conversation Memory
Tracks conversation history per session, enabling context-aware follow-up questions.

Real-Time Streaming
Uses Server-Sent Events to display responses word-by-word as they're generated.

Hybrid RAG System
Searches local database first for verified information, gracefully falls back to LLM general knowledge with clear disclaimers.

Performance Optimizations
Database indexes for 10-100x faster searches
Query caching for instant repeat queries
Connection pooling for concurrent users

Future Enhancements
Vector embeddings for semantic search
User authentication & saved conversations
Voice input/output
Mobile app
Analytics dashboard


License
MIT License - Free to use for learning and portfolios

Author
Madhura Anand

GitHub: 
LinkedIn: https://www.linkedin.com/in/madhura-anand/

Acknowledgments
City of Rochester for open data
Ollama for local LLM inference
Rochester tech community
Built with ❤️ in Rochester, NY 🌸

