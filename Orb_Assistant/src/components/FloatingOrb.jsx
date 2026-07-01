// src/components/FloatingOrb.jsx - Optimized with Lerp
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './FloatingOrb.css';

const FloatingOrb = ({ workerId = "CALI_UNIT_01" }) => {
  const [position, setPosition] = useState({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  const [targetPos, setTargetPos] = useState({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
  const [isMoving, setIsMoving] = useState(false);
  const [animationMode, setAnimationMode] = useState('idle'); // idle, avoiding, assisting, learning
  const [orbSize, setOrbSize] = useState(1.0); // multiplier for size
  const [orbSpeed, setOrbSpeed] = useState(0.05); // lerp factor
  const [orbColor, setOrbColor] = useState('rgba(0, 255, 200, 0.8)'); // glassy blue-green
  const [mood, setMood] = useState(0.75); // 0-1 scale for orb health/color

  // Calculate mood based on activity
  const updateMood = useCallback(() => {
    let newMood = 0.75;

    if (animationMode === 'assisting') newMood += 0.15;
    if (animationMode === 'avoiding') newMood -= 0.1;
    if (isMoving) newMood += 0.05;

    // Idle time factor (simplified)
    const idleTime = Date.now() - (lastActivityRef.current || Date.now());
    if (idleTime > 15000) newMood += 0.1;

    newMood = Math.max(0, Math.min(1, newMood));
    setMood(newMood);
  }, [animationMode, isMoving]);

  const lastActivityRef = useRef(Date.now());

  // Color based on mood/health
  const getOrbColor = (mood) => {
    if (mood >= 0.8) return '#2dd4ff'; // Bright blue - healthy
    if (mood >= 0.6) return '#facc15'; // Yellow - warning
    return '#f87171'; // Red - unhealthy
  };

  // Convert hex to rgb
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  };

  // Update mood periodically
  useEffect(() => {
    const interval = setInterval(updateMood, 1000);
    return () => clearInterval(interval);
  }, [updateMood]);

  // Refs for animation loop
  const positionRef = useRef(position);
  const targetRef = useRef(targetPos);
  const lerpFactorRef = useRef(orbSpeed); // Smoothness factor (learnable!)
  const frameCountRef = useRef(0);

  // Connect to UCM backend
  const wsRef = useRef(null);

  useEffect(() => {
    positionRef.current = position;
  }, [position]);

  useEffect(() => {
    targetRef.current = targetPos;
  }, [targetPos]);

  useEffect(() => {
    lerpFactorRef.current = orbSpeed;
  }, [orbSpeed]);

  // ✅ SAFE: Listen for cursor movement (not screen capture)
  useEffect(() => {
    const handleMouseMove = (e) => {
      lastActivityRef.current = Date.now(); // Update activity timestamp

      // Update target position based on cursor
      const cursorX = e.clientX;
      const cursorY = e.clientY;

      // Calculate avoidance vector
      const dx = cursorX - positionRef.current.x;
      const dy = cursorY - positionRef.current.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      const avoidanceDistance = 350; // pixels

      if (distance < avoidanceDistance) {
        // Cursor is too close - calculate avoidance target
        const angle = Math.atan2(dy, dx);
        const avoidDistance = avoidanceDistance * 1.3; // Extra buffer

        let newTargetX = cursorX + Math.cos(angle) * avoidDistance;
        let newTargetY = cursorY + Math.sin(angle) * avoidDistance;

        // Clamp to viewport
        newTargetX = Math.max(50, Math.min(window.innerWidth - 50, newTargetX));
        newTargetY = Math.max(50, Math.min(window.innerHeight - 50, newTargetY));

        setTargetPos({ x: newTargetX, y: newTargetY });
        setIsMoving(true);
        setAnimationMode('avoiding');

        // Send movement pattern to SKG for learning
        if (frameCountRef.current % 30 === 0) { // Sample every 30 frames
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              action: 'learn_movement',
              pattern: {
                from: positionRef.current,
                to: { x: newTargetX, y: newTargetY },
                cursor_distance: distance,
                velocity: lerpFactorRef.current,
                timestamp: Date.now()
              }
            }));
          }
        }
      } else if (distance > avoidanceDistance * 1.5) {
        // Cursor is far away - gentle floating behavior
        const time = Date.now() * 0.001; // Convert to seconds
        const floatRadius = 100;
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;

        // Gentle floating motion
        const floatX = centerX + Math.sin(time * 0.5) * floatRadius;
        const floatY = centerY + Math.cos(time * 0.3) * floatRadius * 0.5;

        setTargetPos({ x: floatX, y: floatY });
        setAnimationMode('idle');
      }

      frameCountRef.current++;
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Listen for settings updates
  useEffect(() => {
    if (window.electronAPI) {
      const handleSettingsUpdate = (event, settings) => {
        console.log('⚙️ Settings update:', settings);

        if (settings.color) setOrbColor(settings.color);
        if (settings.size) setOrbSize(settings.size);
        if (settings.speed) setOrbSpeed(settings.speed);
        // pulse could be used for animation timing if implemented
      };

      const handleOpenSettings = () => {
        // Send IPC to main process to open settings window
        if (window.electronAPI) {
          window.electronAPI.openSettings();
        }
      };

      window.electronAPI.onSettingsUpdate(handleSettingsUpdate);
      window.electronAPI.onOpenSettings(handleOpenSettings);

      return () => {
        // Clean up if needed
      };
    }
  }, []);

  // 🎮 LERP ANIMATION LOOP
  useEffect(() => {
    let rafId;

    const lerp = (start, end, factor) => {
      return start + (end - start) * factor;
    };

    const animate = () => {
      const current = positionRef.current;
      let target = targetRef.current;

      // Update idle floating target continuously
      if (animationMode === 'idle') {
        const time = Date.now() * 0.001; // Convert to seconds
        const floatRadius = 100;
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;

        // Gentle floating motion
        const floatX = centerX + Math.sin(time * 0.5) * floatRadius;
        const floatY = centerY + Math.cos(time * 0.3) * floatRadius * 0.5;

        target = { x: floatX, y: floatY };
        targetRef.current = target; // Update ref so it's consistent
      }

      // Dynamic lerp factor based on animation mode
      let factor = lerpFactorRef.current;
      if (animationMode === 'avoiding') factor = 0.15; // Faster avoidance
      if (animationMode === 'assisting') factor = 0.08; // Slower, intentional movement

      const newX = lerp(current.x, target.x, factor);
      const newY = lerp(current.y, target.y, factor);

      // Check if movement is complete (within 5px) - but for idle, never complete since target moves
      const distanceToTarget = Math.sqrt(
        (target.x - newX) ** 2 + (target.y - newY) ** 2
      );

      if (distanceToTarget < 5 && animationMode !== 'idle') {
        setIsMoving(false);
        if (animationMode === 'avoiding') {
          setAnimationMode('idle');
        }
      } else {
        setIsMoving(true);
      }

      // Only update position if there's actual movement
      if (Math.abs(newX - current.x) > 0.1 || Math.abs(newY - current.y) > 0.1) {
        setPosition({ x: newX, y: newY });
      }

      rafId = requestAnimationFrame(animate);
    };

    console.log('🎮 Starting animation loop');
    rafId = requestAnimationFrame(animate);
    return () => {
      console.log('🛑 Stopping animation loop');
      cancelAnimationFrame(rafId);
    };
  }, [animationMode]);

  // WebSocket connection to UCM for SKG learning
  useEffect(() => {
    console.log('🔌 Attempting to connect to orb server...');

    const connectWebSocket = () => {
      try {
        // Orb_Assistant is not a worker.
        // It uses a dedicated ORB channel and handshake.
        // Do not reuse worker logic.
        const ws = new WebSocket(`ws://localhost:8000/ws/orb_assistant`);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('✅ Orb connected to UCM SKG server - Sending Handshake');
          ws.send(JSON.stringify({
            type: "ORB_HANDSHAKE",
            orb_id: "ORB_ASSISTANT_PRIMARY_V1",
            role: "orb",
            capabilities: ["presence", "mediation", "ui"]
          }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('📨 Received WS message:', data);

            // Update lerp factor based on learned preferences
            if (data.type === 'lerp_optimization') {
              lerpFactorRef.current = data.optimal_velocity;
              console.log('🎯 Updated lerp factor:', lerpFactorRef.current);
            }

            // ECM-driven drift target (e.g., user prefers orb on right side)
            if (data.type === 'drift_preference') {
              const { preferred_quadrant } = data;
              const centerX = window.innerWidth / 2;
              const centerY = window.innerHeight / 2;

              const quadrantTargets = {
                'top_left': { x: centerX - 200, y: centerY - 200 },
                'top_right': { x: centerX + 200, y: centerY - 200 },
                'bottom_left': { x: centerX - 200, y: centerY + 200 },
                'bottom_right': { x: centerX + 200, y: centerY + 200 },
                'center': { x: centerX, y: centerY }
              };

              const newTarget = quadrantTargets[preferred_quadrant] || quadrantTargets['center'];
              setTargetPos(newTarget);
              console.log('🎯 Updated drift target:', newTarget);
            }
          } catch (error) {
            console.error('❌ Error parsing WS message:', error);
          }
        };

        ws.onclose = (event) => {
          console.log('🔌 WebSocket closed:', event.code, event.reason);
          // Attempt to reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
        };

      } catch (error) {
        console.error('❌ Failed to create WebSocket:', error);
        // Retry connection
        setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleOrbClick = async () => {
    lastActivityRef.current = Date.now(); // Update activity timestamp
    setAnimationMode('assisting');

    // User explicitly clicked orb - VOLUNTARY interaction
    wsRef.current?.send(JSON.stringify({
      action: 'voluntary_interaction',
      type: 'orb_click',
      timestamp: Date.now()
    }));

    // Query mode
    setTimeout(() => setAnimationMode('idle'), 2000);
  };

  return (
    <>
      {/* ... orb component ... */}
      <div
        className={`floating-orb ${animationMode}`}
        style={{
          position: 'fixed',
          left: `${position.x - 75 * orbSize}px`,
          top: `${position.y - 75 * orbSize}px`,
          transform: `scale(${isMoving ? 1.05 : 1})`,
          transition: 'transform 0.1s ease-out',
          pointerEvents: 'auto'
        }}
        onClick={handleOrbClick}
        onMouseEnter={() => {
          if (window.electronAPI) {
             window.electronAPI.setIgnoreMouseEvents(false);
          }
        }}
        onMouseLeave={() => {
          if (window.electronAPI) {
             window.electronAPI.setIgnoreMouseEvents(true, { forward: true });
          }
        }}
      >
        <div className="orb-visual" style={{ transform: `scale(${orbSize})` }}>
          <div
            className={`orb-core ${animationMode}`}
            style={{
              background: `radial-gradient(circle, ${orbColor}, #1a1a2e)`,
              boxShadow: `0 0 30px ${orbColor}, inset 0 0 20px rgba(74, 144, 226, 0.5)`
            }}
          />
          <div
            className={`orb-aura ${animationMode}`}
            style={{
              background: `radial-gradient(circle, ${orbColor.replace('0.8', '0.3').replace('0.9', '0')}, transparent)`
            }}
          />
        </div>
        <div style={{
            position: 'absolute',
            bottom: '-40px',
            width: '200px',
            textAlign: 'center',
            color: 'rgba(0, 255, 200, 1)',
            fontFamily: '"Segoe UI", sans-serif',
            fontSize: '14px',
            fontWeight: 'bold',
            left: '50%',
            transform: 'translateX(-50%)',
            textShadow: '0 0 10px rgba(0, 255, 200, 0.8)',
            pointerEvents: 'none',
            letterSpacing: '1px'
        }}>
            Caleon (CALI)
        </div>
      </div>
      <PerformanceHUD />
    </>
  );
};

// 📡 FRONTEND PERFORMANCE INDICATORS
const PerformanceHUD = () => {
  const [metrics, setMetrics] = useState({
    skg_latency: 0,
    memory_usage: 0,
    fragmentation: 0,
    edge_cutter: false
  });

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/api/orb/performance');
        const data = await response.json();

        setMetrics({
          skg_latency: data.metrics.query_latency_ms.toFixed(0),
          memory_usage: data.metrics.memory_usage_mb.toFixed(0),
          fragmentation: (data.metrics.fragmentation_ratio * 100).toFixed(0),
          edge_cutter: data.health_status === 'degraded'
        });

        // Visual indication of edge cutter mode
        if (data.health_status === 'degraded') {
          document.body.style.border = '2px solid #F5A623'; // Orange border
        } else {
          document.body.style.border = 'none';
        }
      } catch (error) {
        // Fallback if server not available
        setMetrics({
          skg_latency: 'N/A',
          memory_usage: 'N/A',
          fragmentation: 'N/A',
          edge_cutter: false
        });
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="performance-hud" style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      background: 'rgba(0,0,0,0.8)',
      color: metrics.edge_cutter ? '#F5A623' : '#50E3C2',
      padding: '10px',
      borderRadius: '4px',
      fontSize: '12px',
      zIndex: 999999,
      fontFamily: 'monospace'
    }}>
      <div>SKG Latency: {metrics.skg_latency}ms</div>
      <div>Memory: {metrics.memory_usage}MB</div>
      <div>Fragmentation: {metrics.fragmentation}%</div>
      {metrics.edge_cutter && <div style={{color: '#F5A623'}}>⚡ EDGE CUTTER ACTIVE</div>}
    </div>
  );
};

export default FloatingOrb;