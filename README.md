
# AgentOPSYN

AgentOPSYN is a developer tool we’re building to make it easier to understand and manage what’s happening across different tools (GitHub, logs, etc.).

Right now, this repo contains the **backend setup (Django + PostgreSQL + Docker)** and the base structure we’ll build on.

---

## What this project is (in simple terms)

The goal is to build a system where you can:

* Ask questions about your project (like “why did this fail?”)
* Get answers using data from different tools
* Eventually automate some developer workflows

Right now, we are focusing on:

* Setting up the backend
* Connecting it to a database
* Making sure everything runs properly using Docker

---

## Tech Stack

### Backend

* Python (Django)
* PostgreSQL
* psycopg (database driver)

### Frontend

* React (Vite) *(not set up yet fully)*

### Dev Setup

* Docker
* Docker Compose

---

## Project Structure

```
AgentOPSYN/
│
├── backend/
│   ├── backend/        # Django config
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── wait_for_db.py
│   └── .env            # not pushed to Git
│
├── frontend/           # React app
├── docker-compose.yml
└── .gitignore
```

---

## Setup Instructions

### 1. Requirements

Make sure you have:

* Docker
* Docker Compose

---

### 2. Create `.env` file

Inside `backend/`, create a file named `.env`:

```
SECRET_KEY=your-secret-key
DEBUG=True

DB_NAME=agentopsyn_db
DB_USER=agentopsyn_user
DB_PASSWORD=your-password
DB_HOST=db
DB_PORT=5432
```

---

### 3. Run the project

From the root folder:

```
docker compose up --build
```

This will:

* Start PostgreSQL
* Build the backend container
* Wait for DB to be ready
* Start Django server

---

### 4. Run migrations (important)

In another terminal:

```
docker exec -it agentopsyn_backend python manage.py migrate
```

(Optional)

```
docker exec -it agentopsyn_backend python manage.py createsuperuser
```

---

### 5. Open the app

Go to:

```
http://localhost:8000
```

---

## Useful Commands

Start:

```
docker compose up
```

Run in background:

```
docker compose up -d
```

Stop:

```
docker compose down
```

Rebuild:

```
docker compose up --build
```

Logs:

```
docker compose logs -f
```

---

## Notes

* Do NOT commit `.env`
* If something breaks, check logs first
* If DB issues happen, try restarting containers

---

## Who should work on what

Backend:

* Create Django apps
* Add APIs
* Handle DB models

Frontend:

* Build UI in `frontend/`
* Connect to backend APIs

---

## Current Status

* Docker setup working
* Backend running
* Database connected

---

## Next Steps

* Add authentication
* Build APIs
* Start connecting frontend
* Add AI-related features later

---

