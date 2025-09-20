# Dailymotion User Registration API

A production-ready user registration system with email activation.

## 🚀 Features

- **User Registration**: Create user accounts with email and password
- **Email Activation**: 4-digit activation codes sent via email  
- **Secure Authentication**: Basic Auth for activation endpoints
- **Expiring Codes**: Activation codes expire after 1 minute
- **Async Processing**: RabbitMQ for asynchronous email handling
- **Raw SQL**: PostgreSQL without ORM for optimal performance
- **Error Handling**: Comprehensive error handling with structured responses
- **Health Checks**: Built-in health monitoring endpoints
- **Docker Ready**: Fully containerized application

## 🏗️ Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │───▶│   FastAPI App   │───▶│   PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         │
                       ┌─────────────────┐              │
                       │    RabbitMQ     │              │
                       └─────────────────┘              │
                              │                         │
                              ▼                         │
                       ┌─────────────────┐              │
                       │ Email Consumer  │──────────────┘
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ Email Service   │
                       │ (HTTP/Console)  │
                       └─────────────────┘
```

### Code Base Structure
```
src/
├── domain/                 # Business logic layer
│   ├── user/
│   │   ├── entities.py     # User and ActivationCode entities
│   │   ├── repository.py   # Repository interfaces
│   │   └── service.py      # Business logic
│   └── exceptions/         # Domain exceptions
├── infrastructure/         # Technical implementation layer
│   ├── database/          # PostgreSQL client
│   ├── messaging/         # RabbitMQ client
│   ├── email/             # Email service
│   └── auth/              # Authentication utilities
├── routers/               # API routes
└── schemas/               # API request/response models
```

## Prerequisites

- Docker and Docker Compose (only requirements!)
- No need to install Python, PostgreSQL, or RabbitMQ locally

## Quick Start

Get the project running with just two Makefile commands:

1. **Clone the repository**
   ```bash
   git clone git@github.com:Zoulama/djimera-user-registration-api.git
   cd djimera-user-registration-api
   ```

2. **Set up environment configuration**
   ```bash
   cp .env.example .env
   ```
   > **Note:** The default values in `.env` work out of the box with Docker Compose. 
   > Only modify them if you need custom configuration.

3. **Build the project** (choose one):
   ```bash
   # First time (slow but thorough)
   make build
   ```

4. **Start all services**
   ```bash
   make up
   ```

5. **Verify services are running**
   - API Health Check: http://localhost:8000/health
   - API Documentation: http://localhost:8000/docs
   - Email UI: http://localhost:8025

### Available Makefile Commands:
- `make build` - Build Docker images
- `make up` - Start all services
- `make stop` - Stop services (keep containers)
- `make down` - Stop and remove all containers
- `make test-user-service` - Run a test for user service

## Quick Test

Once services are running, test the complete registration and activation flow:

### Step-by-Step Test Guide:

**1. Register a new user:**
```bash
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "tester@example.com", "password": "TestPass123"}'
```

**2. Find the activation code in logs:**
```bash
docker compose logs app --tail=10
```
**Look for this line:**
```
dailymotion-user-api | Activation code sent via console to tester@example.com: 7498
```
The 4-digit number (e.g., `7498`) is your activation code.

**3. Activate the user account:**
```bash
curl -X POST "http://localhost:8000/api/v1/users/activate" \
  -H "Content-Type: application/json" \
  -d '{"email": "tester@example.com", "password": "TestPass123", "code": "7498"}'
```
*(Replace `7498` with your actual activation code)*

**4. Expected result:**
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid-here",
    "email": "tester@example.com", 
    "status": "ACTIVE",
    "activated_at": "2025-09-19T17:56:48Z",
    "message": "Account activated successfully."
  }
}
```


## API Endpoints

### Registration Workflow

#### 1. Register User
```http
POST /api/v1/users/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "status": "PENDING",
    "message": "User registered successfully. Please check your email for activation code."
  }
}
```

#### 2. Find Your Activation Code

