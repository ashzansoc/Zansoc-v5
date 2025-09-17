"""Database management for ZanSoc CLI."""

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .utils.logger import get_logger


class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: str):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.logger = get_logger(__name__)
        
        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create providers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS providers (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    status TEXT DEFAULT 'registering',
                    created_at TEXT NOT NULL,
                    tailscale_ip TEXT,
                    ray_node_id TEXT,
                    platform TEXT,
                    last_seen TEXT
                )
            """)
            
            # Create onboarding_sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_sessions (
                    session_id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    current_step TEXT NOT NULL,
                    completed_steps TEXT DEFAULT '',
                    failed_steps TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (provider_id) REFERENCES providers (id)
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_providers_username 
                ON providers (username)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_providers_status 
                ON providers (status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_provider 
                ON onboarding_sessions (provider_id)
            """)
            
            conn.commit()
            self.logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def get_provider_by_id(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get provider by ID.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Provider data or None if not found
        """
        results = self.execute_query(
            "SELECT * FROM providers WHERE id = ?",
            (provider_id,)
        )
        return results[0] if results else None
    
    def get_provider_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get provider by username.
        
        Args:
            username: Username
            
        Returns:
            Provider data or None if not found
        """
        results = self.execute_query(
            "SELECT * FROM providers WHERE username = ?",
            (username,)
        )
        return results[0] if results else None
    
    def insert_provider(self, provider_data: Dict[str, Any]) -> bool:
        """Insert new provider.
        
        Args:
            provider_data: Provider data dictionary
            
        Returns:
            True if successful
        """
        try:
            self.execute_update("""
                INSERT INTO providers 
                (id, username, status, created_at, tailscale_ip, ray_node_id, platform, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                provider_data['id'],
                provider_data['username'],
                provider_data['status'],
                provider_data['created_at'],
                provider_data.get('tailscale_ip'),
                provider_data.get('ray_node_id'),
                provider_data.get('platform'),
                provider_data.get('last_seen'),
            ))
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert provider: {e}")
            return False
    
    def update_provider(self, provider_id: str, updates: Dict[str, Any]) -> bool:
        """Update provider data.
        
        Args:
            provider_id: Provider ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        if not updates:
            return True
        
        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        
        for field, value in updates.items():
            if field != 'id':  # Don't allow ID updates
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return True
        
        params.append(provider_id)
        query = f"UPDATE providers SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            rows_affected = self.execute_update(query, tuple(params))
            return rows_affected > 0
        except Exception as e:
            self.logger.error(f"Failed to update provider {provider_id}: {e}")
            return False
    
    def get_session_by_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get onboarding session by provider ID.
        
        Args:
            provider_id: Provider ID
            
        Returns:
            Session data or None if not found
        """
        results = self.execute_query(
            "SELECT * FROM onboarding_sessions WHERE provider_id = ? ORDER BY created_at DESC LIMIT 1",
            (provider_id,)
        )
        return results[0] if results else None
    
    def insert_session(self, session_data: Dict[str, Any]) -> bool:
        """Insert new onboarding session.
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            True if successful
        """
        try:
            self.execute_update("""
                INSERT INTO onboarding_sessions 
                (session_id, provider_id, current_step, completed_steps, failed_steps, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data['session_id'],
                session_data['provider_id'],
                session_data['current_step'],
                session_data['completed_steps'],
                session_data['failed_steps'],
                session_data['created_at'],
                session_data['updated_at'],
            ))
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert session: {e}")
            return False
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update onboarding session.
        
        Args:
            session_id: Session ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        if not updates:
            return True
        
        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        
        for field, value in updates.items():
            if field != 'session_id':  # Don't allow session_id updates
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return True
        
        params.append(session_id)
        query = f"UPDATE onboarding_sessions SET {', '.join(set_clauses)} WHERE session_id = ?"
        
        try:
            rows_affected = self.execute_update(query, tuple(params))
            return rows_affected > 0
        except Exception as e:
            self.logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """Get all providers.
        
        Returns:
            List of provider data dictionaries
        """
        return self.execute_query("SELECT * FROM providers ORDER BY created_at DESC")
    
    def get_providers_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get providers by status.
        
        Args:
            status: Provider status
            
        Returns:
            List of provider data dictionaries
        """
        return self.execute_query(
            "SELECT * FROM providers WHERE status = ? ORDER BY created_at DESC",
            (status,)
        )
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up old onboarding sessions.
        
        Args:
            days: Number of days to keep sessions
            
        Returns:
            Number of sessions deleted
        """
        try:
            return self.execute_update("""
                DELETE FROM onboarding_sessions 
                WHERE datetime(created_at) < datetime('now', '-{} days')
            """.format(days))
        except Exception as e:
            self.logger.error(f"Failed to cleanup old sessions: {e}")
            return 0