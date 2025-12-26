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
from playwright.async_api import async_playwright, Browser, Page, Playwright

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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
    def __init__(self, session_id: str, page: Page, context):
        self.session_id = session_id
        self.page = page
        self.context = context
        self.websocket: Optional[WebSocket] = None
        self.last_activity = datetime.now(timezone.utc)
        self.streaming = False
        self.stream_task: Optional[asyncio.Task] = None
        self.viewport_width = 1280
        self.viewport_height = 720

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
        if session.stream_task:
            session.stream_task.cancel()
        try:
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
            '--disable-features=IsolateOrigins,site-per-process'
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
async def create_session(viewport_width: int = 1280, viewport_height: int = 720):
    """Create a new browser session"""
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
            ignore_https_errors=True
        )
        
        page = await context.new_page()
        
        # Create session immediately without waiting for navigation
        session = BrowserSession(session_id, page, context)
        session.viewport_width = viewport_width
        session.viewport_height = viewport_height
        sessions[session_id] = session
        
        logger.info(f"Created session {session_id} with viewport {viewport_width}x{viewport_height}")
        
        # Start navigation in background (don't wait)
        asyncio.create_task(navigate_session(session_id, "https://pocketoption.com"))
        
        return {"session_id": session_id, "status": "created"}
    
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        # Clean up if session creation failed
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

# WebSocket for browser streaming and control - using /api prefix for ingress
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
    
    # Start screenshot streaming task
    async def stream_screenshots():
        while session.streaming:
            try:
                if session.page and not session.page.is_closed():
                    try:
                        screenshot = await session.page.screenshot(
                            type="jpeg",
                            quality=50,
                            full_page=False,
                            timeout=5000  # 5 second timeout
                        )
                        screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
                        
                        await websocket.send_json({
                            "type": "frame",
                            "data": screenshot_base64
                        })
                    except Exception as screenshot_error:
                        # Send a placeholder message if screenshot fails
                        logger.debug(f"Screenshot failed: {screenshot_error}")
                        await asyncio.sleep(0.5)
                        continue
                
                # ~10 FPS for smooth experience
                await asyncio.sleep(0.1)
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(0.5)
    
    session.stream_task = asyncio.create_task(stream_screenshots())
    
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
        if session.stream_task:
            session.stream_task.cancel()
        session.websocket = None

async def handle_browser_event(session: BrowserSession, event: dict):
    """Handle browser events from the frontend"""
    try:
        page = session.page
        event_type = event.get("type")
        
        if event_type == "click":
            x = event.get("x", 0)
            y = event.get("y", 0)
            button = event.get("button", "left")
            await page.mouse.click(x, y, button=button)
        
        elif event_type == "dblclick":
            x = event.get("x", 0)
            y = event.get("y", 0)
            await page.mouse.dblclick(x, y)
        
        elif event_type == "mousemove":
            x = event.get("x", 0)
            y = event.get("y", 0)
            await page.mouse.move(x, y)
        
        elif event_type == "mousedown":
            x = event.get("x", 0)
            y = event.get("y", 0)
            button = event.get("button", "left")
            await page.mouse.move(x, y)
            await page.mouse.down(button=button)
        
        elif event_type == "mouseup":
            x = event.get("x", 0)
            y = event.get("y", 0)
            button = event.get("button", "left")
            await page.mouse.move(x, y)
            await page.mouse.up(button=button)
        
        elif event_type == "scroll":
            x = event.get("x", 0)
            y = event.get("y", 0)
            delta_x = event.get("deltaX", 0)
            delta_y = event.get("deltaY", 0)
            await page.mouse.move(x, y)
            await page.mouse.wheel(delta_x, delta_y)
        
        elif event_type == "keydown":
            key = event.get("key", "")
            await handle_key_event(page, key, "down")
        
        elif event_type == "keyup":
            key = event.get("key", "")
            await handle_key_event(page, key, "up")
        
        elif event_type == "keypress":
            key = event.get("key", "")
            if len(key) == 1:
                await page.keyboard.type(key)
        
        elif event_type == "input":
            # Direct text input for mobile keyboards
            text = event.get("text", "")
            if text:
                await page.keyboard.type(text)
        
        elif event_type == "touch":
            touches = event.get("touches", [])
            action = event.get("action", "tap")
            
            if action == "tap" and touches:
                x = touches[0].get("x", 0)
                y = touches[0].get("y", 0)
                await page.mouse.click(x, y)
            
            elif action == "move" and touches:
                x = touches[0].get("x", 0)
                y = touches[0].get("y", 0)
                await page.mouse.move(x, y)
        
        elif event_type == "resize":
            width = event.get("width", 1280)
            height = event.get("height", 720)
            session.viewport_width = width
            session.viewport_height = height
            await page.set_viewport_size({"width": width, "height": height})
        
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

async def handle_key_event(page: Page, key: str, action: str):
    """Handle keyboard events with proper key mapping"""
    # Map special keys
    key_map = {
        "Backspace": "Backspace",
        "Tab": "Tab",
        "Enter": "Enter",
        "Shift": "Shift",
        "Control": "Control",
        "Alt": "Alt",
        "Escape": "Escape",
        "Space": " ",
        " ": " ",
        "ArrowUp": "ArrowUp",
        "ArrowDown": "ArrowDown",
        "ArrowLeft": "ArrowLeft",
        "ArrowRight": "ArrowRight",
        "Delete": "Delete",
        "Home": "Home",
        "End": "End",
        "PageUp": "PageUp",
        "PageDown": "PageDown",
        "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
        "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
        "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
    }
    
    mapped_key = key_map.get(key, key)
    
    try:
        if action == "down":
            await page.keyboard.down(mapped_key)
        elif action == "up":
            await page.keyboard.up(mapped_key)
    except Exception as e:
        logger.debug(f"Key event error for {key}: {e}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
