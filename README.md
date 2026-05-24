# User Management API

A production-ready RESTful API for user management built with **FastAPI**, **SQLModel**, and **PostgreSQL**. Deployed to **Google Cloud Run** via **Cloud Build** CI/CD.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| ORM | SQLModel 0.0.21 (SQLAlchemy + Pydantic v2) |
| Database | PostgreSQL 16 (Cloud SQL in production) |
| Migrations | Alembic |
| Testing | pytest + httpx (SQLite in-memory) |
| Container | Docker (multi-stage) |
| CI/CD | Google Cloud Build → Cloud Run |

---

## Running Locally (Docker Compose)

```bash
# 1. Clone and enter the project
git clone <YOUR_REPO_URL>
cd SWE

# 2. Start API + PostgreSQL
docker compose up --build

# 3. Open interactive docs
open http://localhost:8000/docs
```

## Running Locally (Without Docker)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set DATABASE_URL to your local PostgreSQL instance

# 4. Apply migrations
alembic upgrade head

# 5. Start the server
uvicorn app.main:app --reload
```

API available at `http://localhost:8000` · Swagger UI at `http://localhost:8000/docs`

---

## Running Tests

```bash
# Tests use SQLite in-memory — no database setup required
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## API Endpoints

| Method | Path | Description | Status |
|---|---|---|---|
| `GET` | `/api/v1/users` | List users (paginated) | 200 |
| `POST` | `/api/v1/users` | Create user | 201 |
| `GET` | `/api/v1/users/{id}` | Get user by UUID | 200 / 404 |
| `PUT` | `/api/v1/users/{id}` | Full update user | 200 / 404 / 409 |
| `PATCH` | `/api/v1/users/{id}` | Partial update user | 200 / 404 / 409 |
| `DELETE` | `/api/v1/users/{id}` | Delete user | 204 / 404 |
| `GET` | `/health` | Health check | 200 |

### Example API Calls

**Create a user**
```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jane_doe",
    "email": "jane@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "admin",
    "active": true
  }'
```

**List users (paginated)**
```bash
curl "http://localhost:8000/api/v1/users?skip=0&limit=10"
```

**Get user by ID**
```bash
curl http://localhost:8000/api/v1/users/<uuid>
```

**Partial update**
```bash
curl -X PATCH http://localhost:8000/api/v1/users/<uuid> \
  -H "Content-Type: application/json" \
  -d '{"active": false}'
```

**Delete user**
```bash
curl -X DELETE http://localhost:8000/api/v1/users/<uuid>
```

---

## User Schema

| Field | Type | Description |
|---|---|---|
| `id` | UUID v4 | Auto-generated primary key |
| `username` | string | Unique, alphanumeric (3–50 chars) |
| `email` | string | Unique, validated email |
| `first_name` | string | Max 100 chars |
| `last_name` | string | Max 100 chars |
| `role` | enum | `admin` \| `user` \| `guest` |
| `created_at` | datetime | Set on creation (UTC) |
| `updated_at` | datetime | Updated on every PATCH/PUT |
| `active` | boolean | Default `true` |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/userdb` |
| `APP_NAME` | OpenAPI title | `User Management API` |
| `APP_VERSION` | OpenAPI version | `1.0.0` |

---

## GCP Deployment

### Prerequisites

```bash
gcloud auth login
gcloud config set project <YOUR_PROJECT_ID>

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com
```

### 1 — Create Artifact Registry repository

```bash
gcloud artifacts repositories create user-management \
  --repository-format=docker \
  --location=us-central1
```

### 2 — Store database URL as a Secret Manager secret

```bash
echo -n "postgresql://USER:PASS@/userdb?host=/cloudsql/PROJECT:REGION:INSTANCE" | \
  gcloud secrets create DATABASE_URL --data-file=-
```

Grant Cloud Build and Cloud Run access to the secret:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3 — Grant Cloud Build permission to deploy Cloud Run

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud iam service-accounts add-iam-policy-binding \
  ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 4 — Trigger a build (manual)

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_REPO=user-management,_SERVICE=user-management-api
```

### 5 — (Optional) Connect Cloud Build to GitHub for automatic CI/CD

In the GCP Console → Cloud Build → Triggers → Connect Repository, then create a trigger on push to `main` using `cloudbuild.yaml`.

### 6 — Run Alembic migrations on Cloud Run

```bash
gcloud run jobs create migrate \
  --image "${REGION}-docker.pkg.dev/${PROJECT_ID}/user-management/user-management-api:latest" \
  --region us-central1 \
  --update-secrets DATABASE_URL=DATABASE_URL:latest \
  --command alembic \
  --args "upgrade,head"

