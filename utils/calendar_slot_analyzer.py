#!/usr/bin/env python3
"""
Calendar Slot Analyzer - Utility to analyze user calendar slots
Shows scheduled meetings, off-hours, and available time slots for debugging
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Add smart-calendar to path
smart_calendar_path = Path(__file__).parent.parent
sys.path.insert(0, str(smart_calendar_path))

from config.settings import Config
from src.calendar.calendar_manager import CalendarManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CalendarSlotAnalyzer:
    """Analyze calendar slots for a specific user"""
    
    def __init__(self):
        self.config = Config()
        self.calendar_manager = CalendarManager()
    
    def analyze_user_calendar(self, email: str, days_ahead: int = 7) -> Dict[str, Any]:
        """
        Analyze a user's calendar for the next N days
        Returns detailed breakdown of scheduled meetings, off-hours, and available slots
        """
        
        print(f"\n🔍 CALENDAR ANALYSIS FOR: {email}")
        print("=" * 60)
        
        # Validate user has token
        if email not in self.config.AVAILABLE_USERS:
            print(f"❌ User {email} is not in available users list")
            print(f"Available users: {self.config.AVAILABLE_USERS}")
            return {}
        
        # Generate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)
        
        start_str = start_date.strftime('%Y-%m-%dT00:00:00+05:30')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59+05:30')
        
        print(f"📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days_ahead} days)")
        print(f"🕒 Business Hours: {self.config.BUSINESS_HOURS_START}:00 AM - {self.config.BUSINESS_HOURS_END}:00 PM")
        
        try:
            # Get calendar events
            events = self.calendar_manager.get_user_events(email, start_str, end_str)
            
            # Analyze the calendar
            analysis = self._analyze_calendar_events(events, start_date, end_date)
            
            # Display analysis
            self._display_analysis(analysis, email)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing calendar for {email}: {e}")
            return {}
    
    def _analyze_calendar_events(self, events: List, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze calendar events and categorize them"""
        
        scheduled_meetings = []
        off_hours_blocks = []
        business_hours_meetings = []
        
        for event in events:
            event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
            
            # Parse event time
            try:
                event_start = datetime.fromisoformat(event_dict['StartTime'].replace('+05:30', ''))
                event_end = datetime.fromisoformat(event_dict['EndTime'].replace('+05:30', ''))
            except:
                continue
            
            # Calculate duration
            duration_minutes = int((event_end - event_start).total_seconds() / 60)
            
            event_analysis = {
                'summary': event_dict.get('Summary', 'No Title'),
                'start_time': event_dict['StartTime'],
                'end_time': event_dict['EndTime'],
                'duration_minutes': duration_minutes,
                'attendees': event_dict.get('Attendees', []),
                'num_attendees': event_dict.get('NumAttendees', 1),
                'day_of_week': event_start.strftime('%A'),
                'date': event_start.strftime('%Y-%m-%d'),
                'start_hour': event_start.hour
            }
            
            # Categorize by type
            if 'off hours' in event_analysis['summary'].lower():
                off_hours_blocks.append(event_analysis)
            else:
                scheduled_meetings.append(event_analysis)
                
                # Further categorize scheduled meetings
                is_business_hours = (
                    self.config.BUSINESS_HOURS_START <= event_start.hour < self.config.BUSINESS_HOURS_END and
                    event_start.weekday() < 5  # Monday=0, Friday=4
                )
                
                if is_business_hours:
                    business_hours_meetings.append(event_analysis)
        
        # Find available time slots
        available_slots = self._find_available_slots(
            scheduled_meetings + off_hours_blocks, start_date, end_date
        )
        
        return {
            'total_events': len(events),
            'scheduled_meetings': scheduled_meetings,
            'off_hours_blocks': off_hours_blocks,
            'business_hours_meetings': business_hours_meetings,
            'available_slots': available_slots,
            'analysis_period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'days': (end_date - start_date).days
            }
        }
    
    def _find_available_slots(self, busy_events: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
        """Find available time slots during business hours"""
        
        available_slots = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_date < end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            # Check each hour during business hours
            for hour in range(self.config.BUSINESS_HOURS_START, self.config.BUSINESS_HOURS_END):
                slot_start = current_date.replace(hour=hour, minute=0)
                slot_end = slot_start + timedelta(hours=1)
                
                # Check if this slot conflicts with any busy event
                is_available = True
                for event in busy_events:
                    try:
                        event_start = datetime.fromisoformat(event['start_time'].replace('+05:30', ''))
                        event_end = datetime.fromisoformat(event['end_time'].replace('+05:30', ''))
                        
                        # Check for overlap
                        if slot_start < event_end and slot_end > event_start:
                            is_available = False
                            break
                    except:
                        continue
                
                if is_available:
                    available_slots.append({
                        'start_time': slot_start.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                        'end_time': slot_end.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                        'duration_minutes': 60,
                        'day_of_week': slot_start.strftime('%A'),
                        'date': slot_start.strftime('%Y-%m-%d'),
                        'hour': hour
                    })
            
            current_date += timedelta(days=1)
        
        return available_slots
    
    def _display_analysis(self, analysis: Dict[str, Any], email: str):
        """Display the calendar analysis in a readable format"""
        
        print(f"\n📊 CALENDAR SUMMARY")
        print(f"   📧 User: {email}")
        print(f"   📅 Period: {analysis['analysis_period']['start']} to {analysis['analysis_period']['end']}")
        print(f"   📝 Total events: {analysis['total_events']}")
        print(f"   📋 Scheduled meetings: {len(analysis['scheduled_meetings'])}")
        print(f"   🏢 Business hours meetings: {len(analysis['business_hours_meetings'])}")
        print(f"   🌙 Off-hours blocks: {len(analysis['off_hours_blocks'])}")
        print(f"   ✅ Available slots (1hr each): {len(analysis['available_slots'])}")
        
        # Show scheduled meetings
        if analysis['scheduled_meetings']:
            print(f"\n📋 SCHEDULED MEETINGS ({len(analysis['scheduled_meetings'])} total):")
            for i, meeting in enumerate(analysis['scheduled_meetings'], 1):
                start_time = meeting['start_time']
                end_time = meeting['end_time']
                duration = meeting['duration_minutes']
                summary = meeting['summary']
                attendees = meeting['attendees']
                
                print(f"   {i}. {summary}")
                print(f"      🕒 {start_time} → {end_time} ({duration} mins)")
                print(f"      👥 Attendees: {', '.join(attendees) if attendees else 'None'}")
                print(f"      📅 {meeting['day_of_week']}, {meeting['date']}")
                
                # Mark if during business hours
                if meeting in analysis['business_hours_meetings']:
                    print(f"      🏢 During business hours")
                else:
                    print(f"      🌙 Outside business hours")
                print()
        
        # Show off-hours blocks
        if analysis['off_hours_blocks']:
            print(f"\n🌙 OFF-HOURS BLOCKS ({len(analysis['off_hours_blocks'])} total):")
            for i, block in enumerate(analysis['off_hours_blocks'], 1):
                print(f"   {i}. {block['summary']}")
                print(f"      🕒 {block['start_time']} → {block['end_time']} ({block['duration_minutes']} mins)")
                print(f"      📅 {block['day_of_week']}, {block['date']}")
                print()
        
        # Show some available slots (limit to first 10 for readability)
        if analysis['available_slots']:
            print(f"\n✅ AVAILABLE TIME SLOTS (showing first 10 of {len(analysis['available_slots'])}):")
            for i, slot in enumerate(analysis['available_slots'][:10], 1):
                print(f"   {i}. {slot['day_of_week']}, {slot['date']} at {slot['hour']:02d}:00")
                print(f"      🕒 {slot['start_time']} → {slot['end_time']}")
                print()
            
            if len(analysis['available_slots']) > 10:
                print(f"   ... and {len(analysis['available_slots']) - 10} more slots")
        else:
            print(f"\n❌ NO AVAILABLE SLOTS FOUND during business hours")
        
        # Daily breakdown
        print(f"\n📅 DAILY BREAKDOWN:")
        daily_stats = {}
        
        # Count meetings per day
        for meeting in analysis['scheduled_meetings']:
            date = meeting['date']
            if date not in daily_stats:
                daily_stats[date] = {'meetings': 0, 'off_hours': 0}
            daily_stats[date]['meetings'] += 1
        
        # Count off-hours per day
        for block in analysis['off_hours_blocks']:
            date = block['date']
            if date not in daily_stats:
                daily_stats[date] = {'meetings': 0, 'off_hours': 0}
            daily_stats[date]['off_hours'] += 1
        
        # Display daily stats
        for date, stats in sorted(daily_stats.items()):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            print(f"   {date} ({day_name}): {stats['meetings']} meetings, {stats['off_hours']} off-hours blocks")


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze calendar slots for a user')
    parser.add_argument('--email', required=True, help='User email to analyze')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of formatted text')
    
    args = parser.parse_args()
    
    analyzer = CalendarSlotAnalyzer()
    
    if args.json:
        import json
        analysis = analyzer.analyze_user_calendar(args.email, args.days)
        print(json.dumps(analysis, indent=2, default=str))
    else:
        analyzer.analyze_user_calendar(args.email, args.days)


if __name__ == "__main__":
    main()