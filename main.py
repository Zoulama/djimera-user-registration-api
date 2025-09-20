import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from config import settings, get_rabbitmq_url
from src.infrastructure.database.postgresql_client import PostgreSQLClient
from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from src.infrastructure.email.email_service import EmailService
from src.domain.user.repository import UserRepository, ActivationCodeRepository
from src.domain.user.service import UserService
from src.api.v1 import users
from src.domain.exceptions import (
    BaseServiceException,
    service_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global service instances
db_client: PostgreSQLClient = None
rabbitmq_client: RabbitMQClient = None
email_service: EmailService = None
user_service: UserService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()


async def startup_event():
    """Initialize services on startup."""
    global db_client, rabbitmq_client, email_service, user_service
    
    logger.info("Starting Dailymotion User Registration API...")
    
    try:
        # Initialize PostgreSQL client
        db_client = PostgreSQLClient(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            username=settings.db_user,
            password=settings.db_password,
            min_connections=settings.db_min_connections,
            max_connections=settings.db_max_connections
        )
        await db_client.connect()
        await db_client.create_tables()
        
        # Initialize RabbitMQ client
        rabbitmq_client = RabbitMQClient(get_rabbitmq_url())
        await rabbitmq_client.connect()
        
        # Initialize email service
        email_service = EmailService(
            rabbitmq_client=rabbitmq_client,
            email_service_url=settings.email_service_url,
            queue_name=settings.email_queue_name
        )
        
        # Start email consumer in background
        asyncio.create_task(email_service.start_email_consumer())
        
        # Initialize repositories
        user_repository = UserRepository(db_client)
        activation_code_repository = ActivationCodeRepository(db_client)
        
        # Initialize user service
        user_service = UserService(
            user_repository=user_repository,
            activation_code_repository=activation_code_repository,
            email_service=email_service
        )
        
        # Set up dependency injection for routes
        users.user_service = user_service
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise


async def shutdown_event():
    """Clean up resources on shutdown."""
    global db_client, rabbitmq_client
    
    logger.info("Shutting down services...")
    
    try:
        if db_client:
            await db_client.disconnect()
        if rabbitmq_client:
            await rabbitmq_client.disconnect()
        logger.info("All services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## User Registration API

    A production-ready user registration system with email activation.

    ### Features
    - User registration with email and password
    - Email activation with 4-digit codes
    - Activation codes expire in 1 minute
    - Request-based authentication for activation
    - Asynchronous email processing via RabbitMQ
    - PostgreSQL storage without ORM
    - Comprehensive error handling
    - Health checks

    ### Workflow
    1. **Register**: POST `/api/v1/users/register` with email and password
    2. **Check Email**: Look for 4-digit activation code in email/console
    3. **Activate**: POST `/api/v1/users/activate` with email, password, and activation code in request body
    4. **Optional**: POST `/api/v1/users/resend-activation` to get a new code (still uses Basic Auth)
    """,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://dailymotion.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(BaseServiceException, service_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(users.router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs",
        "endpoints": {
            "register": "POST /api/v1/users/register",
            "activate": "POST /api/v1/users/activate",
            "resend": "POST /api/v1/users/resend-activation",
            "health": "GET /api/v1/users/health"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Application health check."""
    health_status = {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "components": {}
    }
    
    # Check database health
    if db_client:
        db_healthy = await db_client.health_check()
        health_status["components"]["database"] = "healthy" if db_healthy else "unhealthy"
    else:
        health_status["components"]["database"] = "not_initialized"
    
    # Check RabbitMQ health
    if rabbitmq_client:
        rabbitmq_healthy = await rabbitmq_client.health_check()
        health_status["components"]["rabbitmq"] = "healthy" if rabbitmq_healthy else "unhealthy"
    else:
        health_status["components"]["rabbitmq"] = "not_initialized"
    
    # Check email service health
    if email_service:
        email_healthy = await email_service.health_check()
        health_status["components"]["email_service"] = "healthy" if email_healthy else "unhealthy"
    else:
        health_status["components"]["email_service"] = "not_initialized"
    
    # Overall health status
    component_statuses = list(health_status["components"].values())
    if all(status == "healthy" for status in component_statuses):
        health_status["status"] = "healthy"
    elif any(status == "unhealthy" for status in component_statuses):
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "starting"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )