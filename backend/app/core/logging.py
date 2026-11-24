import logging
import sys
from app.core.config import settings


def setup_logging():
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging_format = (
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=logging_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Suppress excessive logging from lower-level libraries
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)

    logger = logging.getLogger("pharmarca")
    logger.info(f"Initialized PharmaRCA structured logging (Level: {logging.getLevelName(log_level)})")
    return logger


logger = setup_logging()
