import os
from typing import Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Dailymotion User Registration API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    db_host: str = Field(default="localhost", alias="DATABASE_HOST")
    db_port: int = Field(default=5432, alias="DATABASE_PORT")
    db_name: str = Field(default="dailymotion_users", alias="DATABASE_NAME")
    db_user: str = Field(default="postgres", alias="DATABASE_USER")
    db_password: str = Field(default="postgres", alias="DATABASE_PASSWORD")
    db_min_connections: int = 10
    db_max_connections: int = 20
    
    # RabbitMQ
    rabbitmq_host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="guest", alias="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = "/"
    
    # Email Service
    email_queue_name: str = "email_notifications"
    email_service_url: str = Field(default="http://localhost:8080/send-email", alias="EMAIL_SERVICE_URL")
    
    # Security
    password_hash_rounds: int = 12
    
    # JWT for Basic Auth (optional enhancement)
    secret_key: str = Field(default="dailymotion-secret-key-change-in-production", alias="SECRET_KEY")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
        env_prefix="",  # No prefix for environment variables
    )
    
    @field_validator('db_min_connections')
    @classmethod
    def validate_min_connections(cls, v):
        if v < 1:
            raise ValueError('Minimum connections must be at least 1')
        return v
    
    @field_validator('db_max_connections')
    @classmethod
    def validate_max_connections(cls, v, info):
        if 'db_min_connections' in info.data and v < info.data['db_min_connections']:
            raise ValueError('Maximum connections must be greater than or equal to minimum connections')
        return v


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get PostgreSQL database URL."""
    return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"


def get_rabbitmq_url() -> str:
    """Get RabbitMQ connection URL."""
    return f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}{settings.rabbitmq_vhost}"