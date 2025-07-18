# Assistant to the Regional Manager

A sophisticated AI-powered assistant that integrates with Gmail to automatically detect, create, and manage tasks from emails. Built with FastAPI, Streamlit, and powered by Mistral AI.

## 🌟 Features

### Core Functionality
- **Gmail Integration**: Automatic email monitoring and task extraction based on Gmail Pub/Sub triggers
- **AI-Powered Task Detection**: Uses Mistral AI to intelligently identify tasks from emails
- **Task Management**: Full CRUD operations for tasks with priority and due date support
- **Real-time Chat Interface**: Interactive chatbot with conversation history
- **OAuth Authentication**: Secure Google OAuth integration for Gmail access
- **Multi-session Support**: Manage multiple chat sessions with persistent history

### Advanced Features
- **Smart Prompt Management**: Dynamic prompt selection based on conversation context
- **Vector-based Memory**: FAISS-powered semantic search for conversation history
- **Calendar Integration**: Schedule and manage calendar events
- **Web Search Capabilities**: Real-time web search for current information
- **Database Persistence**: PostgreSQL with Alembic migrations
- **Redis Caching**: High-performance session and data caching



## 🏗️ Architecture

### System Overview
```mermaid
graph TB
    subgraph "Frontend Layer"
        A[Streamlit UI<br/>Port 8501]
        A1[Chat Interface]
        A4[Prompt Manager]
        A2[Task Manager]
        A3[Auth UI]
        A --> A1
        A --> A2
        A --> A3
        A --> A4
    end
    
    subgraph "Backend Layer"
        B[FastAPI Server<br/>Port 8000]
        C[Assistant Agent]
        D[Task Detector]
        E[Hybrid Context Manager]
        F[MCP Servers]
        
        B --> C
        B --> D
        C --> E
        C --> F
        E --> F
    end
    
    subgraph "Data Layer"
        Q[Prompts]
        G[PostgreSQL<br/>Port 5432]
        I[FAISS Vector Store]
        H[Redis<br/>Port 6379]

        
        R[Prompt Index]
        O[Long-Term Cross Chat Memory]
        P[Short/Medium-Term Chat Session Memory]

        G3[User Sessions]
        G1[Users Table]
        G2[Tasks Table]
        G --> G1
        G --> G2
        G --> G3
    end
    
    subgraph "External Services"
        M[Gmail Pub/Sub]
        J[Gmail API]
        K[Google Calendar]
        L[Web Search]
    end
    
    %% Frontend to Backend
    A <--> B
    A3 <--> G1
    A2 <--> G2
    
    %% Backend to Data
    B <--> G
    
    E <--> H
    B <--> H
    E <--> I
    
    %% External Integrations
    D <--> J
    D <--> M
    F <--> J
    F <--> K
    F <--> L
    
    %% Data Flow
    F <--> Q
    I <--> O
    Q <--> R
    I <--> R
    H <--> P
   
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style G fill:#e8f5e8
    style H fill:#ffb3b3
```

### Backend (FastAPI)
- **API Layer**: RESTful endpoints for chat, tasks, authentication, and OAuth
- **Agent System**: Modular AI agents with specialized tools and prompts
- **Database Layer**: SQLAlchemy ORM with PostgreSQL
- **Memory Management**: Redis-based session storage and vector search
- **Task Detection**: AI-powered email analysis and task extraction

### Frontend (Streamlit)
- **Chat Interface**: Real-time messaging with the AI assistant
- **Task Manager**: Visual task management with filtering and sorting
- **Authentication UI**: User registration, login, and OAuth flow
- **Prompt Manager**: Dynamic prompt editing and management
- **Session Management**: Multi-session chat history

### Infrastructure
- **Docker Compose**: Complete containerized development environment
- **PostgreSQL**: Primary database for users, tasks, and sessions
- **Redis**: Caching and session storage
- **Alembic**: Database migration management

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+
- Google Cloud Project (for Gmail API)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AssistantToTheRegionalManager
```

### 2. Environment Setup
Create a `.env` file in the root directory:
```env
# Mistral AI Configuration
MISTRAL_KEY=your_mistral_api_key

# API Configuration
FASTAPI_URI=http://fastapi:8000
REDIRECT_URI=http://localhost:8000/oauth2callback

# Google OAuth Configuration
GOOGLE_CLIENT_SECRET_JSON=google_setup/client_secret.json
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_TOPIC=your_pubsub_topic

# Database Configuration (optional - defaults are used)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=taskmanager

# Redis Configuration (optional - defaults are used)
REDIS_URL=redis://localhost:6379

# Optional Configuration
MCP_SERVER_PATH=backend/assistant_app/mcp_server.py
ENVIRONMENT=development
```

### 3. Start the Application
```bash
# Start all services
docker-compose up -d

