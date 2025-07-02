"""Logging configuration for the VidView application.

This module sets up the logging system for the application, with appropriate
log levels and handlers. By default, only warnings and errors are displayed
in the console, but debug and info messages can be enabled by setting the
DEBUG environment variable.
"""

import logging
import os
import sys

# Create a logger for the application
logger = logging.getLogger("vidview")

# Set the default log level
DEFAULT_LOG_LEVEL = logging.WARNING

# Check if debug mode is enabled
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes", "on")

# Configure the logger
def configure_logging():
    """Configure the logging system for the application."""
    # Set the log level based on the DEBUG environment variable
    log_level = logging.DEBUG if DEBUG else DEFAULT_LOG_LEVEL
    logger.setLevel(log_level)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(console_handler)

    # Log the configuration
    logger.debug("Logging configured with level %s", 
                 logging.getLevelName(log_level))

# Configure logging when the module is imported
configure_logging()

# Create module-level loggers
def get_logger(name):
    """Get a logger for a module.
    
    Args:
        name: The name of the module.
        
    Returns:
        A logger instance for the module.
    """
    return logging.getLogger(f"vidview.{name}")