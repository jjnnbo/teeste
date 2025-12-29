#!/usr/bin/env python3
"""
Backend API Testing for Mago Trader
Tests all backend endpoints and WebSocket functionality
"""

import requests
import websocket
import json
import time
import sys
import threading
from datetime import datetime

class MagoTraderAPITester:
    def __init__(self, base_url="https://nolag-video.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None
        self.ws_frames_received = 0
        self.ws_connected = False
        self.ws_error = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def test_api_root(self):
        """Test GET /api/"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                expected_fields = ["message", "status"]
                has_fields = all(field in data for field in expected_fields)
                is_online = data.get("status") == "online"
                success = has_fields and is_online
                details = f"Status: {response.status_code}, Data: {data}"
            else:
                details = f"Status: {response.status_code}"
                
            return self.log_test("API Root Endpoint", success, details)
        except Exception as e:
            return self.log_test("API Root Endpoint", False, f"Error: {str(e)}")

    def test_health_endpoint(self):
        """Test GET /api/health"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                is_healthy = data.get("status") == "healthy"
                has_sessions = "sessions" in data
                success = is_healthy and has_sessions
                details = f"Status: {response.status_code}, Data: {data}"
            else:
                details = f"Status: {response.status_code}"
                
            return self.log_test("Health Endpoint", success, details)
        except Exception as e:
            return self.log_test("Health Endpoint", False, f"Error: {str(e)}")

    def test_create_session(self):
        """Test POST /api/session/create"""
        try:
            # Test with Google instead of pocketoption.com to avoid IP blocking
            params = {"start_url": "https://google.com"}
            response = requests.post(f"{self.api_url}/session/create", params=params, timeout=30)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                has_session_id = "session_id" in data
                has_status = data.get("status") == "created"
                success = has_session_id and has_status
                
                if success:
                    self.session_id = data["session_id"]
                    details = f"Status: {response.status_code}, Session ID: {self.session_id}"
                else:
                    details = f"Status: {response.status_code}, Missing fields in response: {data}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text}"
                
            return self.log_test("Create Session", success, details)
        except Exception as e:
            return self.log_test("Create Session", False, f"Error: {str(e)}")

    def test_create_session_with_viewport(self):
        """Test POST /api/session/create with custom viewport"""
        try:
            params = {"viewport_width": 1920, "viewport_height": 1080}
            response = requests.post(f"{self.api_url}/session/create", params=params, timeout=30)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                has_session_id = "session_id" in data
                has_status = data.get("status") == "created"
                success = has_session_id and has_status
                details = f"Status: {response.status_code}, Custom viewport session created"
            else:
                details = f"Status: {response.status_code}"
                
            return self.log_test("Create Session with Custom Viewport", success, details)
        except Exception as e:
            return self.log_test("Create Session with Custom Viewport", False, f"Error: {str(e)}")

    def test_list_sessions(self):
        """Test GET /api/sessions"""
        try:
            response = requests.get(f"{self.api_url}/sessions", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                has_count = "count" in data
                has_sessions = "sessions" in data
                count_matches = data.get("count") == len(data.get("sessions", []))
                success = has_count and has_sessions and count_matches
                details = f"Status: {response.status_code}, Sessions: {data.get('count', 0)}"
            else:
                details = f"Status: {response.status_code}"
                
            return self.log_test("List Sessions", success, details)
        except Exception as e:
            return self.log_test("List Sessions", False, f"Error: {str(e)}")

    def on_ws_message(self, ws, message):
        """WebSocket message handler"""
        try:
            data = json.loads(message)
            if data.get("type") == "frame":
                self.ws_frames_received += 1
                if self.ws_frames_received == 1:
                    print(f"📡 First WebSocket frame received")
        except Exception as e:
            print(f"WebSocket message error: {e}")

    def on_ws_error(self, ws, error):
        """WebSocket error handler"""
        self.ws_error = str(error)
        print(f"WebSocket error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler"""
        print(f"WebSocket closed: {close_status_code} - {close_msg}")

    def on_ws_open(self, ws):
        """WebSocket open handler"""
        self.ws_connected = True
        print(f"📡 WebSocket connected")
        
        # Send a test event
        test_event = {
            "type": "resize",
            "width": 1280,
            "height": 720
        }
        ws.send(json.dumps(test_event))

    def test_websocket_connection(self):
        """Test WebSocket connection and streaming"""
        if not self.session_id:
            return self.log_test("WebSocket Connection", False, "No session ID available")
        
        try:
            ws_url = f"{self.ws_url}/api/ws/{self.session_id}"
            print(f"🔗 Connecting to WebSocket: {ws_url}")
            
            # Reset counters
            self.ws_frames_received = 0
            self.ws_connected = False
            self.ws_error = None
            
            # Create WebSocket connection
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close,
                on_open=self.on_ws_open
            )
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection and frames
            max_wait = 20  # seconds - increased for Google to load
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                if self.ws_error:
                    break
                if self.ws_connected and self.ws_frames_received > 0:
                    break
                time.sleep(0.5)
            
            # Close WebSocket
            ws.close()
            
            # Evaluate results
            if self.ws_error:
                return self.log_test("WebSocket Connection", False, f"WebSocket error: {self.ws_error}")
            elif not self.ws_connected:
                return self.log_test("WebSocket Connection", False, "Failed to connect")
            elif self.ws_frames_received == 0:
                return self.log_test("WebSocket Connection", False, "Connected but no frames received")
            else:
                return self.log_test("WebSocket Connection", True, f"Connected and received {self.ws_frames_received} frames")
                
        except Exception as e:
            return self.log_test("WebSocket Connection", False, f"Error: {str(e)}")

    def test_delete_session(self):
        """Test DELETE /api/session/{session_id}"""
        if not self.session_id:
            return self.log_test("Delete Session", False, "No session ID available")
        
        try:
            response = requests.delete(f"{self.api_url}/session/{self.session_id}", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                success = data.get("status") == "deleted"
                details = f"Status: {response.status_code}, Response: {data}"
            else:
                details = f"Status: {response.status_code}"
                
            return self.log_test("Delete Session", success, details)
        except Exception as e:
            return self.log_test("Delete Session", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Mago Trader Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Basic API tests
        self.test_api_root()
        self.test_health_endpoint()
        
        # Session management tests
        self.test_create_session()
        self.test_create_session_with_viewport()
        self.test_list_sessions()
        
        # WebSocket tests (requires session)
        if self.session_id:
            self.test_websocket_connection()
            # Give some time for streaming
            time.sleep(2)
            self.test_delete_session()
        
        # Final results
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            return 1

def main():
    """Main test runner"""
    tester = MagoTraderAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())