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

logger = logging.getLogger(__name__)

class SmartScheduler:
    """
    Main scheduling coordinator that orchestrates the entire scheduling process
    """
    
    def __init__(self, model_name: str = None):
        self.config = Config()
        self.calendar_manager = CalendarManager()
        self.llm_client = LLMClient(model_name)
        
        logger.info("SmartScheduler initialized")
    
    def process_meeting_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing meeting requests
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
            calendar_data = self._get_calendar_data_for_attendees(
                all_attendees, meeting_params.get('time_constraints', 'flexible')
            )
            
            # Step 3: Find optimal meeting time
            optimal_time = self._find_optimal_meeting_time(meeting_params, calendar_data)
            
            # Step 4: Format output according to hackathon requirements
            output_data = self._format_output(
                request_data, 
                calendar_data, 
                optimal_time, 
                meeting_params
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Request processed in {processing_time:.2f} seconds")
            
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
        
        constraints_lower = time_constraints.lower()
        
        if 'next week' in constraints_lower:
            # Start from next Monday
            days_ahead = 7 - now.weekday()
            start_date = now + timedelta(days=days_ahead)
            end_date = start_date + timedelta(days=7)
        elif 'tomorrow' in constraints_lower:
            start_date = now + timedelta(days=1)
            end_date = start_date + timedelta(days=1)
        elif 'today' in constraints_lower:
            start_date = now
            end_date = now + timedelta(days=1)
        elif 'this week' in constraints_lower:
            # Rest of this week
            start_date = now
            days_until_sunday = 6 - now.weekday()
            end_date = now + timedelta(days=days_until_sunday)
        elif any(day in constraints_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            # Specific day - find next occurrence
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            target_day = None
            for day in days:
                if day in constraints_lower:
                    target_day = days.index(day)
                    break
            
            if target_day is not None:
                days_ahead = (target_day - now.weekday()) % 7
                if days_ahead == 0:  # If it's today, move to next week
                    days_ahead = 7
                start_date = now + timedelta(days=days_ahead)
                end_date = start_date + timedelta(days=1)
            else:
                # Default case
                start_date = now + timedelta(days=1)
                end_date = start_date + timedelta(days=7)
        else:
            # Default: next 7 days
            start_date = now + timedelta(days=1)
            end_date = start_date + timedelta(days=7)
        
        # Format for Google Calendar API
        start_str = start_date.strftime('%Y-%m-%dT00:00:00+05:30')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59+05:30')
        
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
        
        # Try AI-based scheduling first
        try:
            logger.info(f"🤖 Attempting AI-based scheduling with Llama-3.2-3B...")
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