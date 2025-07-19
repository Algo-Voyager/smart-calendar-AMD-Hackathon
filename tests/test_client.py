"""
Test client for validating the Smart Calendar Assistant
"""
import json
import requests
import time
from typing import Dict, Any
import logging

class SmartCalendarTestClient:
    """Test client for the Smart Calendar API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def test_health_check(self) -> bool:
        """Test health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                self.logger.info("Health check passed")
                return True
            else:
                self.logger.error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return False
    
    def send_meeting_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send meeting request and return response"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/receive",
                json=request_data,
                timeout=15,
                headers={'Content-Type': 'application/json'}
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Request successful (RT: {response_time:.2f}s)")
                return {
                    "success": True,
                    "data": result,
                    "response_time": response_time,
                    "status_code": response.status_code
                }
            else:
                self.logger.error(f"Request failed: {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_time": response_time,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.Timeout:
            self.logger.error("Request timeout")
            return {"success": False, "error": "timeout"}
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_response_format(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate response format against hackathon requirements"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Required fields
        required_fields = [
            "Request_id", "Datetime", "Location", "From", "Attendees",
            "Subject", "EmailContent", "EventStart", "EventEnd", "Duration_mins"
        ]
        
        for field in required_fields:
            if field not in response_data:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Validate Attendees structure
        if "Attendees" in response_data:
            attendees = response_data["Attendees"]
            if not isinstance(attendees, list):
                validation_result["errors"].append("Attendees must be a list")
                validation_result["valid"] = False
            else:
                for i, attendee in enumerate(attendees):
                    if not isinstance(attendee, dict):
                        validation_result["errors"].append(f"Attendee {i} must be a dict")
                        validation_result["valid"] = False
                        continue
                    
                    if "email" not in attendee:
                        validation_result["errors"].append(f"Attendee {i} missing email")
                        validation_result["valid"] = False
                    
                    if "events" not in attendee:
                        validation_result["errors"].append(f"Attendee {i} missing events")
                        validation_result["valid"] = False
                    elif not isinstance(attendee["events"], list):
                        validation_result["errors"].append(f"Attendee {i} events must be list")
                        validation_result["valid"] = False
        
        # Validate datetime formats
        datetime_fields = ["EventStart", "EventEnd"]
        for field in datetime_fields:
            if field in response_data:
                datetime_str = response_data[field]
                import re
                if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+05:30', datetime_str):
                    validation_result["errors"].append(f"Invalid {field} format")
                    validation_result["valid"] = False
        
        return validation_result
    
    def run_test_suite(self, test_data_file: str = None) -> Dict[str, Any]:
        """Run complete test suite"""
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "health_check": False,
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "avg_response_time": 0
            }
        }
        
        # Health check
        results["health_check"] = self.test_health_check()
        
        # Load test data
        test_requests = self._load_test_data(test_data_file)
        
        total_response_time = 0
        
        for i, test_request in enumerate(test_requests):
            self.logger.info(f"Running test {i+1}/{len(test_requests)}")
            
            # Send request
            response = self.send_meeting_request(test_request)
            
            test_result = {
                "test_id": i + 1,
                "request_id": test_request.get("Request_id", f"test_{i+1}"),
                "success": response.get("success", False),
                "response_time": response.get("response_time", 0),
                "validation": {"valid": False}
            }
            
            if response.get("success"):
                # Validate response format
                validation = self.validate_response_format(response["data"])
                test_result["validation"] = validation
                
                if validation["valid"]:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    test_result["success"] = False
            else:
                results["summary"]["failed"] += 1
                test_result["error"] = response.get("error", "Unknown error")
            
            total_response_time += response.get("response_time", 0)
            results["tests"].append(test_result)
            results["summary"]["total"] += 1
        
        # Calculate average response time
        if results["summary"]["total"] > 0:
            results["summary"]["avg_response_time"] = total_response_time / results["summary"]["total"]
        
        return results
    
    def _load_test_data(self, test_data_file: str = None) -> list:
        """Load test data from file or create default test cases"""
        if test_data_file:
            try:
                with open(test_data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load test data: {e}, using defaults")
        
        # Default test cases
        return [
            {
                "Request_id": "test-001",
                "Datetime": "19-07-2025T12:34:55",
                "Location": "IISc Bangalore",
                "From": "userone.amd@gmail.com",
                "Attendees": [
                    {"email": "usertwo.amd@gmail.com"},
                    {"email": "userthree.amd@gmail.com"}
                ],
                "Subject": "AI Project Status Update",
                "EmailContent": "Hi team, let's meet on Thursday for 30 minutes to discuss the AI project status."
            },
            {
                "Request_id": "test-002", 
                "Datetime": "19-07-2025T14:00:00",
                "Location": "Conference Room A",
                "From": "manager@amd.com",
                "Attendees": [
                    {"email": "dev1@amd.com"},
                    {"email": "dev2@amd.com"}
                ],
                "Subject": "Sprint Planning",
                "EmailContent": "Let's schedule our sprint planning for next Monday morning, 1 hour should be enough."
            }
        ]

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Calendar Test Client')
    parser.add_argument('--url', default='http://localhost:5000', help='API base URL')
    parser.add_argument('--test-data', help='Path to test data JSON file')
    parser.add_argument('--output', help='Output file for test results')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create test client
    client = SmartCalendarTestClient(args.url)
    
    # Run tests
    print(f"Running tests against {args.url}")
    results = client.run_test_suite(args.test_data)
    
    # Print summary
    summary = results["summary"]
    print(f"\nTest Results:")
    print(f"  Total tests: {summary['total']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Success rate: {(summary['passed']/summary['total']*100) if summary['total'] > 0 else 0:.1f}%")
    print(f"  Average response time: {summary['avg_response_time']:.2f}s")
    print(f"  Health check: {'✓' if results['health_check'] else '✗'}")
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {args.output}")

if __name__ == '__main__':
    main()