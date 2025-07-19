"""
Optimized Google Calendar integration for the Smart Calendar Assistant
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import Config

logger = logging.getLogger(__name__)

class CalendarEvent:
    """Represents a calendar event with optimized data structure"""
    
    def __init__(self, start_time: str, end_time: str, attendees: List[str], 
                 summary: str, event_id: str = None):
        self.start_time = start_time
        self.end_time = end_time
        self.attendees = attendees
        self.summary = summary
        self.event_id = event_id
        self.num_attendees = len(attendees)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format for JSON serialization"""
        return {
            "StartTime": self.start_time,
            "EndTime": self.end_time,
            "NumAttendees": self.num_attendees,
            "Attendees": self.attendees,
            "Summary": self.summary
        }
    
    def overlaps_with(self, other_start: str, other_end: str) -> bool:
        """Check if this event overlaps with another time range"""
        start1 = datetime.fromisoformat(self.start_time.replace('+05:30', ''))
        end1 = datetime.fromisoformat(self.end_time.replace('+05:30', ''))
        start2 = datetime.fromisoformat(other_start.replace('+05:30', ''))
        end2 = datetime.fromisoformat(other_end.replace('+05:30', ''))
        
        return start1 < end2 and end1 > start2

class CalendarManager:
    """Optimized calendar manager with caching and parallel processing"""
    
    def __init__(self):
        self.config = Config()
        self._calendar_cache = {}
        self._cache_expiry = {}
        self._cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
    
    def _get_credentials(self, email: str) -> Credentials:
        """Get Google Calendar credentials for a user"""
        try:
            token_path = self.config.get_token_path(email)
            return Credentials.from_authorized_user_file(token_path)
        except (ValueError, FileNotFoundError) as e:
            logger.error(f"❌ Calendar token not available for {email}: {e}")
            raise ValueError(f"User {email} does not have calendar access. Please use one of the available users with tokens.")
        except Exception as e:
            logger.error(f"❌ Failed to load credentials for {email}: {e}")
            raise
    
    def _build_calendar_service(self, email: str):
        """Build Google Calendar service for a user"""
        credentials = self._get_credentials(email)
        return build("calendar", "v3", credentials=credentials)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._calendar_cache:
            return False
        
        expiry_time = self._cache_expiry.get(cache_key)
        if not expiry_time or datetime.now() > expiry_time:
            # Clean up expired cache
            self._calendar_cache.pop(cache_key, None)
            self._cache_expiry.pop(cache_key, None)
            return False
        
        return True
    
    def _cache_events(self, cache_key: str, events: List[CalendarEvent]):
        """Cache events data"""
        self._calendar_cache[cache_key] = events
        self._cache_expiry[cache_key] = datetime.now() + self._cache_duration
    
    def get_user_events(self, email: str, start_date: str, end_date: str) -> List[CalendarEvent]:
        """Get calendar events for a single user with caching"""
        cache_key = f"{email}_{start_date}_{end_date}"
        
        logger.info(f"📅 Fetching calendar events for member: {email}")
        logger.info(f"   Date range: {start_date} to {end_date}")
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.info(f"Using cached events for {email}")
            return self._calendar_cache[cache_key]
        
        try:
            calendar_service = self._build_calendar_service(email)
            
            events_result = calendar_service.events().list(
                calendarId='primary',
                timeMin=start_date,
                timeMax=end_date,
                singleEvents=True,
                orderBy='startTime',
                maxResults=50  # Limit results for performance
            ).execute()
            
            events = events_result.get('items', [])
            calendar_events = []
            
            for event in events:
                # Handle attendees
                attendee_list = []
                if 'attendees' in event:
                    for attendee in event['attendees']:
                        if 'email' in attendee:
                            attendee_list.append(attendee['email'])
                
                if not attendee_list:
                    attendee_list = ["SELF"]
                
                # Extract event details
                start_time = event.get('start', {}).get('dateTime', '')
                end_time = event.get('end', {}).get('dateTime', '')
                summary = event.get('summary', 'Untitled Event')
                event_id = event.get('id', '')
                
                if start_time and end_time:
                    calendar_event = CalendarEvent(
                        start_time=start_time,
                        end_time=end_time,
                        attendees=list(set(attendee_list)),  # Remove duplicates
                        summary=summary,
                        event_id=event_id
                    )
                    calendar_events.append(calendar_event)
            
            # Log all existing meetings for the member before scheduling
            logger.info(f"📋 EXISTING MEETINGS LOG for {email}:")
            logger.info(f"   Total events found: {len(calendar_events)}")
            
            off_hours_count = 0
            business_hours_count = 0
            
            for i, event in enumerate(calendar_events, 1):
                start_time = datetime.fromisoformat(event.start_time.replace('+05:30', ''))
                end_time = datetime.fromisoformat(event.end_time.replace('+05:30', ''))
                
                # Check if event is during off hours
                is_off_hours = (start_time.hour < self.config.BUSINESS_HOURS_START or 
                               start_time.hour >= self.config.BUSINESS_HOURS_END or
                               start_time.weekday() >= 5)  # Weekend
                
                if is_off_hours:
                    off_hours_count += 1
                    logger.info(f"   🌙 OFF HOURS Event {i}: {event.summary}")
                else:
                    business_hours_count += 1
                    logger.info(f"   🏢 BUSINESS HOURS Event {i}: {event.summary}")
                
                logger.info(f"      Time: {event.start_time} to {event.end_time}")
                logger.info(f"      Attendees: {event.attendees}")
                logger.info(f"      Duration: {(end_time - start_time).total_seconds() / 60:.0f} minutes")
            
            logger.info(f"📊 MEETING SUMMARY for {email}:")
            logger.info(f"   🏢 Business hours meetings: {business_hours_count}")
            logger.info(f"   🌙 Off hours meetings: {off_hours_count}")
            logger.info(f"   📅 Total meetings: {len(calendar_events)}")
            
            # Cache the results
            self._cache_events(cache_key, calendar_events)
            logger.info(f"✅ Retrieved and cached {len(calendar_events)} events for {email}")
            
            return calendar_events
            
        except HttpError as e:
            logger.error(f"HTTP error getting events for {email}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting events for {email}: {e}")
            return []
    
    def get_multiple_users_events(self, emails: List[str], start_date: str, 
                                end_date: str) -> Dict[str, List[CalendarEvent]]:
        """Get calendar events for multiple users in parallel"""
        logger.info(f"🔄 BEFORE SCHEDULING - Fetching existing meetings for all {len(emails)} members")
        logger.info(f"   Members: {', '.join(emails)}")
        
        results = {}
        
        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=min(len(emails), 5)) as executor:
            future_to_email = {
                executor.submit(self.get_user_events, email, start_date, end_date): email
                for email in emails
            }
            
            for future in as_completed(future_to_email):
                email = future_to_email[future]
                try:
                    events = future.result(timeout=30)
                    results[email] = events
                except Exception as e:
                    logger.error(f"Failed to get events for {email}: {e}")
                    results[email] = []
        
        # Log consolidated summary of all members' meetings
        logger.info(f"📊 CONSOLIDATED MEETINGS SUMMARY (Before Scheduling):")
        total_meetings = 0
        total_off_hours = 0
        total_business_hours = 0
        
        for email, events in results.items():
            off_hours = 0
            business_hours = 0
            
            for event in events:
                start_time = datetime.fromisoformat(event.start_time.replace('+05:30', ''))
                is_off_hours = (start_time.hour < self.config.BUSINESS_HOURS_START or 
                               start_time.hour >= self.config.BUSINESS_HOURS_END or
                               start_time.weekday() >= 5)
                
                if is_off_hours:
                    off_hours += 1
                else:
                    business_hours += 1
            
            total_meetings += len(events)
            total_off_hours += off_hours
            total_business_hours += business_hours
            
            logger.info(f"   {email}: {len(events)} total ({business_hours} business, {off_hours} off-hours)")
        
        logger.info(f"🎯 OVERALL SUMMARY:")
        logger.info(f"   📅 Total meetings across all members: {total_meetings}")
        logger.info(f"   🏢 Total business hours meetings: {total_business_hours}")
        logger.info(f"   🌙 Total off hours meetings: {total_off_hours}")
        logger.info(f"   👥 Members analyzed: {len(emails)}")
        
        return results
    
    def find_free_slots(self, email: str, start_date: str, end_date: str, 
                       duration_minutes: int) -> List[Tuple[str, str]]:
        """Find free time slots for a user"""
        events = self.get_user_events(email, start_date, end_date)
        
        # Convert to datetime objects for easier manipulation
        start_dt = datetime.fromisoformat(start_date.replace('+05:30', ''))
        end_dt = datetime.fromisoformat(end_date.replace('+05:30', ''))
        duration = timedelta(minutes=duration_minutes)
        
        # Create list of busy periods
        busy_periods = []
        for event in events:
            event_start = datetime.fromisoformat(event.start_time.replace('+05:30', ''))
            event_end = datetime.fromisoformat(event.end_time.replace('+05:30', ''))
            busy_periods.append((event_start, event_end))
        
        # Sort busy periods by start time
        busy_periods.sort(key=lambda x: x[0])
        
        # Find free slots
        free_slots = []
        current_time = start_dt
        
        for busy_start, busy_end in busy_periods:
            # Check if there's a free slot before this busy period
            if current_time + duration <= busy_start:
                # Apply business hours constraint
                slot_start = max(current_time, 
                               current_time.replace(hour=self.config.BUSINESS_HOURS_START, 
                                                   minute=0, second=0))
                slot_end = min(busy_start,
                             current_time.replace(hour=self.config.BUSINESS_HOURS_END, 
                                                 minute=0, second=0))
                
                if slot_start + duration <= slot_end:
                    # Check if this slot is during off hours
                    is_off_hours = (slot_start.hour < self.config.BUSINESS_HOURS_START or 
                                   slot_start.hour >= self.config.BUSINESS_HOURS_END or
                                   slot_start.weekday() >= 5)
                    
                    slot_info = (
                        slot_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                        (slot_start + duration).strftime('%Y-%m-%dT%H:%M:%S+05:30')
                    )
                    
                    if is_off_hours:
                        logger.info(f"   🌙 Found OFF HOURS free slot for {email}: {slot_info[0]} to {slot_info[1]}")
                    else:
                        logger.info(f"   🏢 Found BUSINESS HOURS free slot for {email}: {slot_info[0]} to {slot_info[1]}")
                    
                    free_slots.append(slot_info)
            
            current_time = max(current_time, busy_end)
        
        # Check for free slot after last busy period
        if current_time + duration <= end_dt:
            slot_start = max(current_time,
                           current_time.replace(hour=self.config.BUSINESS_HOURS_START, 
                                               minute=0, second=0))
            slot_end = min(end_dt,
                         current_time.replace(hour=self.config.BUSINESS_HOURS_END, 
                                             minute=0, second=0))
            
            if slot_start + duration <= slot_end:
                free_slots.append((
                    slot_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                    (slot_start + duration).strftime('%Y-%m-%dT%H:%M:%S+05:30')
                ))
        
        return free_slots
    
    def find_common_free_slots(self, emails: List[str], start_date: str, end_date: str, 
                             duration_minutes: int) -> List[Tuple[str, str]]:
        """Find common free time slots for multiple users"""
        if not emails:
            return []
        
        # Get free slots for each user
        all_free_slots = {}
        for email in emails:
            all_free_slots[email] = set(self.find_free_slots(email, start_date, end_date, duration_minutes))
        
        # Find intersection of all free slots
        if not all_free_slots:
            return []
        
        common_slots = set.intersection(*all_free_slots.values())
        return sorted(list(common_slots))
    
    def create_calendar_event(self, organizer_email: str, start_time: str, end_time: str,
                            attendees: List[str], summary: str) -> bool:
        """Create a new calendar event (placeholder for actual implementation)"""
        try:
            calendar_service = self._build_calendar_service(organizer_email)
            
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'Asia/Kolkata',
                },
                'attendees': [{'email': email} for email in attendees],
            }
            
            # Note: In a real implementation, you would uncomment this
            # created_event = calendar_service.events().insert(calendarId='primary', body=event).execute()
            # logger.info(f"Event created: {created_event.get('htmlLink')}")
            
            logger.info(f"Would create event: {summary} from {start_time} to {end_time}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return False