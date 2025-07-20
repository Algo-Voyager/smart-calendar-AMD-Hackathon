"""
Smart Scheduler - Main orchestrator for the AI Scheduling Assistant
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config.settings import Config
from src.calendar.calendar_manager import CalendarManager, CalendarEvent
from src.ai_agent.llm_client import LLMClient
from src.scheduler.scheduling_validator import SchedulingValidator  # 🔍 NEW: Import validator

logger = logging.getLogger(__name__)

class SmartScheduler:
    """
    Main scheduling coordinator that orchestrates the entire scheduling process
    """
    
    def __init__(self, model_name: str = None):
        self.config = Config()
        
        # Try to use real calendar manager, fallback to mock if dependencies missing
        try:
            from src.calendar.calendar_manager import CalendarManager
            self.calendar_manager = CalendarManager()
            logger.info("✅ Using real Google Calendar integration")
        except ImportError as e:
            logger.warning(f"⚠️  Google Calendar dependencies not available: {e}")
            logger.info("🔄 Using mock calendar manager for testing")
            from src.calendar.mock_calendar_manager import MockCalendarManager
            self.calendar_manager = MockCalendarManager()
        
        # Try to use real LLM client, fallback to mock if dependencies missing  
        try:
            from src.ai_agent.llm_client import LLMClient
            self.llm_client = LLMClient(model_name)
            logger.info("✅ Using real LLM client")
        except ImportError as e:
            logger.warning(f"⚠️  LLM dependencies not available: {e}")
            logger.info("🔄 Using mock LLM client for testing")
            from src.ai_agent.mock_llm_client import MockLLMClient
            self.llm_client = MockLLMClient()
        
        # 🔍 NEW: Initialize scheduling validator
        self.validator = SchedulingValidator(self.config)
        logger.info("✅ Scheduling validator initialized")
        
        logger.info("SmartScheduler initialized")
    
    def process_meeting_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing meeting requests with iterative validation
        """
        try:
            start_time = datetime.now()
            
            # Validate input
            if not self._validate_input(request_data):
                raise ValueError("Invalid input data")
            
            # Extract request information
            request_id = request_data.get("Request_id")
            email_content = request_data.get("EmailContent", "")
            organizer_email = request_data.get("From", "")
            attendee_emails = [att.get("email") for att in request_data.get("Attendees", [])]
            
            # Add organizer to attendees if not already included
            all_attendees = [organizer_email] + attendee_emails
            all_attendees = list(set(all_attendees))  # Remove duplicates
            
            logger.info(f"Processing request {request_id} for {len(all_attendees)} attendees")
            
            # Step 1: Parse email content using AI
            meeting_params = self.llm_client.parse_email_content(email_content)
            logger.info(f"Parsed meeting parameters: {meeting_params}")
            
            # Step 2: Get calendar data for all attendees
            original_calendar_data = self._get_calendar_data_for_attendees(
                all_attendees, meeting_params.get('time_constraints', 'flexible')
            )
            
            # 🔍 NEW: Use iterative validation system instead of simple scheduling
            logger.info(f"🔍 STARTING ITERATIVE VALIDATION & OPTIMIZATION")
            output_data = self.validator.validate_and_optimize_scheduling(
                request_data=request_data,
                original_calendar_data=original_calendar_data,
                meeting_params=meeting_params,
                scheduler_instance=self  # Pass self so validator can call our methods
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Request processed with validation in {processing_time:.2f} seconds")
            
            # Add processing time to metadata
            if "MetaData" not in output_data:
                output_data["MetaData"] = {}
            output_data["MetaData"]["total_processing_time"] = f"{processing_time:.2f}s"
            
            return output_data
            
        except Exception as e:
            logger.error(f"Error processing meeting request: {e}")
            # Return fallback response
            return self._create_fallback_response(request_data)
    
    def _validate_input(self, request_data: Dict[str, Any]) -> bool:
        """Validate input request data"""
        required_fields = ["Request_id", "From", "EmailContent"]
        
        for field in required_fields:
            if field not in request_data:
                logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    def _get_calendar_data_for_attendees(self, attendees: List[str], 
                                       time_constraints: str) -> Dict[str, List[Dict]]:
        """Get calendar data for all attendees within relevant time range"""
        
        # Determine date range based on time constraints
        start_date, end_date = self._parse_time_constraints(time_constraints)
        
        logger.info(f"🗓️  BEFORE SCHEDULING MEETING - Calendar Analysis Phase")
        logger.info(f"   📅 Date range: {start_date} to {end_date}")
        logger.info(f"   👥 Attendees to analyze: {', '.join(attendees)}")
        logger.info(f"   🎯 Time constraints: {time_constraints}")
        
        # Get events for all attendees in parallel
        calendar_events = self.calendar_manager.get_multiple_users_events(
            attendees, start_date, end_date
        )
        
        # Convert CalendarEvent objects to dictionaries and log details
        calendar_data = {}
        logger.info(f"📝 DETAILED MEMBER ANALYSIS:")
        
        for email, events in calendar_events.items():
            event_dicts = [event.to_dict() for event in events]
            calendar_data[email] = event_dicts
            
            # Log detailed analysis for each member
            logger.info(f"   📧 {email}:")
            logger.info(f"      📊 Total meetings: {len(events)}")
            
            if events:
                off_hours_meetings = []
                business_hours_meetings = []
                
                for event in events:
                    start_time = datetime.fromisoformat(event.start_time.replace('+05:30', ''))
                    is_off_hours = (start_time.hour < self.config.BUSINESS_HOURS_START or 
                                   start_time.hour >= self.config.BUSINESS_HOURS_END or
                                   start_time.weekday() >= 5)
                    
                    if is_off_hours:
                        off_hours_meetings.append(event)
                    else:
                        business_hours_meetings.append(event)
                
                logger.info(f"      🏢 Business hours meetings: {len(business_hours_meetings)}")
                logger.info(f"      🌙 Off hours meetings: {len(off_hours_meetings)}")
                
                # Log specific off-hours meetings
                if off_hours_meetings:
                    logger.info(f"      🌙 OFF HOURS MEETINGS DETAILS:")
                    for i, event in enumerate(off_hours_meetings, 1):
                        logger.info(f"         {i}. {event.summary}")
                        logger.info(f"            Time: {event.start_time} to {event.end_time}")
                        logger.info(f"            Attendees: {', '.join(event.attendees)}")
            else:
                logger.info(f"      ✅ No existing meetings found")
        
        logger.info(f"✅ Calendar data analysis completed for all {len(attendees)} members")
        return calendar_data
    
    def _parse_time_constraints(self, time_constraints: str) -> tuple[str, str]:
        """Parse time constraints and return start/end dates"""
        now = datetime.now()
        
        constraints_lower = time_constraints.lower().strip()
        
        logger.info(f"🔍 PARSING TIME CONSTRAINTS: '{time_constraints}' -> '{constraints_lower}'")
        
        if 'next week' in constraints_lower:
            # Start from next Monday
            days_ahead = 7 - now.weekday()
            start_date = now + timedelta(days=days_ahead)
            end_date = start_date + timedelta(days=7)
            logger.info(f"   📅 Parsed as: Next week ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        elif 'tomorrow' in constraints_lower:
            start_date = now + timedelta(days=1)
            end_date = start_date + timedelta(days=1)
            logger.info(f"   📅 Parsed as: Tomorrow ({start_date.strftime('%Y-%m-%d')})")
        elif 'today' in constraints_lower:
            start_date = now
            end_date = now + timedelta(days=1)
            logger.info(f"   📅 Parsed as: Today ({start_date.strftime('%Y-%m-%d')})")
        elif 'this week' in constraints_lower:
            # Rest of this week
            start_date = now
            days_until_sunday = 6 - now.weekday()
            end_date = now + timedelta(days=days_until_sunday)
            logger.info(f"   📅 Parsed as: This week ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        elif any(day in constraints_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
            # Specific day - find next occurrence
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            target_day = None
            target_day_name = None
            
            for day in days:
                if day in constraints_lower:
                    target_day = days.index(day)
                    target_day_name = day.title()
                    break
            
            if target_day is not None:
                current_weekday = now.weekday()
                days_ahead = (target_day - current_weekday) % 7
                
                # If it's the same day but past business hours, move to next week
                if days_ahead == 0:
                    if now.hour >= self.config.BUSINESS_HOURS_END:
                        days_ahead = 7
                    else:
                        # It's today and still during business hours
                        days_ahead = 0
                
                # If the target day is earlier in the week, move to next week
                if days_ahead == 0 and target_day < current_weekday:
                    days_ahead = 7
                    
                start_date = now + timedelta(days=days_ahead)
                end_date = start_date + timedelta(days=1)
                
                # Ensure we're looking at the right day
                if start_date.weekday() != target_day:
                    # Recalculate to be sure
                    days_ahead = (target_day - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 7  # Next week if same day
                    start_date = now + timedelta(days=days_ahead)
                    end_date = start_date + timedelta(days=1)
                
                logger.info(f"   📅 Parsed as: Next {target_day_name} ({start_date.strftime('%Y-%m-%d %A')})")
                logger.info(f"   🔢 Days ahead calculation: current_weekday={current_weekday}, target_day={target_day}, days_ahead={days_ahead}")
            else:
                # Default case
                start_date = now + timedelta(days=1)
                end_date = start_date + timedelta(days=7)
                logger.info(f"   📅 Parsed as: Default next 7 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        else:
            # Default: next 7 days
            start_date = now + timedelta(days=1)
            end_date = start_date + timedelta(days=7)
            logger.info(f"   📅 Parsed as: Flexible - next 7 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        
        # Format for Google Calendar API
        start_str = start_date.strftime('%Y-%m-%dT00:00:00+05:30')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59+05:30')
        
        logger.info(f"   🎯 FINAL DATE RANGE: {start_str} to {end_str}")
        
        return start_str, end_str
    
    def _find_optimal_meeting_time(self, meeting_params: Dict[str, Any], 
                                 calendar_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Find the optimal meeting time using AI and algorithmic approaches"""
        
        current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        logger.info(f"🎯 SCHEDULING PHASE - Finding optimal meeting time")
        logger.info(f"   📋 Meeting topic: {meeting_params.get('topic', 'N/A')}")
        logger.info(f"   ⏱️  Duration: {meeting_params.get('duration_minutes', 30)} minutes")
        logger.info(f"   🎯 Constraints: {meeting_params.get('time_constraints', 'flexible')}")
        logger.info(f"   👥 Participants: {', '.join(meeting_params.get('participants', []))}")
        
        # 🚨 NEW: Check if this is a high priority meeting
        priority = meeting_params.get('priority', 'normal')
        logger.info(f"   🎖️  Priority: {priority.upper()}")
        
        if priority == "high":
            logger.info(f"🚨 HIGH PRIORITY SCHEDULING - Will reschedule conflicts if needed")
            return self._priority_based_scheduling(meeting_params, calendar_data)
        else:
            logger.info(f"📅 NORMAL PRIORITY SCHEDULING - Finding available slots")
            return self._normal_priority_scheduling(meeting_params, calendar_data)

    def _priority_based_scheduling(self, meeting_params: Dict[str, Any], 
                                 calendar_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """High priority scheduling - can reschedule existing meetings"""
        
        logger.info(f"🚨 PRIORITY SCHEDULING - Finding preferred time and handling conflicts")
        
        duration = meeting_params.get('duration_minutes', 30)
        time_constraints = meeting_params.get('time_constraints', 'flexible')
        
        # Find the preferred time slot based on constraints
        preferred_slot = self._find_preferred_time_slot(time_constraints, duration)
        
        if not preferred_slot:
            logger.warning(f"❌ Could not determine preferred slot, falling back to normal scheduling")
            return self._normal_priority_scheduling(meeting_params, calendar_data)
        
        preferred_start, preferred_end = preferred_slot
        logger.info(f"🎯 PREFERRED SLOT: {preferred_start} to {preferred_end}")
        
        # Check for conflicts with existing meetings
        conflicts = self._find_conflicts(preferred_start, preferred_end, calendar_data)
        
        if not conflicts:
            logger.info(f"✅ No conflicts found - scheduling at preferred time")
            return {
                'start_time': preferred_start,
                'end_time': preferred_end,
                'reasoning': 'High priority meeting scheduled at preferred time with no conflicts'
            }
        
        # Handle conflicts by rescheduling existing meetings
        logger.info(f"⚠️  Found {len(conflicts)} conflicting meetings - attempting to reschedule them")
        
        rescheduled_meetings = []
        for conflict in conflicts:
            alternative_slot = self._find_alternative_slot_for_meeting(conflict, calendar_data)
            if alternative_slot:
                rescheduled_meetings.append({
                    'original': conflict,
                    'new_slot': alternative_slot
                })
                logger.info(f"📅 Rescheduled '{conflict['summary']}' to {alternative_slot[0]} - {alternative_slot[1]}")
            else:
                logger.warning(f"⚠️  Could not reschedule '{conflict['summary']}' - may need manual intervention")
        
        # Update calendar data with rescheduled meetings
        self._apply_rescheduling(calendar_data, rescheduled_meetings)
        
        return {
            'start_time': preferred_start,
            'end_time': preferred_end,
            'reasoning': f'High priority meeting scheduled - rescheduled {len(rescheduled_meetings)} conflicting meetings',
            'rescheduled_count': len(rescheduled_meetings)
        }

    def _normal_priority_scheduling(self, meeting_params: Dict[str, Any], 
                                  calendar_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Normal priority scheduling - existing logic"""
        
        current_time = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        # Try AI-based scheduling first
        try:
            logger.info(f"🤖 Attempting AI-based scheduling...")
            ai_result = self.llm_client.find_optimal_meeting_time(
                meeting_params, calendar_data, current_time
            )
            
            # Validate AI result
            if self._validate_meeting_time(ai_result, calendar_data, meeting_params):
                proposed_start = ai_result.get('start_time')
                proposed_end = ai_result.get('end_time')
                
                # Check if proposed time is off hours
                if proposed_start:
                    start_dt = datetime.fromisoformat(proposed_start.replace('+05:30', ''))
                    is_off_hours = (start_dt.hour < self.config.BUSINESS_HOURS_START or 
                                   start_dt.hour >= self.config.BUSINESS_HOURS_END or
                                   start_dt.weekday() >= 5)
                    
                    if is_off_hours:
                        logger.info(f"🌙 AI proposed OFF HOURS meeting time: {proposed_start} to {proposed_end}")
                    else:
                        logger.info(f"🏢 AI proposed BUSINESS HOURS meeting time: {proposed_start} to {proposed_end}")
                
                logger.info(f"✅ Using AI-recommended meeting time")
                logger.info(f"   Reasoning: {ai_result.get('reasoning', 'No reasoning provided')}")
                return ai_result
            else:
                logger.warning("❌ AI-recommended time has conflicts, falling back to algorithmic approach")
        
        except Exception as e:
            logger.warning(f"❌ AI scheduling failed: {e}, using algorithmic approach")
        
        # Fallback to algorithmic approach
        logger.info(f"🔄 Using algorithmic scheduling approach...")
        return self._algorithmic_scheduling(meeting_params, calendar_data)
    
    def _validate_meeting_time(self, proposed_time: Dict[str, Any], 
                             calendar_data: Dict[str, List[Dict]], 
                             meeting_params: Dict[str, Any]) -> bool:
        """Validate that proposed meeting time doesn't conflict with existing events"""
        
        start_time = proposed_time.get('start_time')
        end_time = proposed_time.get('end_time')
        
        if not start_time or not end_time:
            return False
        
        # Check conflicts for each participant
        for email, events in calendar_data.items():
            for event in events:
                event_start = event['StartTime']
                event_end = event['EndTime']
                
                # Check for time overlap
                if self._times_overlap(start_time, end_time, event_start, event_end):
                    logger.warning(f"Conflict detected for {email}: {event['Summary']}")
                    return False
        
        return True
    
    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Check if two time ranges overlap"""
        try:
            dt_start1 = datetime.fromisoformat(start1.replace('+05:30', ''))
            dt_end1 = datetime.fromisoformat(end1.replace('+05:30', ''))
            dt_start2 = datetime.fromisoformat(start2.replace('+05:30', ''))
            dt_end2 = datetime.fromisoformat(end2.replace('+05:30', ''))
            
            return dt_start1 < dt_end2 and dt_end1 > dt_start2
        
        except Exception:
            return False
    
    def _algorithmic_scheduling(self, meeting_params: Dict[str, Any], 
                              calendar_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Algorithmic approach to find meeting time"""
        
        duration = meeting_params.get('duration_minutes', 30)
        attendees = list(calendar_data.keys())
        
        # Get common free slots
        time_constraints = meeting_params.get('time_constraints', 'flexible')
        start_date, end_date = self._parse_time_constraints(time_constraints)
        
        common_slots = self.calendar_manager.find_common_free_slots(
            attendees, start_date, end_date, duration
        )
        
        if common_slots:
            # Pick the first available slot and log if it's off hours
            start_time, end_time = common_slots[0]
            start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
            is_off_hours = (start_dt.hour < self.config.BUSINESS_HOURS_START or 
                           start_dt.hour >= self.config.BUSINESS_HOURS_END or
                           start_dt.weekday() >= 5)
            
            if is_off_hours:
                logger.info(f"🌙 Algorithmic scheduling selected OFF HOURS slot: {start_time} to {end_time}")
            else:
                logger.info(f"🏢 Algorithmic scheduling selected BUSINESS HOURS slot: {start_time} to {end_time}")
            
            return {
                'start_time': start_time,
                'end_time': end_time,
                'reasoning': 'First available common slot'
            }
        else:
            # No common slots found, suggest a default time
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            while tomorrow.weekday() >= 5:  # Skip weekends
                tomorrow += timedelta(days=1)
            
            start_time = tomorrow.replace(hour=10, minute=0, second=0)
            end_time = start_time + timedelta(minutes=duration)
            
            # Check if default time is off hours
            is_off_hours = (start_time.hour < self.config.BUSINESS_HOURS_START or 
                           start_time.hour >= self.config.BUSINESS_HOURS_END or
                           start_time.weekday() >= 5)
            
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
            
            if is_off_hours:
                logger.warning(f"🌙 DEFAULT FALLBACK selected OFF HOURS slot: {start_str} to {end_str}")
            else:
                logger.info(f"🏢 DEFAULT FALLBACK selected BUSINESS HOURS slot: {start_str} to {end_str}")
            
            return {
                'start_time': start_str,
                'end_time': end_str,
                'reasoning': 'No common free time found, suggesting default slot'
            }
    
    def _find_preferred_time_slot(self, time_constraints: str, duration: int) -> Optional[tuple[str, str]]:
        """Find preferred time slot based on constraints"""
        
        constraints_lower = time_constraints.lower().strip()
        now = datetime.now()
        
        if 'thursday' in constraints_lower:
            # Find next Thursday at 9 AM (preferred business start time)
            days_ahead = (3 - now.weekday()) % 7  # Thursday is weekday 3
            if days_ahead == 0:
                if now.hour >= 18:  # Past business hours
                    days_ahead = 7
                elif now.hour >= 9:  # Same day but need future time
                    days_ahead = 7
            if days_ahead == 0:
                days_ahead = 7
                
            next_thursday = now + timedelta(days=days_ahead)
            preferred_start = next_thursday.replace(hour=9, minute=0, second=0, microsecond=0)
            
        elif 'monday' in constraints_lower:
            days_ahead = (0 - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= 9:
                days_ahead = 7
            next_monday = now + timedelta(days=days_ahead)
            preferred_start = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
            
        elif 'tuesday' in constraints_lower:
            days_ahead = (1 - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= 9:
                days_ahead = 7
            next_tuesday = now + timedelta(days=days_ahead)
            preferred_start = next_tuesday.replace(hour=9, minute=0, second=0, microsecond=0)
            
        elif 'wednesday' in constraints_lower:
            days_ahead = (2 - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= 9:
                days_ahead = 7
            next_wednesday = now + timedelta(days=days_ahead)
            preferred_start = next_wednesday.replace(hour=9, minute=0, second=0, microsecond=0)
            
        elif 'friday' in constraints_lower:
            days_ahead = (4 - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= 9:
                days_ahead = 7
            next_friday = now + timedelta(days=days_ahead)
            preferred_start = next_friday.replace(hour=9, minute=0, second=0, microsecond=0)
            
        elif 'tomorrow' in constraints_lower:
            tomorrow = now + timedelta(days=1)
            preferred_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            
        else:
            # Default: next business day at 9 AM
            tomorrow = now + timedelta(days=1)
            while tomorrow.weekday() >= 5:  # Skip weekends
                tomorrow += timedelta(days=1)
            preferred_start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        preferred_end = preferred_start + timedelta(minutes=duration)
        
        return (
            preferred_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            preferred_end.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        )

    def _find_conflicts(self, start_time: str, end_time: str, 
                       calendar_data: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Find conflicting meetings in the given time slot"""
        
        conflicts = []
        
        for email, events in calendar_data.items():
            for event in events:
                if self._times_overlap(start_time, end_time, event['StartTime'], event['EndTime']):
                    conflicts.append({
                        'email': email,
                        'event': event,
                        'summary': event.get('Summary', 'Unknown Meeting'),
                        'start': event['StartTime'],
                        'end': event['EndTime']
                    })
        
        return conflicts

    def _find_alternative_slot_for_meeting(self, conflict: Dict[str, Any], 
                                         calendar_data: Dict[str, List[Dict]]) -> Optional[tuple[str, str]]:
        """Find an alternative slot for a conflicting meeting"""
        
        original_start = datetime.fromisoformat(conflict['start'].replace('+05:30', ''))
        original_end = datetime.fromisoformat(conflict['end'].replace('+05:30', ''))
        duration_minutes = int((original_end - original_start).total_seconds() / 60)
        
        # Try to find a slot on the same day first
        same_day_slots = self._find_available_slots_on_date(
            original_start.date(), duration_minutes, calendar_data, exclude_conflict=conflict
        )
        
        if same_day_slots:
            logger.info(f"📅 Found alternative slot on same day for '{conflict['summary']}'")
            return same_day_slots[0]
        
        # Try next few days
        for days_offset in range(1, 8):
            target_date = original_start.date() + timedelta(days=days_offset)
            if target_date.weekday() < 5:  # Weekdays only
                slots = self._find_available_slots_on_date(
                    target_date, duration_minutes, calendar_data
                )
                if slots:
                    logger.info(f"📅 Found alternative slot {days_offset} days later for '{conflict['summary']}'")
                    return slots[0]
        
        return None

    def _find_available_slots_on_date(self, target_date, duration_minutes: int, 
                                    calendar_data: Dict[str, List[Dict]], 
                                    exclude_conflict: Dict[str, Any] = None) -> List[tuple[str, str]]:
        """Find available slots on a specific date"""
        
        # Create time slots for business hours (9 AM to 6 PM)
        start_hour = 9
        end_hour = 18
        slot_duration = 30  # Check in 30-minute increments
        
        available_slots = []
        
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                if hour == end_hour - 1 and minute == 30:  # Don't go past 6 PM
                    break
                    
                slot_start = datetime.combine(target_date, datetime.min.time()).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                # Check if this slot is free for all participants
                is_free = True
                for email, events in calendar_data.items():
                    for event in events:
                        # Skip the conflict we're trying to reschedule
                        if exclude_conflict and event == exclude_conflict.get('event'):
                            continue
                            
                        if self._times_overlap(
                            slot_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                            slot_end.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                            event['StartTime'],
                            event['EndTime']
                        ):
                            is_free = False
                            break
                    if not is_free:
                        break
                
                if is_free:
                    available_slots.append((
                        slot_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                        slot_end.strftime('%Y-%m-%dT%H:%M:%S+05:30')
                    ))
        
        return available_slots

    def _apply_rescheduling(self, calendar_data: Dict[str, List[Dict]], 
                           rescheduled_meetings: List[Dict[str, Any]]) -> None:
        """Apply rescheduling changes to calendar data"""
        
        for reschedule in rescheduled_meetings:
            original = reschedule['original']
            new_slot = reschedule['new_slot']
            
            # Find and update the original event
            for email, events in calendar_data.items():
                if email == original['email']:
                    for i, event in enumerate(events):
                        if (event['StartTime'] == original['start'] and 
                            event['EndTime'] == original['end'] and
                            event.get('Summary') == original['summary']):
                            
                            # Update the event times
                            events[i]['StartTime'] = new_slot[0]
                            events[i]['EndTime'] = new_slot[1]
                            
                            logger.info(f"✅ Updated calendar for {email}: moved '{original['summary']}' to {new_slot[0]}")
                            break
    
    def _format_output(self, request_data: Dict[str, Any], 
                     calendar_data: Dict[str, List[Dict]], 
                     optimal_time: Dict[str, Any], 
                     meeting_params: Dict[str, Any]) -> Dict[str, Any]:
        """Format output according to hackathon requirements"""
        
        # Start with original request data
        output_data = request_data.copy()
        
        # Add calendar events for each attendee
        attendees_output = []
        for email in calendar_data.keys():
            attendee_data = {
                "email": email,
                "events": calendar_data[email]
            }
            attendees_output.append(attendee_data)
        
        # Add new meeting event to each attendee's calendar
        new_event = {
            "StartTime": optimal_time['start_time'],
            "EndTime": optimal_time['end_time'],
            "NumAttendees": len(calendar_data),
            "Attendees": list(calendar_data.keys()),
            "Summary": request_data.get("Subject", meeting_params.get('topic', 'Meeting'))
        }
        
        # Log the final scheduled meeting details
        start_dt = datetime.fromisoformat(optimal_time['start_time'].replace('+05:30', ''))
        is_off_hours = (start_dt.hour < self.config.BUSINESS_HOURS_START or 
                       start_dt.hour >= self.config.BUSINESS_HOURS_END or
                       start_dt.weekday() >= 5)
        
        logger.info(f"📅 FINAL SCHEDULED MEETING:")
        logger.info(f"   📋 Subject: {new_event['Summary']}")
        logger.info(f"   ⏰ Time: {new_event['StartTime']} to {new_event['EndTime']}")
        logger.info(f"   👥 Attendees: {', '.join(new_event['Attendees'])}")
        logger.info(f"   📊 Total participants: {new_event['NumAttendees']}")
        
        if is_off_hours:
            logger.info(f"   🌙 SCHEDULED DURING OFF HOURS")
        else:
            logger.info(f"   🏢 SCHEDULED DURING BUSINESS HOURS")
        
        logger.info(f"   🎯 Scheduling method: {optimal_time.get('reasoning', 'Unknown')}")
        
        for attendee_data in attendees_output:
            attendee_data["events"].append(new_event)
        
        # Update output data
        output_data["Attendees"] = attendees_output
        output_data["EventStart"] = optimal_time['start_time']
        output_data["EventEnd"] = optimal_time['end_time']
        output_data["Duration_mins"] = str(meeting_params.get('duration_minutes', 30))
        output_data["MetaData"] = {
            "scheduling_method": optimal_time.get('reasoning', 'AI-assisted'),
            "processing_timestamp": datetime.now().isoformat()
        }
        
        return output_data
    
    def _create_fallback_response(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback response in case of errors"""
        
        # Default meeting time: tomorrow at 10 AM for 30 minutes
        tomorrow = datetime.now() + timedelta(days=1)
        while tomorrow.weekday() >= 5:  # Skip weekends
            tomorrow += timedelta(days=1)
        
        start_time = tomorrow.replace(hour=10, minute=0, second=0)
        end_time = start_time + timedelta(minutes=30)
        
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        # Create minimal response structure
        fallback_data = request_data.copy()
        
        # Create basic attendees structure
        attendees_list = []
        organizer = request_data.get("From", "")
        attendee_emails = [att.get("email") for att in request_data.get("Attendees", [])]
        all_attendees = [organizer] + attendee_emails
        all_attendees = list(set(all_attendees))
        
        for email in all_attendees:
            attendees_list.append({
                "email": email,
                "events": [{
                    "StartTime": start_str,
                    "EndTime": end_str,
                    "NumAttendees": len(all_attendees),
                    "Attendees": all_attendees,
                    "Summary": request_data.get("Subject", "Meeting")
                }]
            })
        
        fallback_data["Attendees"] = attendees_list
        fallback_data["EventStart"] = start_str
        fallback_data["EventEnd"] = end_str
        fallback_data["Duration_mins"] = "30"
        fallback_data["MetaData"] = {
            "scheduling_method": "fallback",
            "error": "Processing failed, using default scheduling"
        }
        
        return fallback_data