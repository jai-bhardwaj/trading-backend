"""
Database Security Manager

This module provides secure database operations with:
- Parameterized queries to prevent SQL injection
- Connection pool security
- Query validation and sanitization
- Database access logging and monitoring
- Connection encryption and authentication
"""

import asyncio
import asyncpg
import logging
import hashlib
import time
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager
import threading
import ssl
import os

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Secure database configuration"""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_min_size: int = 5
    pool_max_size: int = 20
    ssl_mode: str = "require"
    command_timeout: int = 30
    query_timeout: int = 60
    max_cached_statement_lifetime: int = 300
    enable_query_logging: bool = True
    enable_slow_query_logging: bool = True
    slow_query_threshold: float = 1.0

class QueryValidator:
    """Query validation and SQL injection prevention"""
    
    # Dangerous SQL patterns that should never appear in user input
    DANGEROUS_PATTERNS = [
        # SQL injection patterns
        r"(\bor\b|\band\b)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?",
        r"union\s+select",
        r"insert\s+into",
        r"delete\s+from",
        r"drop\s+(table|database|schema)",
        r"alter\s+table",
        r"create\s+(table|database|schema)",
        r"truncate\s+table",
        r"exec(\s|\+)+(s|x)p\w+",
        r"sp_\w+",
        r"xp_\w+",
        r"--\s*$",
        r"/\*.*\*/",
        r";\s*(drop|delete|insert|update|create|alter|exec)",
        
        # Command injection patterns  
        r"[;&|`]",
        r"\$\(\s*.*\s*\)",
        r"`.*`",
        
        # Script injection patterns
        r"<\s*script",
        r"javascript\s*:",
        r"vbscript\s*:",
        r"eval\s*\(",
        r"expression\s*\(",
    ]
    
    @staticmethod
    def validate_query_parameters(params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate query parameters for potential injection attacks
        
        Args:
            params: Dictionary of query parameters
            
        Returns:
            (is_safe, error_message)
        """
        if not isinstance(params, dict):
            return False, "Parameters must be a dictionary"
        
        for key, value in params.items():
            # Validate parameter key
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                return False, f"Invalid parameter name: {key}"
            
            # Check parameter value for dangerous patterns
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in QueryValidator.DANGEROUS_PATTERNS:
                    if re.search(pattern, value_lower, re.IGNORECASE | re.MULTILINE):
                        logger.warning(f"Potential SQL injection detected in parameter '{key}': {pattern}")
                        return False, f"Dangerous pattern detected in parameter '{key}'"
        
        return True, ""
    
    @staticmethod
    def validate_table_name(table_name: str) -> Tuple[bool, str]:
        """
        Validate table name to prevent injection
        
        Args:
            table_name: Name of the table
            
        Returns:
            (is_valid, error_message)
        """
        if not table_name:
            return False, "Table name cannot be empty"
        
        # Table names should only contain letters, numbers, underscores
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            return False, f"Invalid table name format: {table_name}"
        
        # Check against dangerous patterns
        table_lower = table_name.lower()
        for pattern in QueryValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, table_lower, re.IGNORECASE):
                return False, f"Dangerous pattern in table name: {table_name}"
        
        return True, ""
    
    @staticmethod
    def validate_column_names(columns: List[str]) -> Tuple[bool, str]:
        """
        Validate column names to prevent injection
        
        Args:
            columns: List of column names
            
        Returns:
            (is_valid, error_message)
        """
        if not columns:
            return False, "Column list cannot be empty"
        
        for col in columns:
            if not isinstance(col, str):
                return False, f"Column name must be string: {col}"
            
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                return False, f"Invalid column name format: {col}"
        
        return True, ""

