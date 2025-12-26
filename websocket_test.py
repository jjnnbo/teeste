#!/usr/bin/env python3
"""
Simple WebSocket test for existing session
"""

import websocket
import json
import time
import threading

def test_websocket_with_session(session_id):
    """Test WebSocket connection with existing session"""
    ws_url = f"wss://mago-trader-web.preview.emergentagent.com/ws/{session_id}"
    frames_received = 0
    connected = False
    error_msg = None
    
    def on_message(ws, message):
        nonlocal frames_received
        try:
            data = json.loads(message)
            if data.get("type") == "frame":
                frames_received += 1
                if frames_received <= 3:
                    print(f"📡 Frame {frames_received} received (size: {len(data.get('data', ''))} chars)")
        except Exception as e:
            print(f"Message error: {e}")

    def on_error(ws, error):
        nonlocal error_msg
        error_msg = str(error)
        print(f"❌ WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 WebSocket closed: {close_status_code}")

    def on_open(ws):
        nonlocal connected
        connected = True
        print(f"✅ WebSocket connected to session {session_id}")
        
        # Send a test resize event
        test_event = {
            "type": "resize",
            "width": 1280,
            "height": 720
        }
        ws.send(json.dumps(test_event))
        print("📤 Sent resize event")

    print(f"🔗 Connecting to WebSocket: {ws_url}")
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    # Run WebSocket in a separate thread
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for connection and frames
    max_wait = 10  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if error_msg:
            break
        if connected and frames_received >= 3:
            break
        time.sleep(0.5)
    
    # Close WebSocket
    ws.close()
    
    # Results
    print(f"\n📊 WebSocket Test Results:")
    print(f"   Connected: {connected}")
    print(f"   Frames received: {frames_received}")
    print(f"   Error: {error_msg}")
    
    return connected and frames_received > 0 and not error_msg

if __name__ == "__main__":
    # Use the existing session
    session_id = "180c6617-a5da-4f23-aae5-5ba57ebaaa87"
    success = test_websocket_with_session(session_id)
    print(f"\n🎯 WebSocket test {'PASSED' if success else 'FAILED'}")