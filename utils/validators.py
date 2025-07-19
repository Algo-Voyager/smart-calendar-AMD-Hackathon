"""
Validation utilities for the Smart Calendar Assistant
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

class RequestValidator:
    """Validator for incoming meeting requests"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    @staticmethod
    def validate_datetime_format(datetime_str: str, format_str: str) -> bool:
        """Validate datetime format"""
        try:
            datetime.strptime(datetime_str, format_str)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_request_structure(request_data: Dict[str, Any]) -> List[str]:
        """Validate request data structure and return list of errors"""
        errors = []
        
        # Required fields
        required_fields = ["Request_id", "Datetime", "From", "Subject", "EmailContent"]
        for field in required_fields:
            if field not in request_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate email format
        if "From" in request_data:
            if not RequestValidator.validate_email(request_data["From"]):
                errors.append(f"Invalid email format in 'From': {request_data['From']}")
        
        # Validate attendees
        if "Attendees" in request_data:
            if not isinstance(request_data["Attendees"], list):
                errors.append("'Attendees' must be a list")
            else:
                for i, attendee in enumerate(request_data["Attendees"]):
                    if not isinstance(attendee, dict) or "email" not in attendee:
                        errors.append(f"Attendee {i} must have 'email' field")
                    elif not RequestValidator.validate_email(attendee["email"]):
                        errors.append(f"Invalid email format in attendee {i}: {attendee['email']}")
        
        # Validate datetime format
        if "Datetime" in request_data:
            datetime_str = request_data["Datetime"]
            if not RequestValidator.validate_datetime_format(datetime_str, "%d-%m-%YT%H:%M:%S"):
                errors.append(f"Invalid datetime format: {datetime_str}. Expected: DD-MM-YYYYTHH:MM:SS")
        
        return errors
    
    @staticmethod
    def validate_response_structure(response_data: Dict[str, Any]) -> List[str]:
        """Validate response data structure"""
        errors = []
        
        # Required fields in response
        required_fields = ["Request_id", "Attendees", "EventStart", "EventEnd", "Duration_mins"]
        for field in required_fields:
            if field not in response_data:
                errors.append(f"Missing required response field: {field}")
        
        # Validate attendees structure
        if "Attendees" in response_data:
            if not isinstance(response_data["Attendees"], list):
                errors.append("Response 'Attendees' must be a list")
            else:
                for i, attendee in enumerate(response_data["Attendees"]):
                    if not isinstance(attendee, dict):
                        errors.append(f"Attendee {i} must be a dictionary")
                        continue
                    
                    if "email" not in attendee:
                        errors.append(f"Attendee {i} missing 'email' field")
                    
                    if "events" not in attendee:
                        errors.append(f"Attendee {i} missing 'events' field")
                    elif not isinstance(attendee["events"], list):
                        errors.append(f"Attendee {i} 'events' must be a list")
        
        # Validate datetime formats
        datetime_fields = ["EventStart", "EventEnd"]
        for field in datetime_fields:
            if field in response_data:
                datetime_str = response_data[field]
                if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+05:30', datetime_str):
                    errors.append(f"Invalid {field} format: {datetime_str}. Expected: YYYY-MM-DDTHH:MM:SS+05:30")
        
        return errors

class DataSanitizer:
    """Sanitize and clean input data"""
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email address"""
        return email.strip().lower()
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove potentially harmful characters
        text = re.sub(r'[<>"\']', '', text)
        return text
    
    @staticmethod
    def sanitize_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize entire request"""
        sanitized = request_data.copy()
        
        # Sanitize email fields
        if "From" in sanitized:
            sanitized["From"] = DataSanitizer.sanitize_email(sanitized["From"])
        
        if "Attendees" in sanitized:
            for attendee in sanitized["Attendees"]:
                if "email" in attendee:
                    attendee["email"] = DataSanitizer.sanitize_email(attendee["email"])
        
        # Sanitize text fields
        text_fields = ["Subject", "EmailContent", "Location"]
        for field in text_fields:
            if field in sanitized:
                sanitized[field] = DataSanitizer.sanitize_text(sanitized[field])
        
        return sanitized