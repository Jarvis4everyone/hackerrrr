/**
 * WebRTC Utilities
 * Handles TURN server configuration and RTCPeerConnection setup
 */

const METERED_API_KEY = '4b7268b361c4e1a08789e6415026801bfb20'
const METERED_API_URL = `https://x1.metered.live/api/v1/turn/credentials?apiKey=${METERED_API_KEY}`

// Cache for TURN credentials (refresh every hour)
let cachedIceServers = null
let cacheTimestamp = 0
const CACHE_DURATION = 60 * 60 * 1000 // 1 hour

/**
 * Fetch TURN server credentials from Metered.ca API
 * Falls back to STUN servers if API fails
 */
export async function getIceServers() {
  // Return cached credentials if still valid
  const now = Date.now()
  if (cachedIceServers && (now - cacheTimestamp) < CACHE_DURATION) {
    console.log('[WebRTC] Using cached ICE servers')
    return cachedIceServers
  }

  try {
    console.log('[WebRTC] Fetching TURN server credentials from Metered.ca...')
    const response = await fetch(METERED_API_URL)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch TURN credentials: ${response.status}`)
    }
    
    const iceServers = await response.json()
    
    // Validate response
    if (!Array.isArray(iceServers) || iceServers.length === 0) {
      throw new Error('Invalid ICE servers response')
    }
    
    // Cache the credentials
    cachedIceServers = iceServers
    cacheTimestamp = now
    
    console.log('[WebRTC] ✅ TURN server credentials fetched successfully')
    console.log('[WebRTC] ICE servers:', iceServers.length, 'servers configured')
    
    return iceServers
  } catch (error) {
    console.warn('[WebRTC] ⚠️ Failed to fetch TURN credentials, using STUN only:', error.message)
    
    // Fallback to STUN servers
    const fallbackServers = [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' },
      { urls: 'stun:stun2.l.google.com:19302' }
    ]
    
    // Cache fallback to avoid repeated API calls
    cachedIceServers = fallbackServers
    cacheTimestamp = now
    
    return fallbackServers
  }
}

/**
 * Create RTCPeerConnection with TURN server support
 */
export async function createPeerConnection(options = {}) {
  const iceServers = await getIceServers()
  
  const config = {
    iceServers,
    iceCandidatePoolSize: options.iceCandidatePoolSize || 10,
    ...options
  }
  
  console.log('[WebRTC] Creating RTCPeerConnection with', iceServers.length, 'ICE servers')
  
  return new RTCPeerConnection(config)
}

