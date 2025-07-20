"""
Mock LLM Client for testing without external LLM dependencies
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MockLLMClient:
    """Mock LLM client for testing"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or "mock-llm"
        logger.info(f"Initialized Mock LLM client: {self.model_name}")
    
    def parse_email_content(self, email_content: str) -> Dict[str, Any]:
        """Mock email parsing using simple regex patterns"""
        logger.info(f"🤖 MOCK: Parsing email content")
        
        content_lower = email_content.lower()
        
        # Extract participants (simple pattern matching)
        participants = []
        
        # Look for email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, email_content)
        participants.extend(found_emails)
        
        # If no emails found, look for names and add default domain
        if not participants:
            # Look for common greeting patterns
            name_patterns = [
                r'hi\s+([a-zA-Z\s,&]+)',
                r'hello\s+([a-zA-Z\s,&]+)',
                r'team',
                r'all',
                r'everyone'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    if 'team' in pattern or 'all' in pattern or 'everyone' in pattern:
                        # Default team members
                        participants = [
                            "userone.amd@gmail.com",
                            "usertwo.amd@gmail.com", 
                            "userthree.amd@gmail.com"
                        ]
                    break
        
        # Extract duration
        duration = 30  # default
        duration_patterns = [
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)\s*hours?',
            r'half\s*hour',
            r'an?\s*hour'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, content_lower)
            if match:
                if 'half' in pattern:
                    duration = 30
                elif 'hour' in pattern and 'hours' not in pattern:
                    duration = 60
                elif match.group(1):
                    num = int(match.group(1))
                    if 'hour' in pattern:
                        duration = num * 60
                    else:
                        duration = num
                break
        
        # Extract time constraints
        time_constraints = "flexible"
        time_patterns = [
            r'next\s+week',
            r'tomorrow',
            r'today',
            r'this\s+week',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
            r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content_lower)
            if match:
                time_constraints = match.group(0)
                break
        
        # Extract topic
        topic = "Meeting"
        if "status" in content_lower and "update" in content_lower:
            topic = "Status Update Meeting"
        elif "project" in content_lower:
            topic = "Project Meeting"

        # 🎯 NEW: Priority detection for mock client
        priority = "normal"  # default priority
        high_priority_indicators = [
            "urgent", "high priority", "asap", "emergency", "critical", 
            "important", "must schedule", "required meeting", "mandatory"
        ]

        for indicator in high_priority_indicators:
            if indicator in content_lower:
                priority = "high"
                logger.info(f"🚨 MOCK: HIGH PRIORITY meeting detected: '{indicator}' found")
                break

        result = {
            'participants': participants,
            'duration_minutes': duration,
            'time_constraints': time_constraints,
            'topic': topic,
            'priority': priority  # 🎯 NEW: Add priority field
        }
        
        logger.info(f"🤖 MOCK: Parsed email -> {result}")
        return result
    
    def find_optimal_meeting_time(self, meeting_request: Dict[str, Any], 
                                calendar_data: Dict[str, Any], 
                                current_time: str) -> Dict[str, Any]:
        """Mock scheduling logic"""
        logger.info(f"🤖 MOCK: Finding optimal meeting time")
        
        # Simple logic: find next Thursday at 10 AM for "thursday" constraint
        time_constraints = meeting_request.get('time_constraints', 'flexible').lower()
        duration = meeting_request.get('duration_minutes', 30)
        
        now = datetime.now()
        
        if 'thursday' in time_constraints:
            # Find next Thursday
            days_ahead = (3 - now.weekday()) % 7  # Thursday is weekday 3
            if days_ahead == 0:
                # If it's Thursday, check if it's past business hours
                if now.hour >= 18:
                    days_ahead = 7
            if days_ahead == 0:
                days_ahead = 7  # Move to next Thursday
                
            next_thursday = now + timedelta(days=days_ahead)
            start_time = next_thursday.replace(hour=10, minute=0, second=0, microsecond=0)
            
        else:
            # Default: tomorrow at 10 AM
            tomorrow = now + timedelta(days=1)
            while tomorrow.weekday() >= 5:  # Skip weekends
                tomorrow += timedelta(days=1)
            start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        
        end_time = start_time + timedelta(minutes=duration)
        
        result = {
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            'reasoning': f'Mock scheduling: Found {time_constraints} slot with no conflicts'
        }
        
        logger.info(f"🤖 MOCK: Scheduled -> {result}")
        return result 