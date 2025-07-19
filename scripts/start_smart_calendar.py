#!/usr/bin/env python3
"""
Comprehensive startup script for Smart Calendar with Llama-3.2-3B
"""

import subprocess
import sys
import time
import requests
import json
import signal
import os
from pathlib import Path

class SmartCalendarStarter:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.vllm_process = None
        self.api_process = None
        
    def check_dependencies(self):
        """Check if required dependencies are available"""
        print("🔍 Checking dependencies...")
        
        # Check if vLLM is installed
        try:
            import vllm
            print("✅ vLLM is installed")
        except ImportError:
            print("❌ vLLM not found. Please install: pip install vllm")
            return False
        
        # Check if model directory exists
        model_path = "/home/user/smart-calendar/Models/meta-llama/Llama-3.2-3B"
        if not os.path.exists(model_path):
            print(f"❌ Model not found at {model_path}")
            print("Please ensure Llama-3.2-3B model is downloaded")
            return False
        else:
            print(f"✅ Model found at {model_path}")
        
        # Check if calendar tokens exist
        tokens_path = self.base_dir / "IISc_Google_Calendar_Keys"
        if not tokens_path.exists():
            print(f"⚠️  Calendar tokens not found at {tokens_path}")
            print("Google Calendar integration may not work")
        else:
            print("✅ Calendar tokens found")
        
        return True
    
    def start_vllm_server(self):
        """Start the vLLM server"""
        print("🚀 Starting Llama-3.2-3B vLLM server...")
        
        script_path = self.base_dir / "scripts" / "start_llama_server.sh"
        
        try:
            self.vllm_process = subprocess.Popen(
                [str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait for server to start
            print("⏳ Waiting for vLLM server to start...")
            max_wait = 120  # 2 minutes
            for i in range(max_wait):
                try:
                    response = requests.get("http://localhost:4000/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ vLLM server is ready!")
                        return True
                except requests.exceptions.RequestException:
                    pass
                
                if i % 10 == 0:
                    print(f"   Still waiting... ({i}/{max_wait}s)")
                time.sleep(1)
            
            print("❌ vLLM server failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start vLLM server: {e}")
            return False
    
    def start_api_server(self):
        """Start the Smart Calendar API server"""
        print("🚀 Starting Smart Calendar API server...")
        
        try:
            # Change to the smart-calendar directory
            os.chdir(self.base_dir)
            
            self.api_process = subprocess.Popen(
                [sys.executable, "main.py", "server", "--host", "0.0.0.0", "--port", "5000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait for API server to start
            print("⏳ Waiting for API server to start...")
            max_wait = 30
            for i in range(max_wait):
                try:
                    response = requests.get("http://localhost:5000/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Smart Calendar API server is ready!")
                        return True
                except requests.exceptions.RequestException:
                    pass
                
                time.sleep(1)
            
            print("❌ API server failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start API server: {e}")
            return False
    
    def run_health_check(self):
        """Run comprehensive health check"""
        print("🏥 Running health checks...")
        
        # Check vLLM server
        try:
            response = requests.get("http://localhost:4000/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                print("✅ vLLM server healthy, available models:")
                for model in models.get('data', []):
                    print(f"   - {model.get('id', 'Unknown')}")
            else:
                print("⚠️  vLLM server responding but may have issues")
        except Exception as e:
            print(f"❌ vLLM server health check failed: {e}")
            return False
        
        # Check API server
        try:
            response = requests.get("http://localhost:5000/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Smart Calendar API healthy")
                print(f"   Status: {health_data.get('status')}")
                print(f"   Scheduler: {'✅' if health_data.get('scheduler_available') else '❌'}")
            else:
                print("⚠️  API server responding but may have issues")
        except Exception as e:
            print(f"❌ API server health check failed: {e}")
            return False
        
        return True
    
    def run_test_request(self):
        """Run a test request to verify everything works"""
        print("🧪 Running test request...")
        
        test_request = {
            "Request_id": "test-startup-001",
            "Datetime": "19-07-2025T12:34:55",
            "Location": "Test Location",
            "From": "userone.amd@gmail.com",
            "Attendees": [
                {"email": "usertwo.amd@gmail.com"},
                {"email": "userthree.amd@gmail.com"}
            ],
            "Subject": "Test Meeting",
            "EmailContent": "Let's have a test meeting tomorrow for 30 minutes to verify the system works."
        }
        
        try:
            response = requests.post(
                "http://localhost:5000/receive",
                json=test_request,
                timeout=15,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Test request successful!")
                print(f"   Event scheduled: {result.get('EventStart')} to {result.get('EventEnd')}")
                print(f"   Duration: {result.get('Duration_mins')} minutes")
                return True
            else:
                print(f"❌ Test request failed: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Test request failed: {e}")
            return False
    
    def stop_servers(self):
        """Stop all servers gracefully"""
        print("🛑 Stopping servers...")
        
        if self.api_process:
            try:
                os.killpg(os.getpgid(self.api_process.pid), signal.SIGTERM)
                self.api_process.wait(timeout=10)
                print("✅ API server stopped")
            except Exception as e:
                print(f"⚠️  Force killing API server: {e}")
                os.killpg(os.getpgid(self.api_process.pid), signal.SIGKILL)
        
        if self.vllm_process:
            try:
                os.killpg(os.getpgid(self.vllm_process.pid), signal.SIGTERM)
                self.vllm_process.wait(timeout=30)
                print("✅ vLLM server stopped")
            except Exception as e:
                print(f"⚠️  Force killing vLLM server: {e}")
                os.killpg(os.getpgid(self.vllm_process.pid), signal.SIGKILL)
    
    def run(self):
        """Main execution flow"""
        print("🤖 Smart Calendar with Llama-3.2-3B Startup Script")
        print("=" * 50)
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            print("\n🛑 Shutdown signal received")
            self.stop_servers()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Check dependencies
            if not self.check_dependencies():
                print("❌ Dependency check failed. Exiting.")
                return False
            
            # Start vLLM server
            if not self.start_vllm_server():
                print("❌ Failed to start vLLM server. Exiting.")
                return False
            
            # Start API server
            if not self.start_api_server():
                print("❌ Failed to start API server. Exiting.")
                self.stop_servers()
                return False
            
            # Run health checks
            if not self.run_health_check():
                print("❌ Health check failed. Exiting.")
                self.stop_servers()
                return False
            
            # Run test request
            if not self.run_test_request():
                print("⚠️  Test request failed, but servers are running.")
            
            print("\n🎉 Smart Calendar is ready!")
            print("📡 API Endpoint: http://localhost:5000/receive")
            print("🔍 Health Check: http://localhost:5000/health")
            print("📊 vLLM Status: http://localhost:4000/v1/models")
            print("\nPress Ctrl+C to stop all servers")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(10)
                    # Periodic health check
                    if not self.run_health_check():
                        print("⚠️  Health check failed during runtime")
            except KeyboardInterrupt:
                pass
            
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
        finally:
            self.stop_servers()

def main():
    starter = SmartCalendarStarter()
    success = starter.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()