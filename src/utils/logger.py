"""
Simple file logger for Abaqus simulation runs.

Provides a clean way to log messages to a file instead of the Abaqus terminal.
"""

import os
from datetime import datetime


class Logger:
    """
    Simple file logger that writes messages to log.txt.

    Usage:
        logger = Logger(log_dir)
        logger.log("Message")
        logger.close()
    """

    def __init__(self, log_dir, log_filename="log.txt"):
        """
        Initialize logger with log file path.

        Args:
            log_dir: Directory where log file will be created
            log_filename: Name of the log file (default: "log.txt")
        """
        self.log_path = os.path.join(log_dir, log_filename)
        self.file = open(self.log_path, "w")

        # Write header
        self.log("=" * 70)
        self.log("SIMULATION LOG")
        self.log("Started: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.log("=" * 70)
        self.log("")

    def log(self, message):
        """
        Write a message to the log file.

        Args:
            message: Message string to log
        """
        self.file.write("%s\n" % (message))
        self.file.flush()  # Ensure immediate write

    def section(self, title):
        """
        Write a section header to the log.

        Args:
            title: Section title
        """
        self.log("")
        self.log("=" * 70)
        self.log(title)
        self.log("=" * 70)

    def close(self):
        """Close the log file."""
        if self.file and not self.file.closed:
            self.log("")
            self.log("=" * 70)
            self.log("Log ended: %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.log("=" * 70)
            self.file.close()

    def __del__(self):
        """Ensure file is closed on deletion."""
        self.close()


# Global logger instance
_logger = None


def init_logger(log_dir, log_filename="log.txt"):
    """
    Initialize the global logger.

    Args:
        log_dir: Directory where log file will be created
        log_filename: Name of the log file (default: "log.txt")
    """
    global _logger
    if _logger is not None:
        _logger.close()
    _logger = Logger(log_dir, log_filename)


def log_func(message):
    """
    Log a message using the global logger.

    Args:
        message: Message to log
    """
    if _logger is not None:
        _logger.log(message)


def log_section(title):
    """
    Log a section header using the global logger.

    Args:
        title: Section title
    """
    if _logger is not None:
        _logger.section(title)


def close_logger():
    """Close the global logger."""
    global _logger
    if _logger is not None:
        _logger.close()
        _logger = None