After registration, the activation code is displayed in the application logs. Use this command to view the logs:

```bash
docker compose logs app --tail=10
```

**Look for this line in the output:**
```
dailymotion-user-api  | Activation code sent via console to user@example.com: 7498
```

The **4-digit number at the end** is your activation code (in this example: `7498`).

**Alternative:** You can also see the full email notification format:
```
============================================================
📧 EMAIL NOTIFICATION (Console Mode)
============================================================
To: user@example.com
Subject: Your Dailymotion Activation Code

Your activation code is: 7498
This code will expire in 1 minute.

Please use this code to activate your Dailymotion account.
============================================================
```

#### 3. Activate Account
```http
POST /api/v1/users/activate
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "code": "1234"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "status": "ACTIVE",
    "activated_at": "2023-12-01T10:30:00Z",
    "message": "Account activated successfully."
  }
}
```

### Additional Endpoints

#### Resend Activation Code
```http
POST /api/v1/users/resend-activation
Authorization: Basic dXNlckBleGFtcGxlLmNvbTpwYXNzd29yZDEyMw==
```

#### Health Check
```http
GET /health
```

## Authentication

### Activation Endpoint
The `/api/v1/users/activate` endpoint uses **request body authentication**:
- All credentials (email, password, code) are sent in the JSON request body
- No authorization headers required

### Resend Activation Endpoint 
The `/api/v1/users/resend-activation` endpoint still uses **HTTP Basic Authentication**:
- **Username**: User's email address
- **Password**: User's password

## Testing

### Run Unit Tests
```bash
# Inside the container
docker-compose exec app pytest tests/ -v
```

### Manual API Testing
```bash
# 1. Register user
curl -X POST "http://localhost:8000/api/v1/users/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "password123"}'

# 2. Get activation code from logs (use one of these commands)
docker compose logs app --tail=10
# OR filter for activation codes only:
docker compose logs app | grep "activation code"

# 3. Activate user (replace 1234 with the actual code from logs)
curl -X POST "http://localhost:8000/api/v1/users/activate" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "password123", "code": "1234"}'
```

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key configuration options:
- `DEBUG`: Enable debug mode (default: false)
- `DATABASE_HOST`: PostgreSQL host (default: postgres in Docker)
- `RABBITMQ_HOST`: RabbitMQ host (default: rabbitmq in Docker)
- `EMAIL_SERVICE_URL`: External email service URL
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

### Production Settings
For production deployment:
1. Change `SECRET_KEY` to a secure random string
2. Set `DEBUG=false`
3. Configure proper CORS origins
4. Set up proper database credentials
5. Configure external email service

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE NULL
);
```

### Activation Codes Table
```sql
CREATE TABLE activation_codes (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code VARCHAR(4) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE NULL,
    is_used BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, code)
);
```

## Monitoring

### Service Health Checks
- **API Health**: `GET /health`
- **Individual Service Health**: `GET /api/v1/users/health`
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### Logs
```bash
# Application logs
docker-compose logs app

# Database logs
docker-compose logs postgres

# RabbitMQ logs
docker-compose logs rabbitmq

# Email service logs
docker-compose logs email-service
```

## Security Features

- **Password Hashing**: bcrypt with 12 rounds
- **Email Validation**: Comprehensive email format validation
- **Input Validation**: Pydantic schemas for request validation
- **SQL Injection Protection**: Parameterized queries
- **Rate Limiting**: Built-in FastAPI protection
- **Error Handling**: No sensitive data in error responses

## Performance

- **Async Operations**: All I/O operations are asynchronous
- **Connection Pooling**: PostgreSQL and RabbitMQ connection pools
- **Raw SQL**: No ORM overhead
- **Horizontal Scaling**: Stateless application design
- **Background Processing**: Email sending via message queues

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   docker-compose down
   docker-compose up --build
   ```

2. **Database connection issues**
   ```bash
   docker-compose logs postgres
   ```

3. **Activation code expired**
   Request a new code via `/resend-activation` endpoint