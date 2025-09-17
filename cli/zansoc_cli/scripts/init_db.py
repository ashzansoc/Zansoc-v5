"""Database initialization script."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database import DatabaseManager
from config_manager import ConfigManager
from utils.logger import setup_logging, get_logger


def main():
    """Initialize the database with required tables."""
    # Setup logging
    setup_logging("INFO")
    logger = get_logger(__name__)
    
    try:
        # Load configuration
        config = ConfigManager()
        
        # Get database path
        db_path = config.get_database_path()
        
        logger.info(f"Initializing database at: {db_path}")
        
        # Initialize database
        db = DatabaseManager(str(db_path))
        
        logger.info("Database initialization completed successfully!")
        
        # Display some stats
        providers = db.get_all_providers()
        sessions = db.execute_query("SELECT COUNT(*) as count FROM onboarding_sessions")
        
        logger.info(f"Current database stats:")
        logger.info(f"  - Providers: {len(providers)}")
        logger.info(f"  - Sessions: {sessions[0]['count'] if sessions else 0}")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()