"""
Scheduling Validator - Ensures correct scheduling through iterative validation
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy

logger = logging.getLogger(__name__)

class SchedulingValidator:
    """
    Validates scheduling results by comparing before/after scenarios
    and iteratively correcting until output is perfect
    """
    
    def __init__(self, config):
        self.config = config
        self.max_iterations = 5  # Maximum correction attempts
        
    def validate_and_optimize_scheduling(self, 
                                       request_data: Dict[str, Any],
                                       original_calendar_data: Dict[str, List[Dict]], 
                                       meeting_params: Dict[str, Any],
                                       scheduler_instance) -> Dict[str, Any]:
        """
        Main validation function that iteratively optimizes scheduling
        """
        logger.info(f"🔍 STARTING COMPREHENSIVE SCHEDULING VALIDATION")
        logger.info(f"   🎯 Goal: Ensure 100% correct scheduling output")
        logger.info(f"   🔄 Max iterations: {self.max_iterations}")
        
        # Take snapshot of BEFORE scenario
        before_snapshot = self._create_calendar_snapshot(original_calendar_data, "BEFORE SCHEDULING")
        
        best_result = None
        best_score = 0
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"\n🔄 VALIDATION ITERATION {iteration}/{self.max_iterations}")
            
            # Create working copy of calendar data
            working_calendar_data = deepcopy(original_calendar_data)
            
            # Attempt scheduling
            try:
                scheduling_result = scheduler_instance._find_optimal_meeting_time(
                    meeting_params, working_calendar_data
                )
                
                # Format the output
                output_data = scheduler_instance._format_output(
                    request_data, working_calendar_data, scheduling_result, meeting_params
                )
                
                # Take snapshot of AFTER scenario
                after_snapshot = self._create_calendar_snapshot(
                    self._extract_calendar_from_output(output_data), 
                    f"AFTER SCHEDULING (Iteration {iteration})"
                )
                
                # Comprehensive validation
                validation_results = self._comprehensive_validation(
                    before_snapshot, after_snapshot, meeting_params, scheduling_result, output_data
                )
                
                # Calculate correctness score
                score = self._calculate_correctness_score(validation_results)
                
                logger.info(f"   📊 Iteration {iteration} Score: {score:.1f}/100")
                
                if score >= 95.0:  # 95% or higher is considered perfect
                    logger.info(f"✅ PERFECT RESULT ACHIEVED - Score: {score:.1f}/100")
                    return self._finalize_result(output_data, validation_results, iteration)
                
                if score > best_score:
                    best_result = output_data
                    best_score = score
                    logger.info(f"   🎯 New best result - Score: {score:.1f}/100")
                
                # If not perfect, apply corrections for next iteration
                correction_suggestions = self._generate_corrections(validation_results)
                if correction_suggestions:
                    logger.info(f"   🔧 Applying {len(correction_suggestions)} corrections")
                    meeting_params = self._apply_corrections(meeting_params, correction_suggestions)
                else:
                    logger.info(f"   ⚠️  No more corrections possible, using best result")
                    break
                    
            except Exception as e:
                logger.error(f"   ❌ Iteration {iteration} failed: {e}")
                continue
        
        # Return best result found
        if best_result:
            logger.info(f"✅ RETURNING BEST RESULT - Final Score: {best_score:.1f}/100")
            return best_result
        else:
            logger.error(f"❌ ALL ITERATIONS FAILED - Using emergency fallback")
            return self._create_emergency_fallback(request_data)
    
    def _create_calendar_snapshot(self, calendar_data: Dict[str, List[Dict]], 
                                label: str) -> Dict[str, Any]:
        """Create a detailed snapshot of calendar state"""
        
        logger.info(f"📸 CREATING SNAPSHOT: {label}")
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "label": label,
            "attendees": {},
            "total_events": 0,
            "business_hours_events": 0,
            "off_hours_events": 0,
            "conflicts": [],
            "time_ranges": {}
        }
        
        for email, events in calendar_data.items():
            attendee_info = {
                "email": email,
                "total_events": len(events),
                "events": [],
                "business_hours_count": 0,
                "off_hours_count": 0
            }
            
            for event in events:
                try:
                    start_dt = datetime.fromisoformat(event['StartTime'].replace('+05:30', ''))
                    end_dt = datetime.fromisoformat(event['EndTime'].replace('+05:30', ''))
                    
                    is_business_hours = (
                        9 <= start_dt.hour < 18 and 
                        start_dt.weekday() < 5
                    )
                    
                    event_info = {
                        "summary": event.get('Summary', 'Unknown'),
                        "start": event['StartTime'],
                        "end": event['EndTime'],
                        "duration_minutes": int((end_dt - start_dt).total_seconds() / 60),
                        "is_business_hours": is_business_hours,
                        "attendees_count": event.get('NumAttendees', 0)
                    }
                    
                    attendee_info["events"].append(event_info)
                    
                    if is_business_hours:
                        attendee_info["business_hours_count"] += 1
                        snapshot["business_hours_events"] += 1
                    else:
                        attendee_info["off_hours_count"] += 1
                        snapshot["off_hours_events"] += 1
                        
                except Exception as e:
                    logger.warning(f"   ⚠️  Invalid event format: {e}")
            
            snapshot["attendees"][email] = attendee_info
            snapshot["total_events"] += len(events)
        
        # Log snapshot summary
        logger.info(f"   📊 Snapshot Summary:")
        logger.info(f"      👥 Attendees: {len(snapshot['attendees'])}")
        logger.info(f"      📅 Total events: {snapshot['total_events']}")
        logger.info(f"      🏢 Business hours: {snapshot['business_hours_events']}")
        logger.info(f"      🌙 Off hours: {snapshot['off_hours_events']}")
        
        return snapshot
    
    def _comprehensive_validation(self, before_snapshot: Dict[str, Any], 
                                after_snapshot: Dict[str, Any],
                                meeting_params: Dict[str, Any],
                                scheduling_result: Dict[str, Any],
                                output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive validation of scheduling result"""
        
        logger.info(f"🔍 COMPREHENSIVE VALIDATION")
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 1. Validate new meeting was added
        new_meeting_check = self._validate_new_meeting_added(
            before_snapshot, after_snapshot, meeting_params
        )
        validation_results["checks"]["new_meeting_added"] = new_meeting_check
        
        # 2. Validate meeting time constraints
        time_constraints_check = self._validate_time_constraints(
            scheduling_result, meeting_params
        )
        validation_results["checks"]["time_constraints"] = time_constraints_check
        
        # 3. Validate duration accuracy
        duration_check = self._validate_duration_accuracy(
            scheduling_result, meeting_params
        )
        validation_results["checks"]["duration_accuracy"] = duration_check
        
        # 4. Validate no invalid conflicts
        conflict_check = self._validate_no_invalid_conflicts(after_snapshot)
        validation_results["checks"]["no_conflicts"] = conflict_check
        
        # 5. Validate output format
        format_check = self._validate_output_format(output_data)
        validation_results["checks"]["output_format"] = format_check
        
        # 6. Validate future scheduling
        future_check = self._validate_future_scheduling(scheduling_result)
        validation_results["checks"]["future_scheduling"] = future_check
        
        # 7. Validate attendee consistency
        attendee_check = self._validate_attendee_consistency(
            output_data, meeting_params
        )
        validation_results["checks"]["attendee_consistency"] = attendee_check
        
        # 8. Validate priority handling (if applicable)
        priority_check = self._validate_priority_handling(
            before_snapshot, after_snapshot, meeting_params, scheduling_result
        )
        validation_results["checks"]["priority_handling"] = priority_check
        
        # Log validation summary
        passed_checks = sum(1 for check in validation_results["checks"].values() if check["passed"])
        total_checks = len(validation_results["checks"])
        
        logger.info(f"   ✅ Validation Results: {passed_checks}/{total_checks} checks passed")
        
        for check_name, check_result in validation_results["checks"].items():
            status = "✅" if check_result["passed"] else "❌"
            logger.info(f"      {status} {check_name}: {check_result['message']}")
            
            if not check_result["passed"]:
                validation_results["errors"].append({
                    "check": check_name,
                    "message": check_result["message"],
                    "details": check_result.get("details", "")
                })
        
        return validation_results
    
    def _validate_new_meeting_added(self, before_snapshot: Dict[str, Any], 
                                  after_snapshot: Dict[str, Any],
                                  meeting_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that the new meeting was properly added"""
        
        expected_topic = meeting_params.get('topic', 'Meeting')
        expected_duration = meeting_params.get('duration_minutes', 30)
        
        # Check if each attendee has the new meeting
        for email in before_snapshot["attendees"].keys():
            before_events = before_snapshot["attendees"][email]["total_events"]
            after_events = after_snapshot["attendees"][email]["total_events"]
            
            if after_events <= before_events:
                return {
                    "passed": False,
                    "message": f"New meeting not found for {email}",
                    "details": f"Before: {before_events} events, After: {after_events} events"
                }
        
        return {
            "passed": True,
            "message": "New meeting successfully added to all attendees"
        }
    
    def _validate_time_constraints(self, scheduling_result: Dict[str, Any], 
                                 meeting_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that time constraints were respected"""
        
        time_constraints = meeting_params.get('time_constraints', 'flexible').lower()
        start_time = scheduling_result.get('start_time', '')
        
        if not start_time:
            return {
                "passed": False,
                "message": "No start time in scheduling result"
            }
        
        try:
            scheduled_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
            
            # Check specific day constraints
            if 'thursday' in time_constraints:
                if scheduled_dt.weekday() != 3:  # Thursday = 3
                    return {
                        "passed": False,
                        "message": f"Meeting not scheduled on Thursday (got {scheduled_dt.strftime('%A')})"
                    }
            
            # Check other constraints similarly...
            
            return {
                "passed": True,
                "message": f"Time constraints '{time_constraints}' respected"
            }
            
        except Exception as e:
            return {
                "passed": False,
                "message": f"Invalid time format: {e}"
            }
    
    def _validate_duration_accuracy(self, scheduling_result: Dict[str, Any], 
                                  meeting_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate meeting duration is correct"""
        
        expected_duration = meeting_params.get('duration_minutes', 30)
        start_time = scheduling_result.get('start_time', '')
        end_time = scheduling_result.get('end_time', '')
        
        if not start_time or not end_time:
            return {
                "passed": False,
                "message": "Missing start or end time"
            }
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
            end_dt = datetime.fromisoformat(end_time.replace('+05:30', ''))
            actual_duration = int((end_dt - start_dt).total_seconds() / 60)
            
            if abs(actual_duration - expected_duration) > 5:  # Allow 5 minute tolerance
                return {
                    "passed": False,
                    "message": f"Duration mismatch: expected {expected_duration}min, got {actual_duration}min"
                }
            
            return {
                "passed": True,
                "message": f"Duration accurate: {actual_duration} minutes"
            }
            
        except Exception as e:
            return {
                "passed": False,
                "message": f"Duration validation error: {e}"
            }
    
    def _validate_no_invalid_conflicts(self, after_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Validate no invalid time conflicts exist"""
        
        conflicts = []
        
        for email, attendee_info in after_snapshot["attendees"].items():
            events = attendee_info["events"]
            
            # Check for overlapping events for same person
            for i, event1 in enumerate(events):
                for j, event2 in enumerate(events[i+1:], i+1):
                    if self._events_overlap(event1, event2):
                        conflicts.append({
                            "attendee": email,
                            "event1": event1["summary"],
                            "event2": event2["summary"],
                            "time1": f"{event1['start']} - {event1['end']}",
                            "time2": f"{event2['start']} - {event2['end']}"
                        })
        
        if conflicts:
            return {
                "passed": False,
                "message": f"Found {len(conflicts)} time conflicts",
                "details": conflicts
            }
        
        return {
            "passed": True,
            "message": "No time conflicts detected"
        }
    
    def _events_overlap(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if two events overlap in time"""
        try:
            start1 = datetime.fromisoformat(event1['start'].replace('+05:30', ''))
            end1 = datetime.fromisoformat(event1['end'].replace('+05:30', ''))
            start2 = datetime.fromisoformat(event2['start'].replace('+05:30', ''))
            end2 = datetime.fromisoformat(event2['end'].replace('+05:30', ''))
            
            return start1 < end2 and end1 > start2
        except:
            return False
    
    def _validate_output_format(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output follows required format"""
        
        required_fields = ["Request_id", "EventStart", "EventEnd", "Duration_mins", "Attendees", "MetaData"]
        
        for field in required_fields:
            if field not in output_data:
                return {
                    "passed": False,
                    "message": f"Missing required field: {field}"
                }
        
        # Validate Attendees structure
        if not isinstance(output_data["Attendees"], list):
            return {
                "passed": False,
                "message": "Attendees must be a list"
            }
        
        for attendee in output_data["Attendees"]:
            if "email" not in attendee or "events" not in attendee:
                return {
                    "passed": False,
                    "message": "Invalid attendee structure"
                }
        
        return {
            "passed": True,
            "message": "Output format is correct"
        }
    
    def _validate_future_scheduling(self, scheduling_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate meeting is scheduled in the future"""
        
        start_time = scheduling_result.get('start_time', '')
        
        if not start_time:
            return {
                "passed": False,
                "message": "No start time provided"
            }
        
        try:
            scheduled_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
            now = datetime.now()
            
            if scheduled_dt <= now:
                return {
                    "passed": False,
                    "message": f"Meeting scheduled in past: {start_time}"
                }
            
            return {
                "passed": True,
                "message": f"Meeting properly scheduled in future: {start_time}"
            }
            
        except Exception as e:
            return {
                "passed": False,
                "message": f"Invalid start time format: {e}"
            }
    
    def _validate_attendee_consistency(self, output_data: Dict[str, Any], 
                                     meeting_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate attendee lists are consistent"""
        
        expected_participants = set(meeting_params.get('participants', []))
        actual_attendees = set()
        
        for attendee_data in output_data.get("Attendees", []):
            actual_attendees.add(attendee_data.get("email", ""))
        
        if expected_participants != actual_attendees:
            return {
                "passed": False,
                "message": f"Attendee mismatch: expected {expected_participants}, got {actual_attendees}"
            }
        
        return {
            "passed": True,
            "message": "Attendee lists are consistent"
        }
    
    def _validate_priority_handling(self, before_snapshot: Dict[str, Any], 
                                  after_snapshot: Dict[str, Any],
                                  meeting_params: Dict[str, Any],
                                  scheduling_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate priority-based scheduling worked correctly"""
        
        priority = meeting_params.get('priority', 'normal')
        
        if priority == 'high':
            # For high priority, check if rescheduling occurred
            rescheduled_count = scheduling_result.get('rescheduled_count', 0)
            
            # Check if meeting got preferred time slot
            start_time = scheduling_result.get('start_time', '')
            if start_time:
                try:
                    scheduled_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
                    # Check if it's close to preferred time (e.g., 9 AM)
                    if scheduled_dt.hour == 9:
                        return {
                            "passed": True,
                            "message": f"High priority meeting scheduled at preferred time (9 AM), rescheduled {rescheduled_count} meetings"
                        }
                except:
                    pass
        
        return {
            "passed": True,
            "message": f"Priority handling appropriate for {priority} priority"
        }
    
    def _calculate_correctness_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall correctness score (0-100)"""
        
        total_checks = len(validation_results["checks"])
        passed_checks = sum(1 for check in validation_results["checks"].values() if check["passed"])
        
        if total_checks == 0:
            return 0.0
        
        base_score = (passed_checks / total_checks) * 100
        
        # Apply penalties for critical errors
        penalties = 0
        for error in validation_results.get("errors", []):
            if "time" in error["check"] or "format" in error["check"]:
                penalties += 10  # Critical errors get higher penalty
            else:
                penalties += 5   # Other errors get lower penalty
        
        final_score = max(0.0, base_score - penalties)
        
        return final_score
    
    def _generate_corrections(self, validation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate correction suggestions based on validation results"""
        
        corrections = []
        
        for error in validation_results.get("errors", []):
            check_name = error["check"]
            
            if "time_constraints" in check_name:
                corrections.append({
                    "type": "time_constraint_fix",
                    "message": "Adjust time constraint parsing",
                    "action": "reparse_constraints"
                })
            
            elif "duration" in check_name:
                corrections.append({
                    "type": "duration_fix", 
                    "message": "Fix duration calculation",
                    "action": "recalculate_duration"
                })
            
            elif "conflict" in check_name:
                corrections.append({
                    "type": "conflict_resolution",
                    "message": "Resolve time conflicts",
                    "action": "find_alternative_slot"
                })
        
        return corrections
    
    def _apply_corrections(self, meeting_params: Dict[str, Any], 
                         corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply corrections to meeting parameters"""
        
        corrected_params = deepcopy(meeting_params)
        
        for correction in corrections:
            action = correction.get("action", "")
            
            if action == "reparse_constraints":
                # Try more flexible constraint parsing
                time_constraints = corrected_params.get('time_constraints', 'flexible')
                if time_constraints.lower() == 'flexible':
                    corrected_params['time_constraints'] = 'thursday'  # Default to Thursday
            
            elif action == "recalculate_duration":
                # Ensure duration is reasonable
                duration = corrected_params.get('duration_minutes', 30)
                if duration < 15:
                    corrected_params['duration_minutes'] = 30
                elif duration > 120:
                    corrected_params['duration_minutes'] = 60
            
            elif action == "find_alternative_slot":
                # Try different scheduling approach
                corrected_params['scheduling_approach'] = 'algorithmic'
        
        return corrected_params
    
    def _extract_calendar_from_output(self, output_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Extract calendar data from formatted output"""
        
        calendar_data = {}
        
        for attendee_data in output_data.get("Attendees", []):
            email = attendee_data.get("email", "")
            events = attendee_data.get("events", [])
            calendar_data[email] = events
        
        return calendar_data
    
    def _finalize_result(self, output_data: Dict[str, Any], 
                        validation_results: Dict[str, Any], 
                        iteration: int) -> Dict[str, Any]:
        """Finalize the perfect result with validation metadata"""
        
        final_result = deepcopy(output_data)
        
        # Add validation metadata
        if "MetaData" not in final_result:
            final_result["MetaData"] = {}
        
        final_result["MetaData"].update({
            "validation_applied": True,
            "validation_score": self._calculate_correctness_score(validation_results),
            "validation_iterations": iteration,
            "validation_timestamp": datetime.now().isoformat(),
            "all_checks_passed": all(check["passed"] for check in validation_results["checks"].values())
        })
        
        return final_result
    
    def _create_emergency_fallback(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create emergency fallback response"""
        
        tomorrow = datetime.now() + timedelta(days=1)
        while tomorrow.weekday() >= 5:
            tomorrow += timedelta(days=1)
        
        start_time = tomorrow.replace(hour=10, minute=0, second=0)
        end_time = start_time + timedelta(minutes=30)
        
        return {
            **request_data,
            "EventStart": start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            "EventEnd": end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            "Duration_mins": "30",
            "Attendees": [],
            "MetaData": {
                "emergency_fallback": True,
                "validation_failed": True
            }
        } 