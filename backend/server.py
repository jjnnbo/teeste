from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import base64
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, Page, Playwright, CDPSession

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'mago_trader')]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global Playwright instance
playwright_instance: Optional[Playwright] = None
browser_instance: Optional[Browser] = None

# Session management
class BrowserSession:
    def __init__(self, session_id: str, page: Page, context, cdp_session: CDPSession):
        self.session_id = session_id
        self.page = page
        self.context = context
        self.cdp_session = cdp_session
        self.websocket: Optional[WebSocket] = None
        self.last_activity = datetime.now(timezone.utc)
        self.streaming = False
        self.viewport_width = 1280
        self.viewport_height = 720
        self.frame_queue = asyncio.Queue(maxsize=3)  # Buffer for frames
        self.screencast_started = False

sessions: Dict[str, BrowserSession] = {}

# Cleanup inactive sessions
async def cleanup_sessions():
    while True:
        await asyncio.sleep(60)
        now = datetime.now(timezone.utc)
        to_remove = []
        for session_id, session in sessions.items():
            inactive_time = (now - session.last_activity).total_seconds()
            if inactive_time > 300:  # 5 minutes timeout
                to_remove.append(session_id)
        
        for session_id in to_remove:
            await close_session(session_id)
            logger.info(f"Cleaned up inactive session: {session_id}")

async def close_session(session_id: str):
    if session_id in sessions:
        session = sessions[session_id]
        session.streaming = False
        try:
            # Stop screencast
            if session.screencast_started and session.cdp_session:
                try:
                    await session.cdp_session.send("Page.stopScreencast")
                except:
                    pass
            await session.page.close()
            await session.context.close()
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {e}")
        del sessions[session_id]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global playwright_instance, browser_instance
    
    # Startup
    logger.info("Starting Playwright...")
    playwright_instance = await async_playwright().start()
    browser_instance = await playwright_instance.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--enable-features=NetworkService,NetworkServiceInProcess',
            '--force-color-profile=srgb',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
        ]
    )
    logger.info("Playwright browser started")
    
    # Start cleanup task
    cleanup_task = asyncio.create_task(cleanup_sessions())
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    
    for session_id in list(sessions.keys()):
        await close_session(session_id)
    
    if browser_instance:
        await browser_instance.close()
    if playwright_instance:
        await playwright_instance.stop()
    client.close()
    logger.info("Playwright shutdown complete")

# Create the main app with lifespan
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {"message": "Mago Trader API", "status": "online"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "sessions": len(sessions)}

@api_router.post("/session/create")
async def create_session(
    viewport_width: int = 1280, 
    viewport_height: int = 720,
    start_url: str = "https://pocketoption.com"
):
    """Create a new browser session with CDP support"""
    global browser_instance
    
    if not browser_instance:
        return JSONResponse(status_code=500, content={"error": "Browser not available"})
    
    session_id = str(uuid.uuid4())
    
    try:
        # Create browser context with viewport
        context = await browser_instance.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            ignore_https_errors=True,
            java_script_enabled=True,
            has_touch=True,
            is_mobile=False,
        )
        
        page = await context.new_page()
        
        # Get CDP session for screencast
        cdp_session = await context.new_cdp_session(page)
        
        # Create session
        session = BrowserSession(session_id, page, context, cdp_session)
        session.viewport_width = viewport_width
        session.viewport_height = viewport_height
        sessions[session_id] = session
        
        logger.info(f"Created session {session_id} with viewport {viewport_width}x{viewport_height}")
        
        # Start navigation in background
        asyncio.create_task(navigate_session(session_id, start_url))
        
        return {"session_id": session_id, "status": "created"}
    
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        try:
            if 'context' in locals():
                await context.close()
        except:
            pass
        return JSONResponse(status_code=500, content={"error": str(e)})

async def navigate_session(session_id: str, url: str):
    """Navigate session to URL in background"""
    if session_id not in sessions:
        return
    
    session = sessions[session_id]
    try:
        await session.page.goto(url, wait_until="commit", timeout=60000)
        logger.info(f"Session {session_id} navigated to {url}")
    except Exception as e:
        logger.warning(f"Navigation error for session {session_id}: {e}")

