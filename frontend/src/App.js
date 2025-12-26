import { useState, useEffect, useRef, useCallback } from "react";
import "@/App.css";
import { Toaster, toast } from "sonner";
import { Loader2, Wifi, WifiOff, RefreshCw } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace(/^https?/, (match) => match === 'https' ? 'wss' : 'ws');

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const wsRef = useRef(null);
  const imageRef = useRef(new Image());
  const lastFrameRef = useRef(null);
  const inputRef = useRef(null);
  
  // Get viewport dimensions
  const getViewportSize = useCallback(() => {
    const headerHeight = 56; // h-14 = 56px
    return {
      width: window.innerWidth,
      height: window.innerHeight - headerHeight
    };
  }, []);

  // Create session
  const createSession = useCallback(async () => {
    setIsConnecting(true);
    setError(null);
    
    try {
      const { width, height } = getViewportSize();
      const response = await fetch(`${API}/session/create?viewport_width=${width}&viewport_height=${height}`, {
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
    
    const ws = new WebSocket(`${WS_URL}/ws/${sid}`);
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
          lastFrameRef.current = data.data;
          renderFrame(data.data);
        } else if (data.type === 'error') {
          toast.error(data.message);
        }
      } catch (err) {
        console.error('Message parse error:', err);
      }
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };
    
    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('Erro de conexão');
      setIsConnected(false);
    };
  }, [getViewportSize]);

  // Render frame to canvas
  const renderFrame = useCallback((base64Data) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const img = imageRef.current;
    
    img.onload = () => {
      // Match canvas to image size
      if (canvas.width !== img.width || canvas.height !== img.height) {
        canvas.width = img.width;
        canvas.height = img.height;
      }
      ctx.drawImage(img, 0, 0);
    };
    
    img.src = `data:image/jpeg;base64,${base64Data}`;
  }, []);

  // Calculate coordinates relative to browser viewport
  const getCoordinates = useCallback((e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    const clientX = e.clientX ?? e.touches?.[0]?.clientX ?? 0;
    const clientY = e.clientY ?? e.touches?.[0]?.clientY ?? 0;
    
    return {
      x: Math.round((clientX - rect.left) * scaleX),
      y: Math.round((clientY - rect.top) * scaleY)
    };
  }, []);

  // Send event to backend
  const sendEvent = useCallback((event) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(event));
    }
  }, []);

  // Mouse event handlers
  const handleMouseMove = useCallback((e) => {
    const coords = getCoordinates(e);
    sendEvent({ type: 'mousemove', ...coords });
  }, [getCoordinates, sendEvent]);

  const handleMouseDown = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    const button = e.button === 2 ? 'right' : 'left';
    sendEvent({ type: 'mousedown', ...coords, button });
  }, [getCoordinates, sendEvent]);

  const handleMouseUp = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    const button = e.button === 2 ? 'right' : 'left';
    sendEvent({ type: 'mouseup', ...coords, button });
  }, [getCoordinates, sendEvent]);

  const handleClick = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    sendEvent({ type: 'click', ...coords, button: 'left' });
    
    // Focus hidden input for mobile keyboard
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [getCoordinates, sendEvent]);

  const handleDoubleClick = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    sendEvent({ type: 'dblclick', ...coords });
  }, [getCoordinates, sendEvent]);

  const handleContextMenu = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    sendEvent({ type: 'click', ...coords, button: 'right' });
  }, [getCoordinates, sendEvent]);

  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    sendEvent({
      type: 'scroll',
      ...coords,
      deltaX: e.deltaX,
      deltaY: e.deltaY
    });
  }, [getCoordinates, sendEvent]);

  // Touch event handlers
  const handleTouchStart = useCallback((e) => {
    e.preventDefault();
    const touch = e.touches[0];
    if (touch) {
      const coords = getCoordinates(e);
      sendEvent({ type: 'mousedown', ...coords, button: 'left' });
    }
    
    // Focus hidden input for mobile keyboard
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [getCoordinates, sendEvent]);

  const handleTouchMove = useCallback((e) => {
    e.preventDefault();
    const coords = getCoordinates(e);
    sendEvent({ type: 'mousemove', ...coords });
  }, [getCoordinates, sendEvent]);

  const handleTouchEnd = useCallback((e) => {
    e.preventDefault();
    // Use last known position
    const canvas = canvasRef.current;
    if (canvas) {
      sendEvent({ type: 'mouseup', x: 0, y: 0, button: 'left' });
      sendEvent({ type: 'click', x: 0, y: 0, button: 'left' });
    }
  }, [sendEvent]);

  // Keyboard event handlers
  const handleKeyDown = useCallback((e) => {
    // Don't prevent default for text input
    if (e.key.length === 1) {
      sendEvent({ type: 'keypress', key: e.key });
    } else {
      e.preventDefault();
      sendEvent({ type: 'keydown', key: e.key });
    }
  }, [sendEvent]);

  const handleKeyUp = useCallback((e) => {
    if (e.key.length > 1) {
      sendEvent({ type: 'keyup', key: e.key });
    }
  }, [sendEvent]);

  // Handle mobile input
  const handleInput = useCallback((e) => {
    const text = e.target.value;
    if (text) {
      sendEvent({ type: 'input', text });
      e.target.value = '';
    }
  }, [sendEvent]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      const { width, height } = getViewportSize();
      sendEvent({ type: 'resize', width, height });
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [getViewportSize, sendEvent]);

  // Initialize session on mount
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

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setSessionId(null);
    setIsConnected(false);
    
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
        
        {/* Browser Canvas */}
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
        />
        
        {/* Hidden input for mobile keyboard */}
        <input
          ref={inputRef}
          type="text"
          className="hidden-input"
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          onKeyUp={handleKeyUp}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck="false"
          data-testid="mobile-input"
        />
      </main>
    </div>
  );
}

export default App;