class SecureDatabaseManager:
    """
    Secure database manager with SQL injection prevention
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        self.query_validator = QueryValidator()
        self._lock = threading.Lock()
        self._query_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'blocked_queries': 0,
            'slow_queries': 0
        }
        
        # SSL context for secure connections
        self.ssl_context = self._create_ssl_context()
        
        logger.info("🔒 Secure Database Manager initialized")
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for secure database connections"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        if self.config.ssl_mode == "require":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        elif self.config.ssl_mode == "verify-ca":
            context.verify_mode = ssl.CERT_REQUIRED
        elif self.config.ssl_mode == "verify-full":
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = True
        
        return context
    
    async def connect(self) -> bool:
        """
        Establish secure database connection pool
        
        Returns:
            True if connection successful
        """
        try:
            # Build connection string with security parameters
            connection_params = {
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database,
                'user': self.config.username,
                'password': self.config.password,
                'ssl': self.ssl_context,
                'command_timeout': self.config.command_timeout,
                'min_size': self.config.pool_min_size,
                'max_size': self.config.pool_max_size,
                'max_cached_statement_lifetime': self.config.max_cached_statement_lifetime
            }
            
            logger.info(f"🔗 Connecting to database: {self.config.host}:{self.config.port}/{self.config.database}")
            
            self.pool = await asyncpg.create_pool(**connection_params)
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            logger.info("✅ Secure database connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("🔒 Database connection closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            raise Exception("Database not connected")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute parameterized query safely
        
        Args:
            query: SQL query with parameter placeholders ($1, $2, etc.)
            params: Dictionary of parameters
            
        Returns:
            List of result rows as dictionaries
        """
        start_time = time.time()
        params = params or {}
        
        try:
            # Validate parameters
            is_safe, error_msg = self.query_validator.validate_query_parameters(params)
            if not is_safe:
                self._query_stats['blocked_queries'] += 1
                logger.warning(f"🚫 Query blocked due to security validation: {error_msg}")
                raise ValueError(f"Query validation failed: {error_msg}")
            
            # Convert dict params to list for asyncpg
            param_values = list(params.values()) if params else []
            
            async with self.get_connection() as conn:
                # Execute query with parameters
                rows = await conn.fetch(query, *param_values)
                
                # Convert to list of dictionaries
                result = [dict(row) for row in rows]
                
                execution_time = time.time() - start_time
                
                # Update statistics
                self._query_stats['total_queries'] += 1
                self._query_stats['successful_queries'] += 1
                
                # Log slow queries
                if execution_time > self.config.slow_query_threshold:
                    self._query_stats['slow_queries'] += 1
                    if self.config.enable_slow_query_logging:
                        logger.warning(f"🐌 Slow query ({execution_time:.2f}s): {query[:100]}...")
                
                # Log query if enabled
                if self.config.enable_query_logging:
                    logger.debug(f"📝 Query executed ({execution_time:.3f}s): {query[:100]}...")
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._query_stats['total_queries'] += 1
            self._query_stats['failed_queries'] += 1
            
            logger.error(f"❌ Query execution failed ({execution_time:.3f}s): {e}")
            logger.error(f"   Query: {query[:200]}...")
            raise e
    
    async def execute_insert(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Safely insert data into table
        
        Args:
            table: Table name
            data: Dictionary of column: value pairs
            
        Returns:
            ID of inserted row (if applicable)
        """
        # Validate table name
        is_valid, error_msg = self.query_validator.validate_table_name(table)
        if not is_valid:
            raise ValueError(f"Invalid table name: {error_msg}")
        
        # Validate data
        is_safe, error_msg = self.query_validator.validate_query_parameters(data)
        if not is_safe:
            raise ValueError(f"Invalid insert data: {error_msg}")
        
        # Build parameterized insert query
        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """
        
        try:
            result = await self.execute_query(query, data)
            return result[0]['id'] if result else None
        except Exception as e:
            logger.error(f"❌ Insert failed for table {table}: {e}")
            raise e
    
    async def execute_update(self, table: str, data: Dict[str, Any], 
                           where_conditions: Dict[str, Any]) -> int:
        """
        Safely update data in table
        
        Args:
            table: Table name
            data: Dictionary of column: value pairs to update
            where_conditions: Dictionary of WHERE conditions
            
        Returns:
            Number of rows affected
        """
        # Validate table name
        is_valid, error_msg = self.query_validator.validate_table_name(table)
        if not is_valid:
            raise ValueError(f"Invalid table name: {error_msg}")
        
        # Combine and validate all parameters
        all_params = {**data, **where_conditions}
        is_safe, error_msg = self.query_validator.validate_query_parameters(all_params)
        if not is_safe:
            raise ValueError(f"Invalid update parameters: {error_msg}")
        
        # Build parameterized update query
        set_clauses = []
        param_index = 1
        
        for col in data.keys():
            set_clauses.append(f"{col} = ${param_index}")
            param_index += 1
        
        where_clauses = []
        for col in where_conditions.keys():
            where_clauses.append(f"{col} = ${param_index}")
            param_index += 1
        
        query = f"""
            UPDATE {table}
            SET {', '.join(set_clauses)}
            WHERE {' AND '.join(where_clauses)}
        """
        
        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query, *all_params.values())
                
                # Extract number of affected rows
                affected_rows = int(result.split()[-1])
                
                logger.debug(f"📝 Updated {affected_rows} rows in {table}")
                return affected_rows
                
        except Exception as e:
            logger.error(f"❌ Update failed for table {table}: {e}")
            raise e
    
    async def execute_select(self, table: str, columns: List[str] = None,
                           where_conditions: Dict[str, Any] = None,
                           order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Safely select data from table
        
        Args:
            table: Table name
            columns: List of columns to select (None for all)
            where_conditions: Dictionary of WHERE conditions
            order_by: ORDER BY clause
            limit: LIMIT clause
            
        Returns:
            List of result rows
        """
        # Validate table name
        is_valid, error_msg = self.query_validator.validate_table_name(table)
        if not is_valid:
            raise ValueError(f"Invalid table name: {error_msg}")
        
        # Validate columns
        if columns:
            is_valid, error_msg = self.query_validator.validate_column_names(columns)
            if not is_valid:
                raise ValueError(f"Invalid column names: {error_msg}")
        
        # Validate where conditions
        where_conditions = where_conditions or {}
        is_safe, error_msg = self.query_validator.validate_query_parameters(where_conditions)
        if not is_safe:
            raise ValueError(f"Invalid where conditions: {error_msg}")
        
        # Build query
        column_list = ', '.join(columns) if columns else '*'
        query = f"SELECT {column_list} FROM {table}"
        
        params = {}
        if where_conditions:
            where_clauses = []
            for i, (col, value) in enumerate(where_conditions.items(), 1):
                where_clauses.append(f"{col} = ${i}")
                params[f"param_{i}"] = value
            
            query += f" WHERE {' AND '.join(where_clauses)}"
        
        if order_by:
            # Validate order_by clause
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\s+(ASC|DESC))?$', order_by.strip()):
                raise ValueError(f"Invalid ORDER BY clause: {order_by}")
            query += f" ORDER BY {order_by}"
        
        if limit:
            if not isinstance(limit, int) or limit <= 0:
                raise ValueError(f"Invalid LIMIT value: {limit}")
            query += f" LIMIT {limit}"
        
        return await self.execute_query(query, params)
    
    async def execute_delete(self, table: str, where_conditions: Dict[str, Any]) -> int:
        """
        Safely delete data from table
        
        Args:
            table: Table name
            where_conditions: Dictionary of WHERE conditions (required)
            
        Returns:
            Number of rows deleted
        """
        if not where_conditions:
            raise ValueError("DELETE requires WHERE conditions for safety")
        
        # Validate table name
        is_valid, error_msg = self.query_validator.validate_table_name(table)
        if not is_valid:
            raise ValueError(f"Invalid table name: {error_msg}")
        
        # Validate where conditions
        is_safe, error_msg = self.query_validator.validate_query_parameters(where_conditions)
        if not is_safe:
            raise ValueError(f"Invalid where conditions: {error_msg}")
        
        # Build parameterized delete query
        where_clauses = []
        for i, col in enumerate(where_conditions.keys(), 1):
            where_clauses.append(f"{col} = ${i}")
        
        query = f"""
            DELETE FROM {table}
            WHERE {' AND '.join(where_clauses)}
        """
        
        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query, *where_conditions.values())
                
                # Extract number of affected rows
                deleted_rows = int(result.split()[-1])
                
                logger.info(f"🗑️ Deleted {deleted_rows} rows from {table}")
                return deleted_rows
                
        except Exception as e:
            logger.error(f"❌ Delete failed for table {table}: {e}")
            raise e
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get database query statistics"""
        with self._lock:
            total = self._query_stats['total_queries']
            if total == 0:
                success_rate = 0
            else:
                success_rate = (self._query_stats['successful_queries'] / total) * 100
            
            return {
                **self._query_stats,
                'success_rate': success_rate,
                'pool_size': self.pool.get_size() if self.pool else 0,
                'pool_max_size': self.config.pool_max_size,
                'ssl_enabled': self.config.ssl_mode != "disable"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            start_time = time.time()
            
            async with self.get_connection() as conn:
                await conn.execute("SELECT 1")
            
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time * 1000,
                'pool_stats': {
                    'size': self.pool.get_size(),
                    'max_size': self.config.pool_max_size,
                    'idle_connections': self.pool.get_idle_size()
                },
                'ssl_enabled': self.config.ssl_mode != "disable"
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'ssl_enabled': self.config.ssl_mode != "disable"
            }

# Global secure database manager instance
_global_db_manager: Optional[SecureDatabaseManager] = None
_db_lock = threading.Lock()

def get_secure_db_manager() -> Optional[SecureDatabaseManager]:
    """Get global secure database manager instance"""
    global _global_db_manager
    return _global_db_manager

def initialize_secure_database(config: DatabaseConfig) -> SecureDatabaseManager:
    """Initialize global secure database manager"""
    global _global_db_manager
    
    with _db_lock:
        _global_db_manager = SecureDatabaseManager(config)
    
    return _global_db_manager 