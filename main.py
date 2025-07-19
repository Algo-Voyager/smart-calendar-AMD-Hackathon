#!/usr/bin/env python3
"""
Main entry point for the Smart Calendar Assistant

This script provides the main function for the hackathon submission.
It can be used both as a standalone server and as a library.
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add the smart-calendar directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Config
from src.scheduler.smart_scheduler import SmartScheduler
from src.api.flask_server import SmartCalendarAPI
from utils.logger import SmartCalendarLogger

def your_meeting_assistant(request_data):
    """
    Main function for hackathon submission
    
    This is the function that will be called by the hackathon evaluation system.
    It takes a meeting request JSON and returns a processed response.
    
    Args:
        request_data (dict): Meeting request data in hackathon format
        
    Returns:
        dict: Processed meeting response in hackathon format
    """
    try:
        # Initialize logger
        SmartCalendarLogger.setup_logging(log_level="INFO")
        logger = logging.getLogger(__name__)
        
        logger.info(f"Processing meeting request: {request_data.get('Request_id', 'unknown')}")
        
        # Initialize the smart scheduler
        scheduler = SmartScheduler()
        
        # Process the request
        result = scheduler.process_meeting_request(request_data)
        
        logger.info(f"Request processed successfully")
        return result
        
    except Exception as e:
        # Ensure we always return a valid response even if processing fails
        logger.error(f"Error in your_meeting_assistant: {e}")
        return _create_emergency_fallback(request_data)

def _create_emergency_fallback(request_data):
    """Create emergency fallback response"""
    from datetime import datetime, timedelta
    
    # Basic fallback response
    tomorrow = datetime.now() + timedelta(days=1)
    while tomorrow.weekday() >= 5:  # Skip weekends
        tomorrow += timedelta(days=1)
    
    start_time = tomorrow.replace(hour=10, minute=0, second=0)
    end_time = start_time + timedelta(minutes=30)
    
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
    
    # Get attendees
    organizer = request_data.get("From", "")
    attendee_emails = [att.get("email") for att in request_data.get("Attendees", [])]
    all_attendees = [organizer] + attendee_emails
    all_attendees = list(set(all_attendees))
    
    # Create basic response
    response = request_data.copy()
    
    attendees_list = []
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
    
    response.update({
        "Attendees": attendees_list,
        "EventStart": start_str,
        "EventEnd": end_str,
        "Duration_mins": "30",
        "MetaData": {"emergency_fallback": True}
    })
    
    return response

def run_server(host="0.0.0.0", port=5000, model="llama-3.2-3b"):
    """Run the Flask API server with Llama-3.2-3B"""
    SmartCalendarLogger.setup_logging(log_level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Smart Calendar Assistant with Llama-3.2-3B...")
    
    try:
        # Always use Llama-3.2-3B
        api = SmartCalendarAPI(model_name="llama-3.2-3b")
        api.run(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

def run_tests(api_url="http://localhost:5000"):
    """Run validation tests"""
    from tests.test_client import SmartCalendarTestClient
    
    SmartCalendarLogger.setup_logging(log_level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info(f"Running tests against {api_url}")
    
    client = SmartCalendarTestClient(api_url)
    results = client.run_test_suite()
    
    # Print results
    summary = results["summary"]
    print(f"\nTest Results:")
    print(f"  Total: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success rate: {(summary['passed']/summary['total']*100) if summary['total'] > 0 else 0:.1f}%")
    print(f"  Avg response time: {summary['avg_response_time']:.2f}s")
    
    return results

def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Calendar Assistant')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Server command
    server_parser = subparsers.add_parser('server', help='Run API server with Llama-3.2-3B')
    server_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    server_parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run validation tests')
    test_parser.add_argument('--url', default='http://localhost:5000', help='API URL to test')
    
    # Process command (for single request)
    process_parser = subparsers.add_parser('process', help='Process single request')
    process_parser.add_argument('input_file', help='Input JSON file')
    process_parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    if args.command == 'server':
        run_server(host=args.host, port=args.port)
    
    elif args.command == 'test':
        run_tests(api_url=args.url)
    
    elif args.command == 'process':
        # Process single request
        with open(args.input_file, 'r') as f:
            request_data = json.load(f)
        
        result = your_meeting_assistant(request_data)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()