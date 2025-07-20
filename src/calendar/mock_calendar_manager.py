"""
Mock Calendar Manager for testing without Google Calendar dependencies
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class CalendarEvent:
    """Mock calendar event for testing"""
    
    def __init__(self, start_time: str, end_time: str, attendees: List[str], 
                 summary: str, event_id: str = None):
        self.start_time = start_time
        self.end_time = end_time
        self.attendees = attendees
        self.summary = summary
        self.event_id = event_id or f"mock_event_{hash(summary)}"
        self.num_attendees = len(attendees)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            "StartTime": self.start_time,
            "EndTime": self.end_time,
            "NumAttendees": self.num_attendees,
            "Attendees": self.attendees,
            "Summary": self.summary
        }

class MockCalendarManager:
    """Mock calendar manager for testing"""
    
    def __init__(self):
        self.mock_events = self._create_mock_events()
        
    def _create_mock_events(self) -> Dict[str, List[CalendarEvent]]:
        """Create some mock events for testing"""
        
        # Generate some mock events for the next few days
        now = datetime.now()
        events = {}
        
        users = ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"]
        
        for user in users:
            user_events = []
            
            # Add some existing meetings
            for i in range(2):
                start_time = now + timedelta(days=i+1, hours=9+i*2)
                end_time = start_time + timedelta(hours=1)
                
                event = CalendarEvent(
                    start_time=start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                    end_time=end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                    attendees=[user],
                    summary=f"Existing Meeting {i+1}"
                )
                user_events.append(event)
                
            events[user] = user_events
            
        return events
    
    def get_user_events(self, email: str, start_date: str, end_date: str) -> List[CalendarEvent]:
        """Get mock events for a user"""
        logger.info(f"📋 MOCK: Getting events for {email}")
        return self.mock_events.get(email, [])
    
    def get_multiple_users_events(self, emails: List[str], start_date: str, 
                                end_date: str) -> Dict[str, List[CalendarEvent]]:
        """Get mock events for multiple users"""
        logger.info(f"📋 MOCK: Getting events for {len(emails)} users")
        
        results = {}
        for email in emails:
            results[email] = self.get_user_events(email, start_date, end_date)
            
        return results
    
    def find_free_slots(self, email: str, start_date: str, end_date: str, 
                       duration_minutes: int) -> List[Tuple[str, str]]:
        """Find mock free slots"""
        logger.info(f"🔍 MOCK: Finding free slots for {email}")
        
        # Return some mock free slots
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        
        # Find next Thursday
        days_ahead = (3 - tomorrow.weekday()) % 7  # Thursday is weekday 3
        if days_ahead == 0:
            days_ahead = 7
        next_thursday = tomorrow + timedelta(days=days_ahead)
        
        # Mock free slots on Thursday
        free_slots = []
        for hour in [10, 11, 14, 15]:  # 10 AM, 11 AM, 2 PM, 3 PM
            slot_start = next_thursday.replace(hour=hour, minute=0, second=0)
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            
            free_slots.append((
                slot_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                slot_end.strftime('%Y-%m-%dT%H:%M:%S+05:30')
            ))
            
        return free_slots
    
    def find_common_free_slots(self, emails: List[str], start_date: str, end_date: str, 
                             duration_minutes: int) -> List[Tuple[str, str]]:
        """Find mock common free slots"""
        logger.info(f"🔍 MOCK: Finding common free slots for {len(emails)} users")
        
        # For mock purposes, return slots that work for everyone
        if not emails:
            return []
            
        # Get free slots for first user and assume they work for everyone
        return self.find_free_slots(emails[0], start_date, end_date, duration_minutes) 