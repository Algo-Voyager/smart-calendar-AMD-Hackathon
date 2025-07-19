"""
Logging utilities for the Smart Calendar Assistant
"""
import logging
import sys
from datetime import datetime
import json
from pathlib import Path

class SmartCalendarLogger:
    """Custom logger for Smart Calendar Assistant"""
    
    @staticmethod
    def setup_logging(log_level: str = "INFO", log_file: str = None):
        """Setup logging configuration"""
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Suppress some noisy loggers
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('googleapiclient').setLevel(logging.WARNING)
        
        return root_logger
    
    @staticmethod
    def log_request_response(request_id: str, request_data: dict, 
                           response_data: dict, processing_time: float):
        """Log request and response for debugging"""
        logger = logging.getLogger(__name__)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "processing_time_seconds": processing_time,
            "request_summary": {
                "from": request_data.get("From"),
                "attendees_count": len(request_data.get("Attendees", [])),
                "subject": request_data.get("Subject")
            },
            "response_summary": {
                "event_start": response_data.get("EventStart"),
                "event_end": response_data.get("EventEnd"),
                "duration_mins": response_data.get("Duration_mins"),
                "scheduling_method": response_data.get("MetaData", {}).get("scheduling_method")
            }
        }
        
        logger.info(f"Request processed: {json.dumps(log_entry, indent=2)}")