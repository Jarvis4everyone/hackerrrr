/**
 * WebRTC utility functions
 * Provides shared configuration for WebRTC connections
 */

/**
 * Get ICE servers configuration for WebRTC
 * Uses STUN servers by default, and TURN servers if configured
 */
export function getIceServers() {
  const iceServers = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' },
    { urls: 'stun:stun2.l.google.com:19302' },
  ]

  // Check for TURN server configuration in environment
  // In production, you can set these via environment variables
  const turnServerUrl = import.meta.env.VITE_TURN_SERVER_URL
  const turnUsername = import.meta.env.VITE_TURN_SERVER_USERNAME
  const turnPassword = import.meta.env.VITE_TURN_SERVER_PASSWORD

  if (turnServerUrl) {
    const turnConfig = { urls: turnServerUrl }
    if (turnUsername && turnPassword) {
      turnConfig.username = turnUsername
      turnConfig.credential = turnPassword
    }
    iceServers.push(turnConfig)
    console.log('[WebRTC] Using TURN server:', turnServerUrl)
  }

  return { iceServers }
}

/**
 * Get WebSocket URL for WebRTC signaling
 * Automatically uses WSS (secure) when on HTTPS
 */
export function getWebSocketUrl(path) {
  // Get API URL from environment or construct from current location
  let API_BASE_URL = import.meta.env.VITE_API_URL

  if (!API_BASE_URL && import.meta.env.PROD) {
    // In production, construct backend URL
    const hostname = window.location.hostname
    if (hostname.includes('onrender.com')) {
      const parts = hostname.split('.')
      if (parts[0] === 'hackerrrr-frontend') {
        API_BASE_URL = `https://hackerrrr-backend.${parts.slice(1).join('.')}`
      } else {
        API_BASE_URL = '' // Fallback to same origin
      }
    } else {
      API_BASE_URL = '' // Same origin fallback
    }
  } else if (!API_BASE_URL) {
    API_BASE_URL = 'http://localhost:8000' // Development
  }

  // Remove trailing slash
  API_BASE_URL = API_BASE_URL.replace(/\/$/, '')

  // Construct WebSocket URL - ensure WSS for HTTPS
  let wsUrl
  if (API_BASE_URL) {
    // Convert HTTP/HTTPS to WS/WSS
    wsUrl = API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
  } else {
    // Use same origin with appropriate protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    wsUrl = `${protocol}//${window.location.host}`
  }

  // Ensure path starts with /
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  
  return `${wsUrl}${cleanPath}`
}