gcloud run jobs execute migrate --region us-central1
```

---

## Project Structure

```
.
├── app/
│   ├── main.py               # FastAPI app factory, lifespan, CORS, logging
│   ├── config.py             # Settings via pydantic-settings (.env)
│   ├── database.py           # SQLModel engine + get_session dependency
│   ├── models/
│   │   └── user.py           # SQLModel table definition (source of truth)
│   ├── schemas/
│   │   └── user.py           # Pydantic I/O schemas (UserCreate, UserResponse…)
│   ├── services/
│   │   └── user_service.py   # Business logic + DB queries
│   └── routers/
│       └── users.py          # CRUD endpoints with OpenAPI docs
├── tests/
│   ├── conftest.py           # SQLite in-memory fixtures
│   └── test_users.py         # 20+ tests covering all endpoints
├── alembic/                  # Database migrations
├── Dockerfile                # Multi-stage build
├── docker-compose.yml        # Local dev: API + PostgreSQL
├── cloudbuild.yaml           # GCP CI/CD pipeline
└── requirements.txt
```

---

## Original Challenge

> **Software Engineer Challenge** — Overview  
> Welcome to the Software Engineer Application Challenge. In this challenge, you will demonstrate your skills in backend development, API design, testing, and cloud deployment.

## Problem
You will develop a RESTful API for user management with complete CRUD (Create, Read, Update, Delete) operations. The application should handle user data with the following attributes:

| Field       | Description                              |
|-------------|------------------------------------------|
| id          | Unique identifier for each user          |
| username    | User's unique username                   |
| email       | User's email address                     |
| first_name  | User's first name                        |
| last_name   | User's last name                         |
| role        | User role (admin, user, guest)           |
| created_at  | Timestamp when the user was created      |
| updated_at  | Timestamp when the user was last updated |
| active      | Boolean indicating if the user is active |

## Challenge

### Context:
In today's digital landscape, effective user management is a foundational component of virtually all software applications. This challenge simulates a real-world scenario where a user management API is needed for a growing application.

As a Software Engineer, you've been tasked with building a robust and scalable user management API that will serve as the backbone for user-related operations. The API should provide a clean interface for creating, retrieving, updating, and deleting user profiles while ensuring data integrity and following industry best practices.

Beyond just functionality, we're interested in seeing your approach to software architecture, code organization, testing strategies, and cloud deployment skills. This challenge is designed to showcase not only your technical abilities but also your understanding of production-ready software development.


### API Development
Develop an API with FastAPI:

- Implement all CRUD endpoints for user management
- Add proper input validation for all requests
- Document all endpoints using OpenAPI/Swagger
- Implement proper error handling for edge cases
- The API should connect to a database of your choice (SQL or NoSQL)
- Write detailed API tests using pytest
- Deploy your API to Google Cloud Platform (GCP)

Requirements:
- You must use FastAPI as the framework
- Provide examples of API calls for each endpoint in your documentation
- Write clean, maintainable code with proper comments
- The API should follow REST best practices
- Include at least basic logging functionality
- Create a `cloudbuild.yaml` file for Google Cloud Build that includes:
  - Building the Docker image
  - Running tests
  - Deploying the application to Google Cloud Run or App Engine

### Evaluation Criteria
Your submission will be evaluated based on the following criteria:

- **Code Quality**: Readability, organization, and adherence to Python best practices
- **API Design**: Proper implementation of RESTful principles and resource modeling
- **Data Handling**: Effective data validation, error handling, and database integration
- **Testing**: Comprehensive test coverage and proper test organization
- **Documentation**: Clear and complete API documentation
- **Cloud Deployment**: Successful deployment to GCP and proper configuration
- **CI/CD Implementation**: Quality and completeness of the `cloudbuild.yaml` file
- **Overall Functionality**: The API works as expected for all CRUD operations

### Submission Instructions
To submit your challenge, you must do a POST request to: https://advana-challenge-check-api-cr-k4hdbggvoq-uc.a.run.app/software-engineer

This is an example of the body you must send:

```json
{
  "name": "Juan Perez",
  "mail": "juan.perez@example.com",
  "github_url": "https://github.com/juanperez/se-challenge.git",
  "api_url": "https://juan-perez.api"
}
```

PLEASE, SEND THE REQUEST ONLY ONCE.
If your request was successful, you will receive this message:

```
jsonCopiar{
  "status": "OK",
  "detail": "your request was received"
}
```

NOTE: We recommend sending the challenge even if you didn't manage to finish all the parts.