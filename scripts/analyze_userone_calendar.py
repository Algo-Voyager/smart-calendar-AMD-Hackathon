#!/usr/bin/env python3
"""
Quick script to analyze userone.amd@gmail.com calendar
"""

import sys
import os
from pathlib import Path

# Add smart-calendar to path
smart_calendar_path = Path(__file__).parent.parent
sys.path.insert(0, str(smart_calendar_path))

from utils.calendar_slot_analyzer import CalendarSlotAnalyzer

def main():
    """Analyze userone.amd@gmail.com calendar"""
    
    print("🤖 Smart Calendar - User Analysis Tool")
    print("=" * 50)
    
    analyzer = CalendarSlotAnalyzer()
    
    # Analyze userone.amd@gmail.com for the next 7 days
    email = "userone.amd@gmail.com"
    days = 7
    
    print(f"Analyzing {email} for the next {days} days...")
    
    try:
        analysis = analyzer.analyze_user_calendar(email, days)
        
        if analysis:
            print(f"\n🎉 Analysis completed successfully!")
            print(f"   📊 Found {analysis['total_events']} total events")
            print(f"   📋 {len(analysis['scheduled_meetings'])} scheduled meetings")
            print(f"   🌙 {len(analysis['off_hours_blocks'])} off-hours blocks")
            print(f"   ✅ {len(analysis['available_slots'])} available time slots")
        else:
            print(f"\n❌ Analysis failed or returned no data")
            
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()