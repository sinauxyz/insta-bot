import logging
from functools import wraps

# Definisi logger global di tingkat modul
logger = logging.getLogger(__name__)

def setup_logging(level: int = logging.INFO):
    """Mengatur logging dengan tingkat yang ditentukan."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level
    )
    return logger

def log_errors(logger_instance):
    """Dekorator untuk mencatat error pada fungsi."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger_instance.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise
        return wrapper
    return decorator