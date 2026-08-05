import os
import shutil
from datetime import datetime
from bot.config.settings import settings
from bot.utils.logger import logger

async def backup_database() -> str:
    os.makedirs("backups", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/quizbot_backup_{timestamp}.db"

    if settings.DATABASE_URL.startswith("sqlite"):
        db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_file)
            logger.info(f"SQLite backup created at {backup_file}")
            return backup_file

    logger.info(f"Backup requested for database: {settings.DATABASE_URL}")
    return backup_file
