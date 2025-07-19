#!/usr/bin/env python3
"""
Simple test to verify Smart Calendar works with Llama-3.2-3B completions endpoint
"""

import sys
import os
import json
from pathlib import Path

# Add smart-calendar to path
smart_calendar_path = Path(__file__).parent.parent
sys.path.insert(0, str(smart_calendar_path))

def test_llm_client():
    """Test LLM client directly"""
    print("🧪 Testing Smart Calendar LLM Client...")
    
    try:
        from src.ai_agent.llm_client import LLMClient
        
        # Initialize LLM client
        llm_client = LLMClient()
        
        # Test email parsing
        print("\n📧 Testing email parsing...")
        email_content = "Hi team, let's meet tomorrow for 1 hour to discuss the AI project with John and Mary."
        
        result = llm_client.parse_email_content(email_content)
        
        print(f"✅ Email parsing result:")
        print(f"   Participants: {result.get('participants', [])}")
        print(f"   Duration: {result.get('duration_minutes', 0)} minutes")
        print(f"   Time constraints: {result.get('time_constraints', 'N/A')}")
        print(f"   Topic: {result.get('topic', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM client test failed: {e}")
        return False

def test_full_request():
    """Test a complete meeting request"""
    print("\n🎯 Testing complete meeting request...")
    
    try:
        from main import your_meeting_assistant
        
        # Test request data - using only available token users
        test_request = {
            "Request_id": "test-001",
            "Datetime": "20-07-2025T12:34:55",
            "Location": "Test Location",
            "From": "userone.amd@gmail.com",
            "Attendees": [
                {"email": "usertwo.amd@gmail.com"},
                {"email": "userthree.amd@gmail.com"}
            ],
            "Subject": "AI Project Meeting",
            "EmailContent": "Let's meet tomorrow for 30 minutes to discuss the AI project progress."
        }
        
        print("📤 Sending test request...")
        result = your_meeting_assistant(test_request)
        
        print("✅ Request processed successfully!")
        print(f"   Request ID: {result.get('Request_id', 'N/A')}")
        print(f"   Event Start: {result.get('EventStart', 'N/A')}")
        print(f"   Event End: {result.get('EventEnd', 'N/A')}")
        print(f"   Duration: {result.get('Duration_mins', 'N/A')} minutes")
        
        # Check if response has required fields
        required_fields = ["Request_id", "EventStart", "EventEnd", "Duration_mins", "Attendees"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            print(f"⚠️  Missing fields: {missing_fields}")
        else:
            print("✅ All required fields present")
        
        return True
        
    except Exception as e:
        print(f"❌ Full request test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test execution"""
    print("🤖 Smart Calendar Simple Test")
    print("=" * 40)
    
    # Test 1: LLM Client
    llm_success = test_llm_client()
    
    # Test 2: Full Request
    full_success = test_full_request()
    
    print("\n📊 Test Summary:")
    print(f"   LLM Client: {'✅ PASS' if llm_success else '❌ FAIL'}")
    print(f"   Full Request: {'✅ PASS' if full_success else '❌ FAIL'}")
    
    if llm_success and full_success:
        print("\n🎉 All tests passed! Smart Calendar is working with Llama-3.2-3B")
        return True
    else:
        print("\n❌ Some tests failed. Check the logs above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)