"""
Specialized logging utilities for meeting scheduling and off-hours tracking
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

class MeetingLogger:
    """Specialized logger for meeting scheduling events"""
    
    @staticmethod
    def log_member_meetings_before_scheduling(member_email: str, meetings: List[Dict], 
                                            business_hours_start: int = 9, 
                                            business_hours_end: int = 18):
        """Log all existing meetings for a member before scheduling"""
        
        logger.info(f"📋 MEMBER ANALYSIS - {member_email}")
        logger.info(f"   📊 Total existing meetings: {len(meetings)}")
        
        if not meetings:
            logger.info(f"   ✅ No existing meetings found for {member_email}")
            return
        
        off_hours_meetings = []
        business_hours_meetings = []
        
        for meeting in meetings:
            start_time = meeting.get('StartTime', '')
            try:
                start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
                is_off_hours = (start_dt.hour < business_hours_start or 
                               start_dt.hour >= business_hours_end or
                               start_dt.weekday() >= 5)  # Weekend
                
                if is_off_hours:
                    off_hours_meetings.append(meeting)
                else:
                    business_hours_meetings.append(meeting)
            except Exception:
                # If parsing fails, treat as business hours
                business_hours_meetings.append(meeting)
        
        # Log business hours meetings
        logger.info(f"   🏢 BUSINESS HOURS MEETINGS ({len(business_hours_meetings)}):")
        for i, meeting in enumerate(business_hours_meetings, 1):
            logger.info(f"      {i}. {meeting.get('Summary', 'Untitled')}")
            logger.info(f"         Time: {meeting.get('StartTime', 'N/A')} to {meeting.get('EndTime', 'N/A')}")
            logger.info(f"         Attendees: {', '.join(meeting.get('Attendees', ['Unknown']))}")
        
        # Log off hours meetings
        if off_hours_meetings:
            logger.info(f"   🌙 OFF HOURS MEETINGS ({len(off_hours_meetings)}):")
            for i, meeting in enumerate(off_hours_meetings, 1):
                logger.info(f"      {i}. {meeting.get('Summary', 'Untitled')}")
                logger.info(f"         Time: {meeting.get('StartTime', 'N/A')} to {meeting.get('EndTime', 'N/A')}")
                logger.info(f"         Attendees: {', '.join(meeting.get('Attendees', ['Unknown']))}")
                
                # Determine specific off-hours reason
                try:
                    start_dt = datetime.fromisoformat(meeting.get('StartTime', '').replace('+05:30', ''))
                    if start_dt.weekday() >= 5:
                        logger.info(f"         🗓️  Reason: Weekend meeting")
                    elif start_dt.hour < business_hours_start:
                        logger.info(f"         🌅 Reason: Early morning ({start_dt.hour}:00)")
                    elif start_dt.hour >= business_hours_end:
                        logger.info(f"         🌆 Reason: Evening/night ({start_dt.hour}:00)")
                except Exception:
                    logger.info(f"         ❓ Reason: Unknown")
        else:
            logger.info(f"   ✅ No off-hours meetings found")
    
    @staticmethod
    def log_consolidated_team_analysis(team_calendar_data: Dict[str, List[Dict]], 
                                     business_hours_start: int = 9, 
                                     business_hours_end: int = 18):
        """Log consolidated analysis of all team members' calendars"""
        
        logger.info(f"👥 TEAM CALENDAR ANALYSIS (Before Scheduling)")
        logger.info(f"   📊 Team size: {len(team_calendar_data)} members")
        
        total_meetings = 0
        total_off_hours = 0
        total_business_hours = 0
        member_stats = {}
        
        for member_email, meetings in team_calendar_data.items():
            off_hours_count = 0
            business_hours_count = 0
            
            for meeting in meetings:
                try:
                    start_time = meeting.get('StartTime', '')
                    start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
                    is_off_hours = (start_dt.hour < business_hours_start or 
                                   start_dt.hour >= business_hours_end or
                                   start_dt.weekday() >= 5)
                    
                    if is_off_hours:
                        off_hours_count += 1
                    else:
                        business_hours_count += 1
                except Exception:
                    business_hours_count += 1  # Default to business hours if parsing fails
            
            member_stats[member_email] = {
                'total': len(meetings),
                'business_hours': business_hours_count,
                'off_hours': off_hours_count
            }
            
            total_meetings += len(meetings)
            total_off_hours += off_hours_count
            total_business_hours += business_hours_count
        
        # Log individual member statistics
        logger.info(f"📈 INDIVIDUAL MEMBER STATS:")
        for member_email, stats in member_stats.items():
            logger.info(f"   {member_email}: {stats['total']} total "
                       f"({stats['business_hours']} business, {stats['off_hours']} off-hours)")
        
        # Log team totals
        logger.info(f"📊 TEAM TOTALS:")
        logger.info(f"   📅 Total meetings: {total_meetings}")
        logger.info(f"   🏢 Business hours meetings: {total_business_hours}")
        logger.info(f"   🌙 Off hours meetings: {total_off_hours}")
        
        if total_meetings > 0:
            off_hours_percentage = (total_off_hours / total_meetings) * 100
            logger.info(f"   📈 Off-hours percentage: {off_hours_percentage:.1f}%")
        
        # Identify members with most off-hours meetings
        if total_off_hours > 0:
            max_off_hours = max(stats['off_hours'] for stats in member_stats.values())
            members_with_most_off_hours = [
                email for email, stats in member_stats.items() 
                if stats['off_hours'] == max_off_hours
            ]
            logger.info(f"   🌙 Members with most off-hours meetings: {', '.join(members_with_most_off_hours)} ({max_off_hours} meetings)")
    
    @staticmethod
    def log_scheduling_decision(proposed_time: Dict[str, Any], method: str,
                              business_hours_start: int = 9, 
                              business_hours_end: int = 18):
        """Log the final scheduling decision with off-hours analysis"""
        
        start_time = proposed_time.get('start_time', '')
        end_time = proposed_time.get('end_time', '')
        reasoning = proposed_time.get('reasoning', 'No reasoning provided')
        
        logger.info(f"🎯 SCHEDULING DECISION:")
        logger.info(f"   ⏰ Proposed time: {start_time} to {end_time}")
        logger.info(f"   🔧 Method: {method}")
        logger.info(f"   💭 Reasoning: {reasoning}")
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
            is_off_hours = (start_dt.hour < business_hours_start or 
                           start_dt.hour >= business_hours_end or
                           start_dt.weekday() >= 5)
            
            if is_off_hours:
                logger.info(f"   🌙 DECISION: Scheduled during OFF HOURS")
                
                # Specify the type of off-hours
                if start_dt.weekday() >= 5:
                    logger.info(f"      📅 Type: Weekend meeting")
                elif start_dt.hour < business_hours_start:
                    logger.info(f"      🌅 Type: Early morning meeting ({start_dt.hour}:00)")
                elif start_dt.hour >= business_hours_end:
                    logger.info(f"      🌆 Type: Evening meeting ({start_dt.hour}:00)")
                
                logger.warning(f"   ⚠️  ATTENTION: Meeting scheduled outside business hours!")
            else:
                logger.info(f"   🏢 DECISION: Scheduled during BUSINESS HOURS")
                logger.info(f"   ✅ Time slot respects business hours constraints")
        
        except Exception as e:
            logger.error(f"   ❌ Failed to analyze scheduling time: {e}")
    
    @staticmethod
    def log_request_summary(request_data: Dict[str, Any], result_data: Dict[str, Any], 
                          processing_time: float):
        """Log a comprehensive summary of the request processing"""
        
        request_id = request_data.get('Request_id', 'Unknown')
        
        logger.info(f"📋 REQUEST PROCESSING SUMMARY")
        logger.info(f"   🆔 Request ID: {request_id}")
        logger.info(f"   📧 Organizer: {request_data.get('From', 'N/A')}")
        logger.info(f"   👥 Attendees: {len(request_data.get('Attendees', []))} people")
        logger.info(f"   📋 Subject: {request_data.get('Subject', 'N/A')}")
        logger.info(f"   ⏱️  Processing time: {processing_time:.2f} seconds")
        
        # Final scheduling result
        event_start = result_data.get('EventStart', '')
        event_end = result_data.get('EventEnd', '')
        duration = result_data.get('Duration_mins', 'N/A')
        
        logger.info(f"   📅 Final schedule: {event_start} to {event_end}")
        logger.info(f"   ⏰ Duration: {duration} minutes")
        
        # Off-hours check for final result
        try:
            if event_start:
                start_dt = datetime.fromisoformat(event_start.replace('+05:30', ''))
                is_off_hours = (start_dt.hour < 9 or start_dt.hour >= 18 or start_dt.weekday() >= 5)
                
                if is_off_hours:
                    logger.info(f"   🌙 FINAL STATUS: Meeting scheduled during OFF HOURS")
                else:
                    logger.info(f"   🏢 FINAL STATUS: Meeting scheduled during BUSINESS HOURS")
        except Exception:
            logger.info(f"   ❓ FINAL STATUS: Could not determine business/off hours")
        
        # Success/failure status
        if event_start and event_end:
            logger.info(f"   ✅ STATUS: Successfully scheduled")
        else:
            logger.error(f"   ❌ STATUS: Failed to schedule meeting")
        
        logger.info(f"📋 End of request summary for {request_id}")
        logger.info("=" * 60)