@api_router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a browser session"""
    if session_id in sessions:
        await close_session(session_id)
        return {"status": "deleted"}
    return JSONResponse(status_code=404, content={"error": "Session not found"})

@api_router.get("/sessions")
async def list_sessions():
    """List active sessions"""
    return {
        "count": len(sessions),
        "sessions": [
            {
                "id": s.session_id,
                "last_activity": s.last_activity.isoformat(),
                "streaming": s.streaming
            }
            for s in sessions.values()
        ]
    }

# WebSocket for browser streaming and control
@app.websocket("/api/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    if session_id not in sessions:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return
    
    session = sessions[session_id]
    session.websocket = websocket
    session.streaming = True
    
    logger.info(f"WebSocket connected for session {session_id}")
    
    # Setup CDP Screencast handler
    async def on_screencast_frame(params):
        """Handle incoming screencast frames from CDP"""
        if not session.streaming:
            return
        
        try:
            frame_data = params.get("data", "")
            session_id_param = params.get("sessionId", 0)
            
            # Acknowledge frame immediately for smooth streaming
            try:
                await session.cdp_session.send("Page.screencastFrameAck", {"sessionId": session_id_param})
            except:
                pass
            
            # Send frame to client
            if session.websocket and frame_data:
                try:
                    await session.websocket.send_json({
                        "type": "frame",
                        "data": frame_data
                    })
                except:
                    pass
        except Exception as e:
            logger.debug(f"Frame handling error: {e}")
    
    # Subscribe to screencast frames
    session.cdp_session.on("Page.screencastFrame", on_screencast_frame)
    
    # Start CDP Screencast at 60 FPS
    try:
        await session.cdp_session.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 80,  # Higher quality for better visuals
            "maxWidth": session.viewport_width,
            "maxHeight": session.viewport_height,
            "everyNthFrame": 1  # Every frame = 60 FPS
        })
        session.screencast_started = True
        logger.info(f"CDP Screencast started for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to start screencast: {e}")
        # Fallback to screenshot method
        asyncio.create_task(fallback_screenshot_stream(session))
    
    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            session.last_activity = datetime.now(timezone.utc)
            await handle_browser_event(session, event)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        session.streaming = False
        session.screencast_started = False
        try:
            await session.cdp_session.send("Page.stopScreencast")
        except:
            pass
        session.websocket = None

async def fallback_screenshot_stream(session: BrowserSession):
    """Fallback to screenshot streaming if CDP fails"""
    logger.info("Using fallback screenshot streaming")
    while session.streaming:
        try:
            if session.page and not session.page.is_closed():
                screenshot = await session.page.screenshot(
                    type="jpeg",
                    quality=80,
                    full_page=False,
                    timeout=5000
                )
                screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                
                if session.websocket:
                    await session.websocket.send_json({
                        "type": "frame",
                        "data": screenshot_base64
                    })
            
            await asyncio.sleep(0.016)  # ~60 FPS
        except Exception as e:
            logger.debug(f"Fallback stream error: {e}")
            await asyncio.sleep(0.1)

async def handle_browser_event(session: BrowserSession, event: dict):
    """Handle browser events with precise click handling"""
    try:
        page = session.page
        event_type = event.get("type")
        
        if event_type == "click":
            x = float(event.get("x", 0))
            y = float(event.get("y", 0))
            button = event.get("button", "left")
            
            # Use CDP for more precise clicking
            try:
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": button,
                    "clickCount": 1
                })
                await asyncio.sleep(0.05)  # Small delay for click registration
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": button,
                    "clickCount": 1
                })
            except Exception as e:
                # Fallback to Playwright
                logger.debug(f"CDP click failed, using Playwright: {e}")
                await page.mouse.click(x, y, button=button, delay=50)
        
        elif event_type == "dblclick":
            x = float(event.get("x", 0))
            y = float(event.get("y", 0))
            
            try:
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 2
                })
                await asyncio.sleep(0.03)
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 2
                })
            except:
                await page.mouse.dblclick(x, y)
        
        elif event_type == "mousedown":
            x = float(event.get("x", 0))
            y = float(event.get("y", 0))
            button = event.get("button", "left")
            
            try:
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": button,
                    "clickCount": 1
                })
            except:
                await page.mouse.move(x, y)
                await page.mouse.down(button=button)
        
        elif event_type == "mouseup":
            x = float(event.get("x", 0))
            y = float(event.get("y", 0))
            button = event.get("button", "left")
            
            try:
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": button,
                    "clickCount": 1
                })
            except:
                await page.mouse.move(x, y)
                await page.mouse.up(button=button)
        
        elif event_type == "mousemove":
            x = float(event.get("x", 0))
            y = float(event.get("y", 0))
            
            try:
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseMoved",
                    "x": x,
                    "y": y,
                    "button": "none"
                })
            except:
                await page.mouse.move(x, y)
        
        elif event_type == "scroll":
            x = float(event.get("x", 0))
            y = float(event.get("y", 0))
            delta_x = event.get("deltaX", 0)
            delta_y = event.get("deltaY", 0)
            
            try:
                await session.cdp_session.send("Input.dispatchMouseEvent", {
                    "type": "mouseWheel",
                    "x": x,
                    "y": y,
                    "deltaX": delta_x,
                    "deltaY": delta_y
                })
            except:
                await page.mouse.move(x, y)
                await page.mouse.wheel(delta_x, delta_y)
        
        elif event_type == "keydown":
            key = event.get("key", "")
            code = event.get("code", "")
            await handle_key_event_cdp(session, key, code, "keyDown")
        
        elif event_type == "keyup":
            key = event.get("key", "")
            code = event.get("code", "")
            await handle_key_event_cdp(session, key, code, "keyUp")
        
        elif event_type == "keypress":
            key = event.get("key", "")
            if len(key) == 1:
                try:
                    await session.cdp_session.send("Input.dispatchKeyEvent", {
                        "type": "char",
                        "text": key
                    })
                except:
                    await page.keyboard.type(key)
        
        elif event_type == "input":
            text = event.get("text", "")
            if text:
                for char in text:
                    try:
                        await session.cdp_session.send("Input.dispatchKeyEvent", {
                            "type": "char",
                            "text": char
                        })
                    except:
                        await page.keyboard.type(char)
        
        elif event_type == "touch":
            touches = event.get("touches", [])
            action = event.get("action", "tap")
            
            if action == "tap" and touches:
                x = float(touches[0].get("x", 0))
                y = float(touches[0].get("y", 0))
                
                # Use touch events via CDP
                try:
                    await session.cdp_session.send("Input.dispatchTouchEvent", {
                        "type": "touchStart",
                        "touchPoints": [{"x": x, "y": y}]
                    })
                    await asyncio.sleep(0.05)
                    await session.cdp_session.send("Input.dispatchTouchEvent", {
                        "type": "touchEnd",
                        "touchPoints": []
                    })
                except:
                    await page.mouse.click(x, y)
            
            elif action == "move" and touches:
                x = float(touches[0].get("x", 0))
                y = float(touches[0].get("y", 0))
                try:
                    await session.cdp_session.send("Input.dispatchTouchEvent", {
                        "type": "touchMove",
                        "touchPoints": [{"x": x, "y": y}]
                    })
                except:
                    await page.mouse.move(x, y)
        
        elif event_type == "resize":
            width = event.get("width", 1280)
            height = event.get("height", 720)
            session.viewport_width = width
            session.viewport_height = height
            await page.set_viewport_size({"width": width, "height": height})
            
            # Restart screencast with new dimensions
            if session.screencast_started:
                try:
                    await session.cdp_session.send("Page.stopScreencast")
                    await session.cdp_session.send("Page.startScreencast", {
                        "format": "jpeg",
                        "quality": 80,
                        "maxWidth": width,
                        "maxHeight": height,
                        "everyNthFrame": 1
                    })
                except:
                    pass
        
        elif event_type == "navigate":
            url = event.get("url", "")
            if url:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        elif event_type == "back":
            await page.go_back()
        
        elif event_type == "forward":
            await page.go_forward()
        
        elif event_type == "refresh":
            await page.reload()
    
    except Exception as e:
        logger.error(f"Error handling event {event.get('type')}: {e}")

async def handle_key_event_cdp(session: BrowserSession, key: str, code: str, event_type: str):
    """Handle keyboard events with CDP for better compatibility"""
    # Map special keys to CDP format
    key_map = {
        "Backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8},
        "Tab": {"key": "Tab", "code": "Tab", "keyCode": 9},
        "Enter": {"key": "Enter", "code": "Enter", "keyCode": 13},
        "Shift": {"key": "Shift", "code": "ShiftLeft", "keyCode": 16},
        "Control": {"key": "Control", "code": "ControlLeft", "keyCode": 17},
        "Alt": {"key": "Alt", "code": "AltLeft", "keyCode": 18},
        "Escape": {"key": "Escape", "code": "Escape", "keyCode": 27},
        "Space": {"key": " ", "code": "Space", "keyCode": 32},
        " ": {"key": " ", "code": "Space", "keyCode": 32},
        "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38},
        "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40},
        "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37},
        "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39},
        "Delete": {"key": "Delete", "code": "Delete", "keyCode": 46},
        "Home": {"key": "Home", "code": "Home", "keyCode": 36},
        "End": {"key": "End", "code": "End", "keyCode": 35},
        "PageUp": {"key": "PageUp", "code": "PageUp", "keyCode": 33},
        "PageDown": {"key": "PageDown", "code": "PageDown", "keyCode": 34},
    }
    
    mapped = key_map.get(key, {"key": key, "code": code or f"Key{key.upper()}", "keyCode": ord(key.upper()) if len(key) == 1 else 0})
    
    try:
        await session.cdp_session.send("Input.dispatchKeyEvent", {
            "type": event_type,
            "key": mapped["key"],
            "code": mapped["code"],
            "windowsVirtualKeyCode": mapped["keyCode"],
            "nativeVirtualKeyCode": mapped["keyCode"]
        })
    except Exception as e:
        logger.debug(f"CDP key event error: {e}")
        # Fallback to Playwright
        page = session.page
        if event_type == "keyDown":
            await page.keyboard.down(key)
        elif event_type == "keyUp":
            await page.keyboard.up(key)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
