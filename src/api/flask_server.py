"""
Optimized Flask API server for the Smart Calendar Assistant
"""
import json
import logging
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
import signal
import sys
from datetime import datetime

from config.settings import Config
from src.scheduler.smart_scheduler import SmartScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmartCalendarAPI:
    """
    Optimized Flask API server for handling meeting requests
    """
    
    def __init__(self, model_name: str = None):
        self.config = Config()
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for cross-origin requests
        
        # Initialize the smart scheduler
        try:
            self.scheduler = SmartScheduler(model_name)
            logger.info("SmartScheduler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SmartScheduler: {e}")
            self.scheduler = None
        
        # Store received data for debugging
        self.received_requests = []
        
        # Setup routes
        self._setup_routes()
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "scheduler_available": self.scheduler is not None
            })
        
        @self.app.route('/receive', methods=['POST'])
        def receive_meeting_request():
            """Main endpoint for receiving meeting requests"""
            start_time = time.time()
            
            try:
                # Get JSON data from request
                data = request.get_json()
                
                if not data:
                    logger.error("No JSON data received")
                    return jsonify({"error": "No JSON data provided"}), 400
                
                request_id = data.get('Request_id', 'unknown')
                logger.info(f"🚀 RECEIVED MEETING REQUEST: {request_id}")
                logger.info(f"   📧 From: {data.get('From', 'N/A')}")
                logger.info(f"   📋 Subject: {data.get('Subject', 'N/A')}")
                logger.info(f"   👥 Attendees: {len(data.get('Attendees', []))} people")
                logger.info(f"   📍 Location: {data.get('Location', 'N/A')}")
                logger.info(f"   📝 Email Content: {data.get('EmailContent', 'N/A')[:100]}...")
                
                # Store request for debugging
                self.received_requests.append({
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                })
                
                # Process the meeting request
                if self.scheduler is None:
                    logger.error("Scheduler not available")
                    return jsonify({"error": "Scheduler not initialized"}), 500
                
                # Process with timeout protection
                try:
                    result = self.scheduler.process_meeting_request(data)
                    
                    processing_time = time.time() - start_time
                    
                    # Log the final result
                    logger.info(f"✅ REQUEST COMPLETED: {request_id}")
                    logger.info(f"   ⏱️  Processing time: {processing_time:.2f} seconds")
                    logger.info(f"   📅 Scheduled: {result.get('EventStart', 'N/A')} to {result.get('EventEnd', 'N/A')}")
                    logger.info(f"   ⏰ Duration: {result.get('Duration_mins', 'N/A')} minutes")
                    
                    # Check if final meeting is during off hours
                    if result.get('EventStart'):
                        try:
                            start_dt = datetime.fromisoformat(result['EventStart'].replace('+05:30', ''))
                            is_off_hours = (start_dt.hour < 9 or start_dt.hour >= 18 or start_dt.weekday() >= 5)
                            if is_off_hours:
                                logger.info(f"   🌙 FINAL RESULT: Meeting scheduled during OFF HOURS")
                            else:
                                logger.info(f"   🏢 FINAL RESULT: Meeting scheduled during BUSINESS HOURS")
                        except:
                            pass
                    
                    # Check if processing time exceeds limit
                    if processing_time > self.config.API_TIMEOUT:
                        logger.warning(f"⚠️  Processing time ({processing_time:.2f}s) exceeded limit ({self.config.API_TIMEOUT}s)")
                    
                    return jsonify(result)
                    
                except Exception as e:
                    logger.error(f"Error processing request: {e}")
                    # Return fallback response
                    fallback_response = self._create_emergency_fallback(data)
                    return jsonify(fallback_response)
            
            except Exception as e:
                logger.error(f"Unexpected error in receive endpoint: {e}")
                return jsonify({"error": "Internal server error"}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Get server status and statistics"""
            return jsonify({
                "status": "running",
                "requests_processed": len(self.received_requests),
                "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
                "scheduler_available": self.scheduler is not None
            })
        
        @self.app.route('/debug/requests', methods=['GET'])
        def get_debug_info():
            """Get debug information (last few requests)"""
            # Return last 5 requests for debugging
            recent_requests = self.received_requests[-5:] if self.received_requests else []
            return jsonify({
                "recent_requests": recent_requests,
                "total_requests": len(self.received_requests)
            })
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({"error": "Endpoint not found"}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({"error": "Internal server error"}), 500
    
    def _create_emergency_fallback(self, request_data):
        """Create emergency fallback response"""
        from datetime import datetime, timedelta
        
        # Very basic fallback
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=10, minute=0, second=0)
        end_time = start_time + timedelta(minutes=30)
        
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')
        
        # Basic response structure
        response = request_data.copy()
        response.update({
            "EventStart": start_str,
            "EventEnd": end_str,
            "Duration_mins": "30",
            "MetaData": {"emergency_fallback": True}
        })
        
        return response
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self, host=None, port=None, debug=False):
        """Run the Flask server"""
        host = host or self.config.API_HOST
        port = port or self.config.API_PORT
        
        self.start_time = time.time()
        
        logger.info(f"Starting Smart Calendar API server on {host}:{port}")
        logger.info(f"Scheduler status: {'Available' if self.scheduler else 'Not Available'}")
        
        try:
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,  # Enable threading for concurrent requests
                use_reloader=False  # Disable reloader in production
            )
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    def run_background(self, host=None, port=None):
        """Run the Flask server in background thread"""
        def run_server():
            self.run(host, port, debug=False)
        
        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()
        logger.info("Flask server started in background")
        return server_thread
    
    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down Smart Calendar API server...")
        # Add any cleanup logic here if needed

def create_app(model_name: str = None) -> Flask:
    """Factory function to create Flask app"""
    api = SmartCalendarAPI(model_name)
    return api.app

def main():
    """Main entry point for Llama-3.2-3B"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Calendar API Server (Llama-3.2-3B)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Always use Llama-3.2-3B model
    api = SmartCalendarAPI(model_name='llama-3.2-3b')
    api.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()