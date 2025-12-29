#!/usr/bin/env python3
"""
Focused API Test for Review Request Requirements
Tests the specific endpoints mentioned in the review request
"""

import requests
import json
import time

# Backend URL from frontend .env
BACKEND_URL = "https://nolag-video.preview.emergentagent.com/api"

def test_review_requirements():
    """Test the specific requirements from the review request"""
    print("🔍 Testing Review Request Requirements")
    print("=" * 50)
    
    session = requests.Session()
    session.timeout = 30
    
    # Test 1: Health Check - GET /api/health
    print("1. Testing Health Check: GET /api/health")
    try:
        response = session.get(f"{BACKEND_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print(f"   ✅ PASS - Health check returned: {data}")
            else:
                print(f"   ❌ FAIL - Invalid status: {data}")
                return False
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        return False
    
    print()
    
    # Test 2: Session Creation - POST /api/session/create
    print("2. Testing Session Creation: POST /api/session/create?viewport_width=1280&viewport_height=720&start_url=https://google.com")
    try:
        params = {
            "viewport_width": 1280,
            "viewport_height": 720,
            "start_url": "https://google.com"
        }
        response = session.post(f"{BACKEND_URL}/session/create", params=params)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            status = data.get("status")
            if session_id and status == "created":
                print(f"   ✅ PASS - Session created: {data}")
                print(f"   📝 Session ID: {session_id}")
            else:
                print(f"   ❌ FAIL - Invalid response: {data}")
                return False
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        return False
    
    print()
    
    # Test 3: List Sessions - GET /api/sessions
    print("3. Testing List Sessions: GET /api/sessions")
    try:
        response = session.get(f"{BACKEND_URL}/sessions")
        if response.status_code == 200:
            data = response.json()
            count = data.get("count")
            sessions = data.get("sessions", [])
            if isinstance(count, int) and isinstance(sessions, list):
                print(f"   ✅ PASS - Sessions listed: {data}")
                print(f"   📊 Found {count} sessions")
                
                # Verify our session is in the list
                session_ids = [s.get("id") for s in sessions]
                if session_id in session_ids:
                    print(f"   ✅ Created session {session_id} found in list")
                else:
                    print(f"   ⚠️ Created session {session_id} not found in list")
            else:
                print(f"   ❌ FAIL - Invalid response format: {data}")
                return False
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        return False
    
    print()
    
    # Test 4: Delete Session - DELETE /api/session/{session_id}
    print(f"4. Testing Delete Session: DELETE /api/session/{session_id}")
    try:
        response = session.delete(f"{BACKEND_URL}/session/{session_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "deleted":
                print(f"   ✅ PASS - Session deleted: {data}")
            else:
                print(f"   ❌ FAIL - Invalid status: {data}")
                return False
        else:
            print(f"   ❌ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        return False
    
    print()
    print("🎉 ALL REVIEW REQUIREMENTS PASSED!")
    return True

if __name__ == "__main__":
    success = test_review_requirements()
    exit(0 if success else 1)