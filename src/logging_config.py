# logging_config.py
# Centralized logging configuration for FuDog Labs Forensic Report Suite
# Provides consistent logging across all modules with rotation and formatting

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class LogConfig:
    """Configuration constants for logging"""
    
    # Log levels
    CONSOLE_LEVEL = logging.INFO
    FILE_LEVEL = logging.DEBUG
    
    # Log rotation (10MB files, keep 5 backups)
    MAX_BYTES = 10_000_000  # 10MB
    BACKUP_COUNT = 5
    
    # Log format
    DETAILED_FORMAT = "%(asctime)s [%(name)s] %(levelname)s [%(filename)s:%(lineno)d]: %(message)s"
    SIMPLE_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_log_directory(app_name: str = "forensic_app") -> Path:
    """
    Get or create application log directory.
    
    Args:
        app_name: Name of application (used in path)
    
    Returns:
        Path object for log directory
    """
    log_dir = Path.home() / ".forensic_app" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    app_name: str = "forensic_app",
    log_dir: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure application-wide logging with file rotation and console output.
    
    This function should be called once at application startup.
    
    Args:
        app_name: Name of application (default "forensic_app")
        log_dir: Directory for log files (default ~/.forensic_app/logs)
        console_level: Logging level for console output (default INFO)
        file_level: Logging level for file output (default DEBUG)
        log_file: Name of log file (default app_name.log)
    
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = setup_logging("forensic_app")
        >>> logger.info("Application started")
        >>> logger.error("An error occurred")
    """
    if log_dir is None:
        log_dir = get_log_directory(app_name)
    
    if log_file is None:
        log_file = f"{app_name}.log"
    
    # Get or create logger
    logger = logging.getLogger(app_name)
    
    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)  # Set root level to DEBUG, handlers will filter
    
    # ========== Console Handler (INFO and above) ==========
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        LogConfig.SIMPLE_FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # ========== File Handler (DEBUG and above with rotation) ==========
    log_file_path = log_dir / log_file
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file_path),
        maxBytes=LogConfig.MAX_BYTES,
        backupCount=LogConfig.BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(
        LogConfig.DETAILED_FORMAT,
        datefmt=LogConfig.DATE_FORMAT
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging initialized: {app_name}")
    logger.info(f"Log file: {log_file_path}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger (for use in modules).
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Named logger instance
    
    Example:
        # In any module
        logger = get_logger(__name__)
        logger.info("Message from module")
    """
    return logging.getLogger(name)


def configure_module_logging(module_name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure logging for a specific module.
    
    Args:
        module_name: Name of module (typically __name__)
        level: Logging level for this module
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(level)
    return logger


def get_active_handlers(logger: Optional[logging.Logger] = None) -> list[str]:
    """
    Get list of active handlers for a logger.
    
    Args:
        logger: Logger to check (default root logger)
    
    Returns:
        List of handler class names
    """
    if logger is None:
        logger = logging.getLogger()
    
    return [handler.__class__.__name__ for handler in logger.handlers]


def cleanup_logging(logger: Optional[logging.Logger] = None) -> None:
    """
    Cleanup logging handlers (useful for graceful shutdown).
    
    Args:
        logger: Logger to cleanup (default root logger)
    """
    if logger is None:
        logger = logging.getLogger()
    
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


# ============================================================================
# Context Manager for Temporary Logging Level
# ============================================================================

class temporary_logging_level:
    """
    Context manager to temporarily change logging level.
    
    Usage:
        >>> logger = get_logger(__name__)
        >>> with temporary_logging_level(logger, logging.DEBUG):
        ...     logger.debug("This will be logged")
        >>> logger.debug("This won't be logged if logger is INFO level")
    """
    
    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.previous_level = logger.level
        self.new_level = level
    
    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.previous_level)
        return False


# ============================================================================
# Error Logging Helper
# ============================================================================