# Or start with logs
docker-compose up
```

### 4. Access the Application
- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **PostgreSQL Database**: localhost:5432
- **Redis**: localhost:6379

## 📋 Setup Instructions

### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API and Google+ API
4. Create OAuth 2.0 credentials
5. Download the client secret JSON file
6. Place the JSON file in the `google_setup/` directory as `client_secret.json`
7. Add authorized redirect URIs:
   - `http://localhost:8000/oauth2callback`
   - `http://localhost:8501/oauth2callback`
8. Copy your Project ID to the `GOOGLE_PROJECT_ID` variable in your `.env` file
9. Create a Pub/Sub topic for Gmail notifications and add it to `GOOGLE_TOPIC` in your `.env` file

### Database Setup
```bash
# Run database migrations
docker-compose exec fastapi alembic upgrade head
```

### First Time Setup
1. Access the Streamlit UI at http://localhost:8501
2. Register a new account
3. Login and authenticate with Google
4. Grant Gmail permissions
5. Start chatting with your AI assistant!

## 🛠️ Development

### Project Structure
```
AssistantToTheRegionalManager2/
├── backend/
│   └── assistant_app/
│       ├── agents/           # AI agents and tools
│       ├── api/             # FastAPI endpoints
│       ├── models/          # Database models
│       ├── services/        # Business logic
│       └── utils/           # Utilities and helpers
├── streamlit/               # Streamlit frontend
├── alembic/                 # Database migrations
├── scripts/                 # Utility scripts
└── docker-compose.yml       # Container orchestration
```

### Running in Development Mode
```bash
# Install dependencies
conda env create -f environment.yml
conda activate env

# Start services
docker-compose up postgres redis -d

# Run FastAPI backend
cd backend
uvicorn assistant_app.main:app --reload --host 0.0.0.0 --port 8000

# Run Streamlit frontend
cd streamlit
streamlit run main.py
```

### Database Migrations
```bash
# Create new migration
docker-compose exec fastapi alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec fastapi alembic upgrade head
```

### Database Schema
```mermaid
erDiagram
    USERS {
        string id PK
        string email UK
        string password_hash
        datetime last_login
        boolean is_oauth_authenticated
        datetime created_at
    }
    
    USER_SESSIONS {
        string id PK
        string user_id FK
        string session_token UK
        datetime expires_at
        boolean is_active
        datetime last_activity
        datetime created_at
    }
    
    TASKS {
        string id PK
        string ticket_id UK
        string title
        text description
        datetime due_date
        integer priority
        string status
        string user_id FK
        string gmail_message_id UK
        datetime created_at
        datetime updated_at
    }
    
    TICKET_COUNTER {
        integer id PK
        integer last_number
    }
    
    USERS ||--o{ USER_SESSIONS : "has"
    USERS ||--o{ TASKS : "creates"
    USER_SESSIONS }o--|| USERS : "belongs_to"
    TASKS }o--|| USERS : "belongs_to"
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MISTRAL_KEY` | Mistral AI API Key | - | ✅ Required |
| `FASTAPI_URI` | FastAPI server URI | http://fastapi:8000 | ✅ Required |
| `REDIRECT_URI` | OAuth redirect URI | http://localhost:8000/oauth2callback | ✅ Required |
| `GOOGLE_CLIENT_SECRET_JSON` | Path to Google client secret JSON file | google_setup/client_secret.json | ✅ Required |
| `GOOGLE_PROJECT_ID` | Google Cloud Project ID | - | ✅ Required |
| `GOOGLE_TOPIC` | Google Pub/Sub topic for Gmail notifications | - | ✅ Required |
| `POSTGRES_USER` | PostgreSQL username | postgres | ❌ Optional |
| `POSTGRES_PASSWORD` | PostgreSQL password | postgres | ❌ Optional |
| `POSTGRES_HOST` | PostgreSQL host | localhost | ❌ Optional |
| `POSTGRES_PORT` | PostgreSQL port | 5432 | ❌ Optional |
| `POSTGRES_DB` | PostgreSQL database name | taskmanager | ❌ Optional |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379 | ❌ Optional |
| `MCP_SERVER_PATH` | Path to MCP server script | backend/assistant_app/mcp_server.py | ❌ Optional |
| `ENVIRONMENT` | Application environment | development | ❌ Optional |

### Docker Configuration
The application uses Docker Compose with the following services:
- **postgres**: PostgreSQL database
- **redis**: Redis cache and session storage
- **fastapi**: Backend API server
- **streamlit**: Frontend web interface

## 📚 API Documentation

