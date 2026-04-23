# AgentOPSYN

AgentOPSYN is an Agentic Developer Experience Platform that helps developers understand, debug, and automate workflows across tools like GitHub, logs, Slack, Jira, and more.

Instead of manually digging through dashboards and logs, you can:

- Ask: “Why did this fail?”
- Get contextual answers across systems
- Automate repetitive developer workflows

---

## Vision

AgentOPSYN is a control plane for developer operations, powered by:

- Retrieval-Augmented Generation (RAG)
- Tool-integrated AI agents
- Real-time system insights

---

## Tech Stack

### Backend
- Python (Django)
- PostgreSQL
- psycopg
- Django REST Framework (planned)

### Frontend
- React (Vite)
- TypeScript

### Infrastructure
- Docker
- Docker Compose

### AI / Integrations (Planned / Partial)
- Groq API
- Hugging Face
- GitHub, Slack, Notion, Jira integrations

---

## Project Structure

```
AgentOPSYN/
│
├── backend/
│   ├── backend/          # Django core config
│   ├── accounts/         # Auth system
│   ├── agent/            # AI agent logic
│   ├── approvals/        # Workflow approvals
│   ├── integrations/     # External tools
│   ├── knowledge/        # RAG / embeddings layer
│   ├── runbooks/         # Automated workflows
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── wait_for_db.py
│   └── .env              # Not committed
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   ├── runbooks/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── AgentChat.tsx
│   │   │   └── IntegrationManager.tsx
│   │   ├── utils/
│   │   │   └── api.ts
│   ├── Dockerfile
│   ├── package.json
│   └── ...
│
├── docker-compose.yml
└── README.md
```

---

## Environment Variables

Create a `.env` file inside `backend/`:

```
SECRET_KEY=your-secret-key
DEBUG=True

DB_NAME=agentopsyn_db
DB_USER=agentopsyn_user
DB_PASSWORD=strongpassword123
DB_HOST=db
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:3000

FERNET_KEY=your-fernet-key
GROQ_API_KEY=your-groq-key
HF_TOKEN=your-huggingface-token
```

---

## Generating Required Keys

### Django SECRET_KEY

Run this command:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### FERNET_KEY

Run:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

---

## Setup Instructions

### 1. Prerequisites

- Docker
- Docker Compose

---

### 2. Build and Run

```bash
docker compose up --build
```

---

### 3. Run Migrations

```bash
docker exec -it agentopsyn_backend python manage.py migrate
```

Optional:

```bash
docker exec -it agentopsyn_backend python manage.py createsuperuser
```

---

### 4. Install Frontend Dependency

```bash
docker exec -it agentopsyn_frontend npm install axios
```

---

### 5. Access Application

Backend: http://localhost:8000  
Frontend: http://localhost:3000 (if configured)

---

## Useful Commands

```bash
docker compose up
docker compose up -d
docker compose down
docker compose up --build
docker compose logs -f
```

---

## Integration Tokens Setup

### GitHub Token

1. Go to https://github.com/settings/tokens  
2. Generate a new token  
3. Select scopes:
   - repo
   - workflow
   - read:org  

---

### Notion API Key

1. Go to https://www.notion.so/my-integrations  
2. Create integration  
3. Copy internal token  
4. Share pages with integration  

---

### Slack Token

1. Go to https://api.slack.com/apps  
2. Create app  
3. Add OAuth scopes:
   - channels:read
   - chat:write
   - users:read  
4. Install app and copy bot token  

---

### Jira API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens  
2. Create token  
3. Use email and token for authentication  

---

### Groq API Key

1. Go to https://console.groq.com  
2. Generate API key  

---

### Hugging Face Token

1. Go to https://huggingface.co/settings/tokens  
2. Create token  

---

## Development Guidelines

### Backend
- Use modular Django apps
- Keep integrations isolated
- Put business logic in services

### Frontend
- Use reusable components
- Keep API calls inside `utils/api.ts`
- Maintain clean routing

---

## Current Status

- Docker setup working  
- Backend running  
- Database connected  
- APIs in progress  
- Agent system under development  

---

## Roadmap

- Authentication (JWT)
- Integrations (GitHub, Slack, Jira)
- RAG pipeline
- Agent orchestration
- Workflow automation
- Deployment

---

## Notes

- Do not commit `.env`
- Check logs if issues occur:
  ```bash
  docker compose logs -f
  ```
- Restart containers if database issues occur

---

## Contribution

- Follow project structure
- Write clean, modular code
- Keep things scalable
