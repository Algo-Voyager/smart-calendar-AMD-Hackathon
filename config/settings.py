"""
Configuration settings for the Smart Calendar AI Assistant
"""
import os
from typing import Dict, List

class Config:
    # vLLM Server Configuration for Llama-3.2-3B
    LLAMA_BASE_URL = "http://localhost:4000/v1"
    LLAMA_MODEL_PATH = "/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B"
    
    # Optimized for Llama-3.2-3B (smaller, faster model)
    DEFAULT_MODEL = "llama-3.2-3b"
    LLM_TIMEOUT = 15  # Reduced timeout for faster model
    LLM_MAX_RETRIES = 3
    
    # Llama-3.2-3B specific optimizations
    MAX_TOKENS = 512  # Sufficient for scheduling tasks
    TEMPERATURE = 0.1  # Low temperature for consistent results
    TOP_P = 0.9
    
    # Calendar Configuration
    CALENDAR_TOKENS_PATH = "/home/user/smart-calendar/IISc_Google_Calendar_Keys"
    TIMEZONE = "+05:30"  # IST timezone
    DEFAULT_DOMAIN = "@amd.com"
    
    # Available users with calendar tokens
    AVAILABLE_USERS = [
        "userone.amd@gmail.com",
        "usertwo.amd@gmail.com", 
        "userthree.amd@gmail.com"
    ]
    
    # API Configuration
    API_HOST = "0.0.0.0"
    API_PORT = 5000
    API_TIMEOUT = 10  # seconds - hackathon requirement
    
    # Scheduling Configuration
    BUSINESS_HOURS_START = 9  # 9 AM
    BUSINESS_HOURS_END = 18   # 6 PM
    MIN_MEETING_DURATION = 15  # minutes
    MAX_MEETING_DURATION = 480  # 8 hours
    DEFAULT_MEETING_DURATION = 30  # minutes
    
    # Date/Time Formats
    INPUT_DATETIME_FORMAT = "%d-%m-%YT%H:%M:%S"
    OUTPUT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    CALENDAR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    
    # Optimized AI Agent Prompts for Llama-3.2-3B
    EMAIL_PARSING_PROMPT = """You are a meeting scheduler. Extract meeting information from the email below and return ONLY a valid JSON response.

REQUIRED JSON FORMAT:
{{"participants": ["email1@domain.com", "email2@domain.com"], "duration_minutes": 30, "time_constraints": "specific_constraint", "topic": "meeting_topic", "priority": "normal"}}

EXTRACTION RULES:
1. Extract ALL participant email addresses
2. If only names provided, append {domain} 
3. Duration: Extract from phrases like "30 minutes", "1 hour", "half hour" (default: {default_duration})
4. Time constraints: Extract specific time references like:
   - "Thursday" → "thursday"
   - "next week" → "next week" 
   - "tomorrow" → "tomorrow"
   - "Monday morning" → "monday"
5. Topic: Extract main meeting purpose or use email subject
6. Priority: Detect priority level:
   - "high" if content contains: urgent, ASAP, critical, emergency, high priority, must schedule, required, mandatory, deadline, time sensitive, crisis
   - "normal" for regular meetings

EMAIL CONTENT: {email_content}

Return ONLY the JSON object (no explanations):"""

    SCHEDULING_PROMPT = """You are an AI scheduling assistant. Find the optimal meeting time and return ONLY a valid JSON response.

MEETING DETAILS:
- Topic: {topic}
- Duration: {duration} minutes
- Participants: {participants}
- Time Constraint: {time_constraints}
- Current Time: {current_time}

PARTICIPANT CALENDARS:
{calendar_data}

SCHEDULING RULES:
1. Business hours: 9:00 AM - 6:00 PM IST (Monday-Friday)
2. Avoid ALL calendar conflicts 
3. Respect the time constraint "{time_constraints}":
   - "thursday" = next Thursday between 9 AM - 6 PM
   - "next week" = any day next week during business hours
   - "tomorrow" = tomorrow during business hours
   - "flexible" = any available business hours slot
4. Choose earliest available slot that meets all criteria
5. Format times as: YYYY-MM-DDTHH:MM:SS+05:30

REQUIRED JSON FORMAT:
{{"start_time": "2025-07-24T10:00:00+05:30", "end_time": "2025-07-24T10:30:00+05:30", "reasoning": "Found available slot on Thursday morning with no conflicts for all participants"}}

IMPORTANT: 
- Check for time overlaps carefully
- If "{time_constraints}" specifies a day, find that specific day
- Ensure the duration matches exactly
- Account for IST timezone (+05:30)

Return ONLY the JSON object (no explanations):"""

    @classmethod
    def get_model_config(cls, model_name: str = None) -> Dict[str, str]:
        """Get model configuration for Llama-3.2-3B"""
        model_name = model_name or cls.DEFAULT_MODEL
        
        # Always use Llama-3.2-3B configuration
        return {
            "base_url": cls.LLAMA_BASE_URL,
            "model_path": cls.LLAMA_MODEL_PATH,
            "max_tokens": cls.MAX_TOKENS,
            "temperature": cls.TEMPERATURE,
            "top_p": cls.TOP_P
        }
    
    @classmethod
    def get_token_path(cls, email: str) -> str:
        """Get token file path for a user email"""
        # Validate that the user has an available token
        if email not in cls.AVAILABLE_USERS:
            raise ValueError(f"User {email} does not have a calendar token. Available users: {cls.AVAILABLE_USERS}")
        
        username = email.split("@")[0]
        token_file = f"{username}.token"
        token_path = os.path.join(cls.CALENDAR_TOKENS_PATH, token_file)
        
        # Double-check that the token file actually exists
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Token file not found: {token_path}. Available users: {cls.AVAILABLE_USERS}")
        
        return token_path