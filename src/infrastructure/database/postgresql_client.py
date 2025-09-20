import asyncpg
import logging
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from src.domain.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class PostgreSQLClient:
    """PostgreSQL client for managing database connections."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        min_connections: int = 10,
        max_connections: int = 20
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=30,
                server_settings={
                    'timezone': 'UTC'
                }
            )
            logger.info("PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {str(e)}")
            raise DatabaseException(f"Failed to connect to PostgreSQL: {str(e)}")

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool with context manager."""
        if not self.pool:
            raise DatabaseException("Database pool not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation failed: {str(e)}")
                raise DatabaseException(f"Database operation failed: {str(e)}")

    async def execute_query(
        self,
        query: str,
        *args,
        fetch: str = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute SQL query.
        
        Args:
            query: SQL query string
            *args: Query parameters
            fetch: 'all', 'one', 'val', or None for non-select queries
            
        Returns:
            Query result based on fetch type
        """
        async with self.get_connection() as conn:
            try:
                if fetch == 'all':
                    result = await conn.fetch(query, *args)
                    return [dict(record) for record in result]
                elif fetch == 'one':
                    result = await conn.fetchrow(query, *args)
                    return dict(result) if result else None
                elif fetch == 'val':
                    return await conn.fetchval(query, *args)
                else:
                    # Execute without fetching (INSERT, UPDATE, DELETE)
                    return await conn.execute(query, *args)
            except Exception as e:
                logger.error(f"Query execution failed: {query} - {str(e)}")
                raise DatabaseException(f"Query execution failed: {str(e)}")

    async def execute_transaction(self, queries: List[tuple]) -> None:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (query, args) tuples
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                try:
                    for query, args in queries:
                        await conn.execute(query, *args)
                except Exception as e:
                    logger.error(f"Transaction failed: {str(e)}")
                    raise DatabaseException(f"Transaction failed: {str(e)}")

    async def create_tables(self):
        """Create database tables if they don't exist."""
        
        # Users table
        users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            activated_at TIMESTAMP WITH TIME ZONE NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
        """

        # Activation codes table
        activation_codes_table = """
        CREATE TABLE IF NOT EXISTS activation_codes (
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            code VARCHAR(4) NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            used_at TIMESTAMP WITH TIME ZONE NULL,
            is_used BOOLEAN DEFAULT FALSE,
            PRIMARY KEY (user_id, code)
        );
        
        CREATE INDEX IF NOT EXISTS idx_activation_codes_expires_at ON activation_codes(expires_at);
        CREATE INDEX IF NOT EXISTS idx_activation_codes_is_used ON activation_codes(is_used);
        """

        try:
            await self.execute_query(users_table)
            await self.execute_query(activation_codes_table)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise DatabaseException(f"Failed to create tables: {str(e)}")

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            result = await self.execute_query("SELECT 1", fetch='val')
            return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False