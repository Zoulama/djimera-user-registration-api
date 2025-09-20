# Architecture Overview

## System Architecture

The Dailymotion User Registration API follows Domain-Driven Design (DDD) principles, which I have simplified through clean architecture and separation of concerns.
### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           FastAPI Routes & Controllers                  │ │
│  │  • User Registration Endpoints                         │ │
│  │  • Basic Auth Middleware                               │ │
│  │  • Request/Response Schemas                            │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               User Service                              │ │
│  │  • Registration Business Logic                         │ │
│  │  • Activation Code Management                          │ │
│  │  • Authentication & Validation                         │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │      User       │  │ ActivationCode  │  │   Exceptions    │ │
│  │   Entity        │  │     Entity      │  │   & Errors      │ │
│  │                 │  │                 │  │                 │ │
│  │ • UserStatus    │  │ • Code Gen      │  │ • Domain Rules  │ │
│  │ • Validation    │  │ • Expiration    │  │ • Error Types   │ │
│  │ • Business      │  │ • Usage Track   │  │ • Messages      │ │
│  │   Rules         │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  PostgreSQL  │  │   RabbitMQ   │  │    Email     │       │
│  │  Repository  │  │   Messaging  │  │   Service    │       │
│  │              │  │              │  │              │       │
│  │ • Raw SQL    │  │ • Async      │  │ • HTTP API   │       │
│  │ • Connection │  │   Publishing │  │ • Console    │       │
│  │   Pooling    │  │ • Queue Mgmt │  │   Fallback   │       │
│  │ • Migrations │  │ • Consumer   │  │ • Templates  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Component Flow

### 1. User Registration Flow
```
[Client] --> [FastAPI Router] --> [User Service] --> [User Repository] --> [PostgreSQL]
                    │                     │
                    │                     └-> [Email Service] --> [RabbitMQ]
                    │                                                 │
                    └-> [Response Schema]                             └-> [Email Consumer] --> [SMTP/Console]
```

### 2. Activation Flow
```
[Client + Basic Auth] --> [Auth Middleware] --> [User Service] --> [Code Repository] --> [PostgreSQL]
                                │                     │
                                │                     └-> [User Repository] --> [Update Status]
                                │
                                └-> [Response Schema]
```

## Key Architectural Decisions

### 1. **Domain-Driven Design (DDD) inspiration withoup application layer**
- **Entities**: User, ActivationCode with rich domain behavior
- **Services**: Business logic encapsulation
- **Repositories**: Data access abstraction
- **Exceptions**: Domain-specific error handling

### 2. **No ORM Usage**
- Raw SQL with asyncpg for optimal performance
- Explicit query control and optimization
- Direct mapping between domain entities and database rows
- Connection pooling for scalability

### 3. **Asynchronous Message Processing**
- RabbitMQ for email sending decoupling
- Separate consumer processes for horizontal scaling
- Fault tolerance with message acknowledgments
- Dead letter queues for error handling

### 4. **Clean Error Handling**
- Structured error responses following NBK patterns
- Hierarchical exception classes
- Consistent error codes and messages
- Security-conscious error disclosure

### 5. **Security by Design**
- bcrypt password hashing (12 rounds)
- Basic Authentication for activation
- Input validation at multiple layers
- SQL injection prevention via parameterized queries

## Data Flow

### Registration Process
1. **API Layer**: Validates request schema (email format, password strength)
2. **Service Layer**: Applies business rules, checks duplicates
3. **Repository Layer**: Persists user with PENDING status
4. **Email Service**: Generates 4-digit code, queues email message
5. **Consumer**: Processes email queue, sends notification

### Activation Process
1. **Auth Layer**: Validates Basic Auth credentials
2. **Service Layer**: Authenticates user, validates activation code
3. **Repository Layer**: Updates user status to ACTIVE, marks code as used
4. **Response**: Returns activated user details

## Scalability Considerations

### Horizontal Scaling
- **Stateless Application**: No server-side sessions
- **Database Connection Pooling**: Efficient connection reuse
- **Message Queue**: Async processing isolation
- **Container Ready**: Docker for easy deployment

### Performance Optimizations
- **Async/Await**: Non-blocking I/O operations
- **Database Indexes**: Optimized query performance
- **Connection Pooling**: Resource efficiency
- **Raw SQL**: No ORM overhead

## Deployment Architecture

### Development
```
[Docker Compose]
├── App Container (FastAPI)
├── PostgreSQL Container
├── RabbitMQ Container
└── MailHog Container (Email Testing)
```

This architecture provides a solid foundation for a production-ready user registration system with clear separation of concerns, excellent testability, and horizontal scaling capabilities.