"""
Optimized LLM client for the Smart Calendar Assistant
"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
import time
from functools import lru_cache

from config.settings import Config

logger = logging.getLogger(__name__)

class LLMClient:
    """Optimized LLM client with error handling and caching"""
    
    def __init__(self, model_name: str = None):
        self.config = Config()
        self.model_name = model_name or self.config.DEFAULT_MODEL
        self.model_config = self.config.get_model_config(self.model_name)
        
        # Initialize OpenAI client for Llama-3.2-3B
        self.client = OpenAI(
            api_key="NULL",  # vLLM doesn't require API key
            base_url=self.model_config["base_url"],
            timeout=self.config.LLM_TIMEOUT,
            max_retries=self.config.LLM_MAX_RETRIES
        )
        
        self.model_path = self.model_config["model_path"]
        self.max_tokens = self.model_config["max_tokens"]
        self.temperature = self.model_config["temperature"]
        self.top_p = self.model_config["top_p"]
        
        # Enhanced caching for Llama-3.2-3B
        self._response_cache = {}
        self._cache_hits = 0
        self._total_requests = 0
        
        logger.info(f"Initialized Llama-3.2-3B client: {self.model_path}")
    
    def _get_cache_key(self, prompt: str, temperature: float) -> str:
        """Generate cache key for request"""
        return f"{hash(prompt)}_{temperature}_{self.model_name}"
    
    def _make_completion_request(self, prompt: str, temperature: float = None, 
                               use_cache: bool = True) -> Optional[str]:
        """Optimized completion request for Llama-3.2-3B - uses completions endpoint directly"""
        temperature = temperature if temperature is not None else self.temperature
        cache_key = self._get_cache_key(prompt, temperature)
        
        self._total_requests += 1
        
        # Check cache first
        if use_cache and cache_key in self._response_cache:
            self._cache_hits += 1
            logger.debug(f"Cache hit ({self._cache_hits}/{self._total_requests})")
            return self._response_cache[cache_key]
        
        try:
            start_time = time.time()
            
            # Use completions endpoint directly since chat template has issues
            logger.debug("Using completions endpoint for Llama-3.2-3B")
            import requests
            
            response = requests.post(
                f"{self.model_config['base_url']}/completions",
                json={
                    "model": self.model_path,
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": temperature,
                    "top_p": self.top_p,
                    "stop": ["</s>", "\n\n"]
                },
                timeout=self.config.LLM_TIMEOUT,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['text'].strip()
                
                response_time = time.time() - start_time
                logger.info(f"Llama-3.2-3B completions response: {response_time:.2f}s")
                
                # Cache the response
                if use_cache:
                    self._response_cache[cache_key] = content
                    # Limit cache size for memory efficiency
                    if len(self._response_cache) > 100:
                        # Remove oldest entries
                        oldest_key = next(iter(self._response_cache))
                        del self._response_cache[oldest_key]
                
                return content
            else:
                logger.error(f"Completions request failed: {response.status_code} - {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"Llama-3.2-3B completions request failed: {e}")
            return None
    
    def parse_email_content(self, email_content: str, default_duration: int = 30) -> Dict[str, Any]:
        """Parse email content optimized for Llama-3.2-3B"""
        prompt = self.config.EMAIL_PARSING_PROMPT.format(
            domain=self.config.DEFAULT_DOMAIN,
            default_duration=default_duration,
            email_content=email_content[:500]  # Limit input length for efficiency
        )
        
        response = self._make_completion_request(prompt)
        
        if not response:
            logger.warning("LLM request failed, using enhanced fallback parsing")
            return self._enhanced_fallback_parsing(email_content, default_duration)
        
        # Enhanced JSON extraction for Llama-3.2-3B
        parsed_data = self._extract_json_from_llama_response(response)
        
        if parsed_data:
            # Validate and clean the data
            cleaned_data = self._validate_and_clean_email_data(parsed_data, default_duration)
            if cleaned_data:
                logger.info(f"Llama-3.2-3B parsed: {cleaned_data}")
                return cleaned_data
        
        # Enhanced fallback with regex patterns
        return self._enhanced_fallback_parsing(email_content, default_duration)
    
    def _extract_json_from_llama_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from Llama-3.2-3B response with multiple strategies"""
        strategies = [
            # Strategy 1: Look for complete JSON object
            lambda r: self._extract_json_by_braces(r),
            # Strategy 2: Look for JSON after "JSON:" marker
            lambda r: self._extract_json_after_marker(r, "JSON:"),
            # Strategy 3: Look for JSON in last lines
            lambda r: self._extract_json_from_end(r),
        ]
        
        for strategy in strategies:
            try:
                result = strategy(response)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"JSON extraction strategy failed: {e}")
                continue
        
        return None
    
    def _extract_json_by_braces(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON by finding balanced braces"""
        start = response.find('{')
        if start == -1:
            return None
        
        brace_count = 0
        for i, char in enumerate(response[start:], start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = response[start:i+1]
                    return json.loads(json_str)
        return None
    
    def _extract_json_after_marker(self, response: str, marker: str) -> Optional[Dict[str, Any]]:
        """Extract JSON after a specific marker"""
        marker_pos = response.find(marker)
        if marker_pos != -1:
            json_part = response[marker_pos + len(marker):].strip()
            return self._extract_json_by_braces(json_part)
        return None
    
    def _extract_json_from_end(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from the end of response"""
        lines = response.strip().split('\n')
        for i in range(len(lines)):
            try:
                line = lines[-(i+1)].strip()
                if line.startswith('{') and line.endswith('}'):
                    return json.loads(line)
            except (json.JSONDecodeError, IndexError):
                continue
        return None
    
    def _validate_and_clean_email_data(self, data: Dict[str, Any], default_duration: int) -> Optional[Dict[str, Any]]:
        """Validate and clean parsed email data"""
        required_fields = ['participants', 'duration_minutes', 'time_constraints', 'topic']
        
        if not all(field in data for field in required_fields):
            return None
        
        # Clean participants
        participants = data['participants']
        if isinstance(participants, str):
            participants = [p.strip() for p in participants.split(',')]
        elif not isinstance(participants, list):
            return None
        
        # Clean and validate each participant
        cleaned_participants = []
        for p in participants:
            p = p.strip()
            if p:
                if '@' not in p:
                    p += self.config.DEFAULT_DOMAIN
                cleaned_participants.append(p)
        
        # Validate duration
        try:
            duration = int(data['duration_minutes'])
            if duration <= 0 or duration > 480:  # Max 8 hours
                duration = default_duration
        except (ValueError, TypeError):
            duration = default_duration
        
        return {
            'participants': cleaned_participants,
            'duration_minutes': duration,
            'time_constraints': str(data['time_constraints']).strip(),
            'topic': str(data['topic']).strip()
        }
    
    def _enhanced_fallback_parsing(self, email_content: str, default_duration: int) -> Dict[str, Any]:
        """Enhanced fallback parsing with better heuristics"""
        logger.info("Using enhanced fallback email parsing")
        
        content_lower = email_content.lower()
        
        # Enhanced email detection
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, email_content, re.IGNORECASE)
        
        # Enhanced name detection if no emails found
        if not emails:
            name_patterns = [
                r'(?:attendees?|participants?|invite)[:\s]+([^.!?\n]+)',
                r'(?:with|cc|include)[:\s]+([^.!?\n]+)',
                r'team[:\s]*([^.!?\n]+)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, content_lower, re.IGNORECASE)
                if match:
                    name_text = match.group(1)
                    names = re.split(r'[,&\sand\s]+', name_text)
                    for name in names:
                        name = name.strip()
                        if name and len(name) > 1 and not any(word in name for word in ['meet', 'discuss', 'talk']):
                            if '@' not in name:
                                name += self.config.DEFAULT_DOMAIN
                            emails.append(name)
                    break
        
        # Enhanced duration detection
        duration = default_duration
        duration_patterns = [
            (r'(\d+)\s*hours?', lambda x: int(x) * 60),
            (r'(\d+)\s*(?:minutes?|mins?)', lambda x: int(x)),
            (r'half\s*(?:an?\s*)?hour', lambda x: 30),
            (r'(?:an?\s*)?hour', lambda x: 60),
            (r'(\d+)h', lambda x: int(x) * 60),
            (r'(\d+)m', lambda x: int(x)),
        ]
        
        for pattern, converter in duration_patterns:
            match = re.search(pattern, content_lower)
            if match:
                try:
                    if match.groups():
                        duration = converter(match.group(1))
                    else:
                        duration = converter(None)
                    break
                except (ValueError, TypeError):
                    continue
        
        # Enhanced time constraint detection
        time_constraints = "flexible"
        time_patterns = [
            r'next\s+week',
            r'this\s+week',
            r'tomorrow',
            r'today',
            r'(?:next\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(?:this|next)\s+(?:monday|tuesday|wednesday|thursday|friday)',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content_lower)
            if match:
                time_constraints = match.group(0)
                break
        
        # Enhanced topic extraction
        topic = "Meeting"
        subject_indicators = ['about', 'regarding', 'discuss', 'meeting about', 'talk about']
        
        for indicator in subject_indicators:
            pattern = f'{indicator}\\s+([^.!?\\n]+)'
            match = re.search(pattern, content_lower)
            if match:
                potential_topic = match.group(1).strip()
                if len(potential_topic) > 3 and len(potential_topic) < 100:
                    topic = potential_topic.title()
                    break
        
        # If no specific topic found, use first meaningful sentence
        if topic == "Meeting":
            sentences = re.split(r'[.!?]+', email_content)
            for sentence in sentences:
                sentence = sentence.strip()
                if 10 < len(sentence) < 80 and not sentence.lower().startswith('hi'):
                    topic = sentence
                    break
        
        return {
            'participants': emails,
            'duration_minutes': duration,
            'time_constraints': time_constraints,
            'topic': topic
        }
    
    def _fallback_email_parsing(self, email_content: str, default_duration: int) -> Dict[str, Any]:
        """Fallback email parsing using simple heuristics"""
        logger.info("Using fallback email parsing")
        
        content_lower = email_content.lower()
        
        # Extract participants (simple email detection)
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, email_content)
        
        # If no emails found, look for names and add default domain
        if not emails:
            # Simple name detection (words followed by common patterns)
            name_patterns = [
                r'attendees?:\s*([^.!?]+)',
                r'participants?:\s*([^.!?]+)',
                r'invite:\s*([^.!?]+)'
            ]
            
            names = []
            for pattern in name_patterns:
                match = re.search(pattern, content_lower)
                if match:
                    name_text = match.group(1)
                    # Split by common delimiters
                    potential_names = re.split(r'[,&\s]+', name_text)
                    for name in potential_names:
                        name = name.strip()
                        if name and len(name) > 1:
                            if '@' not in name:
                                name += self.config.DEFAULT_DOMAIN
                            names.append(name)
            emails = names
        
        # Extract duration
        duration = default_duration
        duration_patterns = [
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)\s*hours?',
            r'half\s*hour',
            r'an?\s*hour'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, content_lower)
            if match:
                if 'half' in pattern:
                    duration = 30
                elif 'hour' in pattern and 'hours' not in pattern:
                    duration = 60
                elif match.group(1):
                    num = int(match.group(1))
                    if 'hour' in pattern:
                        duration = num * 60
                    else:
                        duration = num
                break
        
        # Extract time constraints
        time_constraints = "flexible"
        time_patterns = [
            r'next\s+week',
            r'tomorrow',
            r'today',
            r'this\s+week',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
            r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, content_lower):
                match = re.search(pattern, content_lower)
                time_constraints = match.group(0)
                break
        
        # Extract topic (use first sentence or subject-like content)
        topic = "Meeting"
        sentences = re.split(r'[.!?]+', email_content)
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 10 and len(first_sentence) < 100:
                topic = first_sentence
        
        return {
            'participants': emails,
            'duration_minutes': duration,
            'time_constraints': time_constraints,
            'topic': topic
        }
    
    def find_optimal_meeting_time(self, meeting_request: Dict[str, Any], 
                                calendar_data: Dict[str, Any], 
                                current_time: str) -> Dict[str, Any]:
        """Use LLM to find optimal meeting time"""
        
        # Format calendar data for LLM
        calendar_summary = self._format_calendar_data_for_llm(calendar_data)
        
        prompt = self.config.SCHEDULING_PROMPT.format(
            topic=meeting_request.get('topic', 'Meeting'),
            duration=meeting_request.get('duration_minutes', 30),
            participants=', '.join(meeting_request.get('participants', [])),
            time_constraints=meeting_request.get('time_constraints', 'flexible'),
            current_time=current_time,
            calendar_data=calendar_summary
        )
        
        response = self._make_completion_request(prompt, temperature=0.1)
        
        if not response:
            # Fallback to algorithmic scheduling
            return self._fallback_scheduling(meeting_request, calendar_data)
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                scheduling_result = json.loads(json_str)
                
                # Validate the response
                if 'start_time' in scheduling_result and 'end_time' in scheduling_result:
                    logger.info(f"LLM scheduling result: {scheduling_result}")
                    return scheduling_result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM scheduling response: {e}")
        
        # Fallback to algorithmic approach
        return self._fallback_scheduling(meeting_request, calendar_data)
    
    def _format_calendar_data_for_llm(self, calendar_data: Dict[str, Any]) -> str:
        """Format calendar data in a readable format for LLM"""
        formatted_data = []
        
        for email, events in calendar_data.items():
            event_list = []
            for event in events:
                event_list.append(f"  - {event['Summary']}: {event['StartTime']} to {event['EndTime']}")
            
            events_str = "\n".join(event_list) if event_list else "  - No events"
            formatted_data.append(f"{email}:\n{events_str}")
        
        return "\n\n".join(formatted_data)
    
    def _fallback_scheduling(self, meeting_request: Dict[str, Any], 
                           calendar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple algorithmic fallback for scheduling"""
        from datetime import datetime, timedelta
        
        # Default to next business day at 10 AM
        tomorrow = datetime.now() + timedelta(days=1)
        while tomorrow.weekday() >= 5:  # Skip weekends
            tomorrow += timedelta(days=1)
        
        start_time = tomorrow.replace(hour=10, minute=0, second=0)
        duration_minutes = meeting_request.get('duration_minutes', 30)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        return {
            'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            'reasoning': 'Fallback scheduling: next business day at 10 AM'
        }