def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: dict = None,
    level: int = logging.ERROR
) -> None:
    """
    Log an exception with additional context information.
    
    Args:
        logger: Logger instance
        error: Exception to log
        context: Dictionary of context variables to include
        level: Logging level (default ERROR)
    
    Example:
        >>> try:
        ...     result = dangerous_operation()
        ... except Exception as e:
        ...     log_error_with_context(logger, e, {'operation': 'load_report', 'case_id': '123'})
    """
    context_str = ""
    if context:
        context_str = " | Context: " + ", ".join(f"{k}={v}" for k, v in context.items())
    
    logger.log(
        level,
        f"{error.__class__.__name__}: {error}{context_str}",
        exc_info=True  # Includes traceback
    )


# ============================================================================
# Performance Logging Helper
# ============================================================================

class LogExecutionTime:
    """
    Context manager to log execution time of operations.
    
    Usage:
        >>> logger = get_logger(__name__)
        >>> with LogExecutionTime(logger, "Report export"):
        ...     export_report(case_id)
    """
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation} ({elapsed:.2f}s)")
        else:
            self.logger.error(f"Failed: {self.operation} ({elapsed:.2f}s) - {exc_type.__name__}")
        
        return False


# ============================================================================
# Performance Baseline Logging
# ============================================================================

def log_performance_baseline(logger: logging.Logger) -> dict:
    """
    Log system performance baseline metrics.
    Called at application startup to record system state.
    
    Args:
        logger: Logger instance
    
    Returns:
        Dictionary of baseline metrics
    """
    try:
        import psutil
        
        process = psutil.Process()
        baseline = {
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0,
                msg='', args=(), exc_info=None
            )),
            'memory_rss_mb': round(process.memory_info().rss / (1024**2), 2),
            'memory_vms_mb': round(process.memory_info().vms / (1024**2), 2),
            'cpu_count_logical': psutil.cpu_count(logical=True),
            'cpu_count_physical': psutil.cpu_count(logical=False),
            'ram_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'ram_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
        }
        
        logger.info(
            f"Performance baseline: "
            f"Memory={baseline['memory_rss_mb']}MB, "
            f"Available RAM={baseline['ram_available_gb']}GB, "
            f"CPUs={baseline['cpu_count_logical']}"
        )
        
        return baseline
    
    except ImportError:
        logger.warning("psutil not available for performance metrics")
        return {}
    except Exception as e:
        logger.error(f"Failed to log performance baseline: {e}")
        return {}


class PerformanceMonitor:
    """
    Monitor application performance over time.
    Tracks memory usage, execution times, and other metrics.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.metrics = {}
    
    def record_metric(self, name: str, value: float, unit: str = ""):
        """Record a performance metric."""
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            'value': value,
            'unit': unit,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0,
                msg='', args=(), exc_info=None
            ))
        })
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            return round(psutil.Process().memory_info().rss / (1024**2), 2)
        except Exception:
            return 0.0
    
    def log_memory_snapshot(self, label: str = ""):
        """Log current memory usage."""
        mem = self.get_memory_usage_mb()
        self.logger.debug(f"Memory snapshot {label}: {mem}MB")
        self.record_metric('memory_mb', mem, 'MB')
        return mem
    
    def get_summary(self) -> dict:
        """Get summary of recorded metrics."""
        summary = {}
        for name, values in self.metrics.items():
            if values:
                nums = [v['value'] for v in values]
                summary[name] = {
                    'count': len(nums),
                    'min': min(nums),
                    'max': max(nums),
                    'avg': round(sum(nums) / len(nums), 2),
                }
        return summary
    
    def log_summary(self):
        """Log summary of all metrics."""
        summary = self.get_summary()
        if summary:
            self.logger.info("Performance summary: " + str(summary))
        else:
            self.logger.debug("No performance metrics recorded")


# ============================================================================
# Module-level initialization
# ============================================================================

# Initialize root logger when module is imported
try:
    _root_logger = setup_logging()
except Exception as e:
    print(f"Warning: Failed to initialize logging: {e}")
    _root_logger = logging.getLogger()
