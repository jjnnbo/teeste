import { useState, useEffect, useRef, useCallback } from "react";
import "@/App.css";
import { Toaster, toast } from "sonner";
import { Loader2, Wifi, WifiOff, RefreshCw } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace(/^https?/, (match) => match === 'https' ? 'wss' : 'ws');

console.log('Config:', { BACKEND_URL, API, WS_URL });

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [hasFrames, setHasFrames] = useState(false);
  const [error, setError] = useState(null);
  const [fps, setFps] = useState(0);
  
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const imageRef = useRef(new Image());
  const inputRef = useRef(null);
  const frameCountRef = useRef(0);
  const lastFpsUpdateRef = useRef(Date.now());
  
  // Track actual canvas dimensions for precise coordinate mapping
  const canvasDimensionsRef = useRef({ width: 1280, height: 720 });
  
  // Get viewport dimensions
  const getViewportSize = useCallback(() => {
    const headerHeight = 56;
    return {
      width: Math.floor(window.innerWidth),
      height: Math.floor(window.innerHeight - headerHeight)
    };
  }, []);

  // Target URL
  const TARGET_URL = "https://pocketoption.com/en/login";

  // Create session
  const createSession = useCallback(async () => {
    setIsConnecting(true);
    setError(null);
    
    try {
      const { width, height } = getViewportSize();
      const url = `${API}/session/create?viewport_width=${width}&viewport_height=${height}&start_url=${encodeURIComponent(TARGET_URL)}`;
      const response = await fetch(url, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to create session');
      }
      
      const data = await response.json();
      setSessionId(data.session_id);
      toast.success("Sessão criada com sucesso!");
      return data.session_id;
    } catch (err) {
      console.error('Session creation error:', err);
      setError('Erro ao criar sessão. Tente novamente.');
      toast.error("Erro ao conectar");
      setIsConnecting(false);
      return null;
    }
  }, [getViewportSize]);

  // Connect WebSocket
  const connectWebSocket = useCallback((sid) => {
    if (!sid) return;
    
    const wsUrl = `${WS_URL}/api/ws/${sid}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    
    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      console.log('WebSocket connected');
      
      // Send initial viewport size
      const { width, height } = getViewportSize();
      ws.send(JSON.stringify({
        type: 'resize',
        width,
        height
      }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'frame') {
          if (!hasFrames) setHasFrames(true);
          renderFrame(data.data);
          
          // FPS counter
          frameCountRef.current++;
          const now = Date.now();
          if (now - lastFpsUpdateRef.current >= 1000) {
            setFps(frameCountRef.current);
            frameCountRef.current = 0;
            lastFpsUpdateRef.current = now;
          }
        } else if (data.type === 'error') {
          toast.error(data.message);
        }
      } catch (err) {
        console.error('Message parse error:', err);
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      setHasFrames(false);
      console.log('WebSocket disconnected');
    };
    
    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('Erro de conexão');
      setIsConnected(false);
    };
  }, [getViewportSize, hasFrames]);

  // Render frame to canvas with exact dimensions
  const renderFrame = useCallback((base64Data) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d', { alpha: false });
    const img = imageRef.current;
    
    img.onload = () => {
      // Update canvas to match image exactly
      if (canvas.width !== img.width || canvas.height !== img.height) {
        canvas.width = img.width;
        canvas.height = img.height;
        canvasDimensionsRef.current = { width: img.width, height: img.height };
      }
      ctx.drawImage(img, 0, 0);
    };
    
    img.src = `data:image/jpeg;base64,${base64Data}`;
  }, []);

  // PRECISE coordinate calculation - critical for accurate clicks
  const getCoordinates = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    const canvasWidth = canvasDimensionsRef.current.width;
    const canvasHeight = canvasDimensionsRef.current.height;
    
    // Get the displayed size
    const displayWidth = rect.width;
    const displayHeight = rect.height;
    
    // Calculate scale factors
    const scaleX = canvasWidth / displayWidth;
    const scaleY = canvasHeight / displayHeight;
    
    // Get client coordinates
    let clientX, clientY;
    if (e.touches && e.touches.length > 0) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else if (e.changedTouches && e.changedTouches.length > 0) {
      clientX = e.changedTouches[0].clientX;
      clientY = e.changedTouches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }
    
    // Calculate precise coordinates
    const x = (clientX - rect.left) * scaleX;
    const y = (clientY - rect.top) * scaleY;
    
    // Return with decimal precision for subpixel accuracy
    return {
      x: Math.max(0, Math.min(canvasWidth, x)),
      y: Math.max(0, Math.min(canvasHeight, y))
    };
  }, []);

  // Send event to backend
  const sendEvent = useCallback((event) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(event));
    }
  }, []);

  // Mouse handlers with debounced mousemove
  const lastMoveRef = useRef(0);
  const MOVE_THROTTLE = 16; // ~60fps for mouse move
  
  const handleMouseMove = useCallback((e) => {
    const now = Date.now();
    if (now - lastMoveRef.current < MOVE_THROTTLE) return;
    lastMoveRef.current = now;
    
    const coords = getCoordinates(e);
    sendEvent({ type: 'mousemove', ...coords });
  }, [getCoordinates, sendEvent]);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    const coords = getCoordinates(e);
    const button = e.button === 2 ? 'right' : 'left';
    sendEvent({ type: 'mousedown', ...coords, button });
  }, [getCoordinates, sendEvent]);

  const handleMouseUp = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    const coords = getCoordinates(e);
    const button = e.button === 2 ? 'right' : 'left';
    sendEvent({ type: 'mouseup', ...coords, button });
  }, [getCoordinates, sendEvent]);

  const handleClick = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    const coords = getCoordinates(e);
    console.log('Click at:', coords);
    sendEvent({ type: 'click', ...coords, button: 'left' });
    
    // Focus hidden input for mobile keyboard
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [getCoordinates, sendEvent]);

  const handleDoubleClick = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    const coords = getCoordinates(e);
    sendEvent({ type: 'dblclick', ...coords });
  }, [getCoordinates, sendEvent]);

  const handleContextMenu = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    const coords = getCoordinates(e);
    sendEvent({ type: 'click', ...coords, button: 'right' });
  }, [getCoordinates, sendEvent]);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    sendEvent({
      type: 'scroll',
      ...coords,
      deltaX: Math.round(e.deltaX),
      deltaY: Math.round(e.deltaY)
    });
  }, [getCoordinates, sendEvent]);

  // Touch handlers with precise tracking
  const touchStartRef = useRef({ x: 0, y: 0, time: 0 });
  const lastTouchRef = useRef({ x: 0, y: 0 });
  
  const handleTouchStart = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    touchStartRef.current = { ...coords, time: Date.now() };
    lastTouchRef.current = coords;
    sendEvent({ type: 'mousedown', ...coords, button: 'left' });
    
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [getCoordinates, sendEvent]);

  const handleTouchMove = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    lastTouchRef.current = coords;
    sendEvent({ type: 'mousemove', ...coords });
  }, [getCoordinates, sendEvent]);

  const handleTouchEnd = useCallback((e) => {
    e.preventDefault();
    const coords = lastTouchRef.current;
    const startCoords = touchStartRef.current;
    const elapsed = Date.now() - startCoords.time;
    
    // Calculate distance moved
    const dx = Math.abs(coords.x - startCoords.x);
    const dy = Math.abs(coords.y - startCoords.y);
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    sendEvent({ type: 'mouseup', ...coords, button: 'left' });
    
    // Only send click if it was a tap (short duration, small movement)
    if (elapsed < 300 && distance < 10) {
      sendEvent({ type: 'click', ...coords, button: 'left' });
    }
    
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [sendEvent]);

  // Keyboard handlers
  const handleKeyDown = useCallback((e) => {
    if (e.key.length === 1) {
      sendEvent({ type: 'keypress', key: e.key, code: e.code });
    } else {
      e.preventDefault();
      sendEvent({ type: 'keydown', key: e.key, code: e.code });
    }
  }, [sendEvent]);

  const handleKeyUp = useCallback((e) => {
    if (e.key.length > 1) {
      sendEvent({ type: 'keyup', key: e.key, code: e.code });
    }
  }, [sendEvent]);

  // Mobile input handler
  const handleInput = useCallback((e) => {
    const text = e.target.value;
    if (text) {
      sendEvent({ type: 'input', text });
      e.target.value = '';
    }
  }, [sendEvent]);

  const handleMobileKeyDown = useCallback((e) => {
    if (e.key === 'Backspace' || e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      sendEvent({ type: 'keydown', key: e.key, code: e.code });
    }
  }, [sendEvent]);

  // Handle resize with debounce
  useEffect(() => {
    let resizeTimeout;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        const { width, height } = getViewportSize();
        sendEvent({ type: 'resize', width, height });
      }, 100);
    };
    
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimeout);
    };
  }, [getViewportSize, sendEvent]);

  // Global keyboard listener
  useEffect(() => {
    if (!isConnected) return;
    
    const handleGlobalKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      
      e.preventDefault();
      if (e.key.length === 1) {
        sendEvent({ type: 'keypress', key: e.key, code: e.code });
      } else {
        sendEvent({ type: 'keydown', key: e.key, code: e.code });
      }
    };
    
    const handleGlobalKeyUp = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key.length > 1) {
        sendEvent({ type: 'keyup', key: e.key, code: e.code });
      }
    };
    
    window.addEventListener('keydown', handleGlobalKeyDown);
    window.addEventListener('keyup', handleGlobalKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleGlobalKeyDown);
      window.removeEventListener('keyup', handleGlobalKeyUp);
    };
  }, [isConnected, sendEvent]);

  // Initialize session
  useEffect(() => {
    let mounted = true;
    
    const init = async () => {
      const sid = await createSession();
      if (mounted && sid) {
        connectWebSocket(sid);
      }
    };
    
    init();
    
    return () => {
      mounted = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [createSession, connectWebSocket]);

  // Refresh handler
  const handleRefresh = useCallback(async () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setSessionId(null);
    setIsConnected(false);
    setHasFrames(false);
    setIsConnecting(true);
    setFps(0);
    
    const sid = await createSession();
    if (sid) {
      connectWebSocket(sid);
    }
  }, [createSession, connectWebSocket]);

  return (
    <div className="app-container" data-testid="app-container">
      <Toaster position="top-center" richColors />
      
      {/* Header */}
      <header className="app-header" data-testid="header">
        <div className="logo" data-testid="logo">
          <span className="logo-text">MAGO</span>
          <span className="logo-accent">TRADER</span>
        </div>
        
        <div className="header-actions">
          {/* FPS Counter */}
          {isConnected && (
            <div className="fps-counter" data-testid="fps-counter">
              {fps} FPS
            </div>
          )}
          
          <button
            className="refresh-btn"
            onClick={handleRefresh}
            disabled={isConnecting}
            data-testid="refresh-btn"
            aria-label="Recarregar"
          >
            <RefreshCw className={`icon ${isConnecting ? 'spinning' : ''}`} />
          </button>
          
          <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} data-testid="connection-status">
            {isConnected ? <Wifi className="icon" /> : <WifiOff className="icon" />}
          </div>
        </div>
      </header>
      
      {/* Main Content */}
      <main className="browser-container" ref={containerRef} data-testid="browser-container">
        {/* Loading State */}
        {isConnecting && (
          <div className="loading-overlay" data-testid="loading-overlay">
            <div className="loading-content">
              <Loader2 className="loading-spinner" />
              <p>Conectando ao servidor...</p>
            </div>
          </div>
        )}
        
        {/* Site Loading State */}
        {isConnected && !hasFrames && !isConnecting && (
          <div className="loading-overlay site-loading" data-testid="site-loading-overlay">
            <div className="loading-content">
              <Loader2 className="loading-spinner" />
              <p>Carregando site...</p>
              <span className="loading-hint">Aguarde enquanto o site é carregado</span>
            </div>
          </div>
        )}
        
        {/* Error State */}
        {error && !isConnecting && (
          <div className="error-overlay" data-testid="error-overlay">
            <div className="error-content">
              <WifiOff className="error-icon" />
              <p>{error}</p>
              <button
                className="retry-btn"
                onClick={handleRefresh}
                data-testid="retry-btn"
              >
                Tentar Novamente
              </button>
            </div>
          </div>
        )}
        
        {/* Browser Canvas - with precise event handling */}
        <canvas
          ref={canvasRef}
          className="browser-canvas"
          data-testid="browser-canvas"
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onClick={handleClick}
          onDoubleClick={handleDoubleClick}
          onContextMenu={handleContextMenu}
          onWheel={handleWheel}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          tabIndex={0}
          style={{ touchAction: 'none' }}
        />
        
        {/* Hidden input for mobile keyboard */}
        <input
          ref={inputRef}
          type="text"
          className="hidden-input"
          onInput={handleInput}
          onKeyDown={handleMobileKeyDown}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck="false"
          enterKeyHint="send"
          inputMode="text"
          data-testid="mobile-input"
          aria-label="Mobile keyboard input"
        />
      </main>
    </div>
  );
}

export default App;
