"""Logging configuration for NS Lookup MCP Server."""

import logging
import os
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging() -> logging.Logger:
    """Set up logging configuration.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path.home() / ".mcp" / "data"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate log filename with project name, timestamp and PID
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    pid = os.getpid()
    log_file = log_dir / f"ns-lookup-mcp-{timestamp}-{pid}.log"
    
    # Create logger
    logger = logging.getLogger("ns_lookup_mcp")
    logger.setLevel(logging.INFO)
    
    # Create formatter with process info
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - PID:%(process)d - %(levelname)s - %(message)s'
    )
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024*1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    # Log startup information
    logger.info(f"Starting NS Lookup MCP server (PID: {pid})")
    
    return logger 