### Core Endpoints
- `POST /chat` - Chat with AI assistant
- `GET /tasks` - Get user tasks
- `POST /tasks` - Create new task
- `GET /oauth2callback` - OAuth callback handler
- `POST /gmail/push` - Gmail webhook endpoint

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

## 🤖 AI Features

### Chat Conversation Flow
```mermaid
graph LR
    A[User Input] --> B[Streamlit Frontend]
    B --> C[FastAPI Backend]
    C --> D[Context Manager]
    D --> E[Vector Search<br/>FAISS]
    E --> F[Prompt Selection]
    F --> G[Mistral AI]
    G --> H[Response Generation]
    H --> I[Memory Update]
    I --> J[Response to User]
    
    subgraph "Memory System"
        K[Redis Session Store]
        L[Conversation History]
        M[Vector Embeddings]
    end
    
    D --> K
    D --> L
    D --> M
    E --> M
    I --> K
    I --> L
    I --> M
```

### Task Detection
The AI automatically detects tasks from Gmail messages using:
- Natural language processing
- Priority assessment
- Due date extraction
- Context understanding

### Task Detection Pipeline
```mermaid
flowchart TD
    A[Email Content] --> B[Text Preprocessing]
    B --> C[Content Cleaning]
    C --> D[Task Detector]
    D --> E[Mistral AI Analysis]
    E --> F{Task Detected?}
    F -->|Yes| G[Extract Task Details]
    F -->|No| H[Skip Processing]
    G --> I[Priority Assessment]
    I --> J[Due Date Extraction]
    J --> K[Task Creation]
    K --> L[Database Storage]
    L --> M[Task Available in UI]
    
    subgraph "Task Details"
        N[Title]
        O[Description]
        P[Priority Level]
        Q[Due Date]
        R[User Assignment]
    end
    
    G --> N
    G --> O
    I --> P
    J --> Q
    K --> R
```

### Conversation Memory
- Vector-based semantic search
- Context-aware responses
- Persistent conversation history
- Multi-session management

### Tools and Integrations
- **Calendar Tools**: Schedule and manage events
- **Gmail Tools**: Email composition and management
- **Web Search**: Real-time information retrieval
- **Task Management**: CRUD operations for tasks

## 🔄 Workflows

### 📧 Gmail Integration Workflow

```mermaid
sequenceDiagram
    participant Gmail
    participant PubSub
    participant Webhook
    participant TaskDetector
    participant AI
    participant Database
    
    Gmail->>PubSub: New email received
    PubSub->>Webhook: Push notification
    Webhook->>TaskDetector: Process email content
    TaskDetector->>AI: Analyze for tasks
    AI->>TaskDetector: Return task details
    TaskDetector->>Database: Create task record
    Database-->>Webhook: Task saved
    Webhook-->>PubSub: Processing complete
```

### 🔐 Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Streamlit
    participant FastAPI
    participant Google
    participant Database
    
    User->>Streamlit: Register/Login
    Streamlit->>FastAPI: Auth Request
    FastAPI->>Database: Validate User
    Database-->>FastAPI: User Data
    FastAPI-->>Streamlit: Session Token
    
    User->>Streamlit: OAuth Request
    Streamlit->>Google: Authorize
    Google-->>Streamlit: Auth Code
    Streamlit->>FastAPI: Exchange Code
    FastAPI->>Google: Token Exchange
    Google-->>FastAPI: Access Token
    FastAPI->>Database: Store Credentials
    FastAPI-->>Streamlit: OAuth Complete
```

### 📅 Calendar Integration Flow

```mermaid
sequenceDiagram
    participant User
    participant AI
    participant Calendar
    participant Database
    
    User->>AI: "Schedule meeting tomorrow"
    AI->>Calendar: Check Availability
    Calendar-->>AI: Available Slots
    AI->>Calendar: Create Event
    Calendar-->>AI: Event Created
    AI->>Database: Log Action
    AI-->>User: "Meeting scheduled for 2 PM"
```

## 🔒 Security

- **OAuth 2.0**: Secure Google authentication
- **Password Hashing**: bcrypt for user passwords
- **Session Management**: Secure session tokens
- **CORS Protection**: Configured for production use
- **Input Validation**: Pydantic models for data validation

## 📊 Monitoring and Logging

- **Health Checks**: Docker health checks for all services
- **Logging**: Structured logging with different levels
- **Error Handling**: Comprehensive error handling and recovery
- **Database Monitoring**: Connection pool management

## 🚀 Deployment

### Production Considerations
1. **Environment Variables**: Use production secrets
2. **Database**: Use managed PostgreSQL service
3. **Redis**: Use managed Redis service
4. **SSL/TLS**: Configure HTTPS
5. **CORS**: Restrict origins to your domain
6. **Rate Limiting**: Implement API rate limiting
7. **Monitoring**: Add application monitoring

---