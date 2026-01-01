import { useEffect, useState, useRef } from 'react'
import { MonitorSpeaker, Play, Square, Monitor } from 'lucide-react'
import { getPCs, startScreenStream, stopStream, getStreamStatus } from '../services/api'
import { createPeerConnection } from '../utils/webrtc'

// Get API URL from environment or construct from current location
let API_BASE_URL = import.meta.env.VITE_API_URL
if (!API_BASE_URL && import.meta.env.PROD) {
  const hostname = window.location.hostname
  if (hostname.includes('onrender.com')) {
    const parts = hostname.split('.')
    if (parts[0] === 'hackerrrr-frontend') {
      API_BASE_URL = `https://hackerrrr-backend.${parts.slice(1).join('.')}`
    } else {
      API_BASE_URL = ''
    }
  } else {
    API_BASE_URL = ''
  }
} else if (!API_BASE_URL) {
  API_BASE_URL = 'http://localhost:8000'
}

API_BASE_URL = API_BASE_URL.replace(/\/$/, '')

const WS_BASE_URL = API_BASE_URL 
  ? API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
  : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

const Screen = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [connectionState, setConnectionState] = useState('disconnected')
  const videoRef = useRef(null)
  const peerConnectionRef = useRef(null)
  const wsRef = useRef(null)
  const connectingRef = useRef(false)

  useEffect(() => {
    loadPCs()
    const interval = setInterval(loadPCs, 3000)
    return () => {
      clearInterval(interval)
      cleanupWebRTC()
    }
  }, [])

  useEffect(() => {
    if (selectedPC) {
      checkStreamStatus()
      const interval = setInterval(checkStreamStatus, 2000)
      return () => clearInterval(interval)
    } else {
      cleanupWebRTC()
    }
  }, [selectedPC])

  useEffect(() => {
    if (connectionState === 'connected' && videoRef.current) {
      const video = videoRef.current
      if (video.srcObject) {
        video.play().catch((error) => {
          console.error('[WebRTC] Error auto-playing video:', error)
        })
      }
    }
  }, [connectionState])

  useEffect(() => {
    if (streamStatus?.has_active_stream && streamStatus?.stream_type === 'screen' && selectedPC) {
      const ws = wsRef.current
      const isConnected = ws && ws.readyState === WebSocket.OPEN
      const isConnecting = ws && ws.readyState === WebSocket.CONNECTING
      
      if (!isConnected && !isConnecting && !connectingRef.current && connectionState === 'disconnected') {
        console.log('[WebRTC] Stream detected as active, initiating connection...')
        connectToStream(selectedPC)
      }
    }
  }, [streamStatus, selectedPC, connectionState])

  const cleanupWebRTC = () => {
    connectingRef.current = false
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close()
      peerConnectionRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setConnectionState('disconnected')
  }

  const loadPCs = async () => {
    try {
      const data = await getPCs(true)
      setPCs(data.pcs || [])
    } catch (error) {
      console.error('Error loading PCs:', error)
    }
  }

  const checkStreamStatus = async () => {
    if (!selectedPC) return
    try {
      const status = await getStreamStatus(selectedPC)
      setStreamStatus(status)
      
      if (status.has_active_stream && status.stream_type === 'screen') {
        const ws = wsRef.current
        const isConnected = ws && ws.readyState === WebSocket.OPEN
        const isConnecting = ws && ws.readyState === WebSocket.CONNECTING
        
        if (!isConnected && !isConnecting && !connectingRef.current) {
          console.log('[WebRTC] Stream is active, connecting to frontend WebSocket...')
          connectingRef.current = true
          connectToStream(selectedPC)
        }
      } else if (!status.has_active_stream) {
        if (wsRef.current || peerConnectionRef.current) {
          cleanupWebRTC()
        }
      }
    } catch (error) {
      console.error('Error checking stream status:', error)
    }
  }

  const connectToStream = async (pcId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('[WebRTC] Already connected, skipping...')
      return
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      console.log('[WebRTC] Connection in progress, skipping...')
      return
    }
    
    try {
      setConnectionState('connecting')
      cleanupWebRTC()
      
      const wsUrl = `${WS_BASE_URL}/ws/frontend/${pcId}/screen`
      console.log('[WebRTC] Connecting to:', wsUrl)
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WebRTC] WebSocket connected for signaling')
        connectingRef.current = false
      }

      ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('[WebRTC] Received message:', data.type)
          await handleSignalingMessage(data, pcId)
        } catch (error) {
          console.error('[WebRTC] Error handling message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WebRTC] WebSocket error:', error)
        setConnectionState('error')
        if (trackCheckInterval) {
          clearInterval(trackCheckInterval)
        }
      }

      // Create peer connection with TURN server support
      const pc = await createPeerConnection({ iceCandidatePoolSize: 10 })
      peerConnectionRef.current = pc
      
      let trackCheckInterval = null
      
      ws.onclose = (event) => {
        if (trackCheckInterval) {
          clearInterval(trackCheckInterval)
          trackCheckInterval = null
        }
        console.log('[WebRTC] WebSocket closed', event.code, event.reason)
        connectingRef.current = false
        setConnectionState('disconnected')
      }

      pc.ontrack = (event) => {
        console.log('[WebRTC] ===== TRACK RECEIVED =====')
        console.log('[WebRTC] Track kind:', event.track.kind)
        
        if (event.track.kind === 'video') {
          console.log('[WebRTC] Video track received!')
          
          if (!videoRef.current) {
            console.error('[WebRTC] videoRef.current is null!')
            return
          }
          
          const stream = event.streams[0] || new MediaStream([event.track])
          console.log('[WebRTC] Setting video srcObject')
          
          videoRef.current.srcObject = stream
          setConnectionState('connected')
          
          setTimeout(() => {
            if (videoRef.current) {
              console.log('[WebRTC] Attempting to play video...')
              videoRef.current.play().then(() => {
                console.log('[WebRTC] ✅ Video is playing successfully!')
                console.log('[WebRTC] Video dimensions:', videoRef.current.videoWidth, 'x', videoRef.current.videoHeight)
              }).catch((error) => {
                console.error('[WebRTC] ❌ Error playing video:', error)
              })
            }
          }, 100)
        }
      }

      pc.onicecandidate = (event) => {
        if (event.candidate && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'webrtc_ice_candidate',
            candidate: {
              candidate: event.candidate.candidate,
              sdpMLineIndex: event.candidate.sdpMLineIndex,
              sdpMid: event.candidate.sdpMid
            }
          }))
        }
      }

      pc.onconnectionstatechange = () => {
        console.log('[WebRTC] Connection state changed:', pc.connectionState)
        setConnectionState(pc.connectionState)
        
        if (pc.connectionState === 'connected') {
          console.log('[WebRTC] Connection established!')
        }
        
        if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
          cleanupWebRTC()
        }
      }
      
      trackCheckInterval = setInterval(() => {
        if (pc.connectionState === 'connected') {
          const receivers = pc.getReceivers()
          const videoReceivers = receivers.filter(r => r.track && r.track.kind === 'video')
          if (videoReceivers.length > 0) {
            console.log('[WebRTC] Found', videoReceivers.length, 'video receiver(s)')
            if (videoRef.current && !videoRef.current.srcObject) {
              console.log('[WebRTC] Found video receiver but no srcObject, setting it now...')
              const stream = new MediaStream(videoReceivers.map(r => r.track).filter(Boolean))
              videoRef.current.srcObject = stream
              videoRef.current.play().catch(console.error)
            }
          }
        }
      }, 1000)

      console.log('[WebRTC] Waiting for offer from server...')

    } catch (error) {
      console.error('[WebRTC] Error connecting to stream:', error)
      connectingRef.current = false
      setConnectionState('error')
      cleanupWebRTC()
    }
  }

  const handleSignalingMessage = async (data, pcId) => {
    const pc = peerConnectionRef.current
    if (!pc) return

    try {
      if (data.type === 'webrtc_offer') {
        await pc.setRemoteDescription(new RTCSessionDescription({
          type: 'offer',
          sdp: data.sdp
        }))
        
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'webrtc_answer',
            sdp: answer.sdp
          }))
        }
        console.log('[WebRTC] Answer sent, connection in progress...')
      } else if (data.type === 'webrtc_ice_candidate') {
        if (data.candidate) {
          await pc.addIceCandidate(new RTCIceCandidate({
            candidate: data.candidate.candidate,
            sdpMLineIndex: data.candidate.sdpMLineIndex,
            sdpMid: data.candidate.sdpMid
          }))
        }
      } else if (data.type === 'webrtc_error') {
        console.error('[WebRTC] Error from server:', data.message)
        setConnectionState('error')
        cleanupWebRTC()
      }
    } catch (error) {
      console.error('[WebRTC] Error handling signaling message:', error)
    }
  }

  const handleStartStream = async () => {
    if (!selectedPC) {
      alert('Please select a PC')
      return
    }
    setLoading(true)
    try {
      await startScreenStream(selectedPC)
      await checkStreamStatus()
    } catch (error) {
      alert('Error starting screen stream: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleStopStream = async () => {
    if (!selectedPC) return
    setLoading(true)
    try {
      await stopStream(selectedPC)
      cleanupWebRTC()
      await checkStreamStatus()
    } catch (error) {
      alert('Error stopping stream: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const isStreaming = streamStatus?.has_active_stream && streamStatus?.stream_type === 'screen'

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl sm:text-2xl font-mono text-hack-green">Screen Share</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        {/* Left Sidebar - PC Selection & Controls */}
        <div className="lg:col-span-4 space-y-4 sm:space-y-6">
          {/* PC Selection Card */}
          <div className="bg-hack-dark/90 backdrop-blur-sm border border-gray-800 rounded-xl p-4 sm:p-6 shadow-xl">
            <div className="flex items-center gap-3 mb-4 sm:mb-6">
              <Monitor className="text-hack-green" size={20} />
              <h2 className="text-base sm:text-lg font-semibold text-white">Connected Devices</h2>
            </div>
            <div className="space-y-2 max-h-80 overflow-y-auto custom-scrollbar">
              {pcs.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-white/50 text-sm">No devices connected</p>
                </div>
              ) : (
                pcs.map((pc) => (
                  <button
                    key={pc.pc_id}
                    onClick={() => setSelectedPC(pc.pc_id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedPC === pc.pc_id
                        ? 'bg-hack-green/20 border-hack-green text-hack-green'
                        : 'bg-black/50 border-white/10 text-white hover:border-hack-green/30'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Monitor size={16} />
                      <span className="font-mono text-sm">{pc.pc_id}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Controls Card */}
          {selectedPC && (
            <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-4 sm:p-6 shadow-xl">
              <h3 className="text-base sm:text-lg font-semibold text-white mb-4">Controls</h3>
              <div className="space-y-2">
                {!isStreaming ? (
                  <button
                    onClick={handleStartStream}
                    disabled={loading}
                    className="w-full bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-4 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Play size={18} />
                    Start Screen Share
                  </button>
                ) : (
                  <button
                    onClick={handleStopStream}
                    disabled={loading}
                    className="w-full bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Square size={18} />
                    Stop Stream
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Status Card */}
          {selectedPC && streamStatus && (
            <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-4 sm:p-6 shadow-xl">
              <h3 className="text-base sm:text-lg font-semibold text-white mb-4">Status</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-white/70 text-sm">Stream Type</span>
                  <span className="text-hack-green font-mono text-sm">
                    {streamStatus.stream_type || 'None'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-white/70 text-sm">Active</span>
                  <span className={isStreaming ? 'text-hack-green font-mono text-sm' : 'text-white/50 font-mono text-sm'}>
                    {isStreaming ? 'YES' : 'NO'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-white/70 text-sm">Connection</span>
                  <span className={`font-mono text-xs uppercase ${
                    connectionState === 'connected' ? 'text-hack-green' :
                    connectionState === 'connecting' ? 'text-hack-green' :
                    connectionState === 'error' ? 'text-red-400' :
                    'text-white/50'
                  }`}>
                    {connectionState}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Content - Video Display */}
        <div className="lg:col-span-8">
          <div className="bg-black backdrop-blur-sm border border-white/10 rounded-xl overflow-hidden shadow-xl">
            {!selectedPC ? (
              <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                <div className="text-center">
                  <MonitorSpeaker className="mx-auto text-white/30 mb-4" size={48} />
                  <p className="text-white font-medium">Select a PC to view screen</p>
                </div>
              </div>
            ) : !isStreaming ? (
              <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                <div className="text-center">
                  <MonitorSpeaker className="mx-auto text-white/30 mb-4" size={48} />
                  <p className="text-white font-medium">Screen share not active</p>
                  <p className="text-white/50 text-sm mt-2">Click "Start Screen Share" to begin</p>
                </div>
              </div>
            ) : connectionState === 'connecting' ? (
              <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-hack-green mx-auto mb-4"></div>
                  <p className="text-white font-medium">Establishing WebRTC connection...</p>
                </div>
              </div>
            ) : (
              <div className="relative w-full" style={{ aspectRatio: '16/9' }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-contain bg-black"
                  style={{ aspectRatio: '16/9' }}
                  onLoadedMetadata={() => {
                    console.log('[WebRTC] Video metadata loaded')
                    if (videoRef.current) {
                      videoRef.current.play().catch(console.error)
                    }
                  }}
                  onCanPlay={() => {
                    console.log('[WebRTC] Video can play')
                    if (videoRef.current) {
                      videoRef.current.play().catch(console.error)
                    }
                  }}
                  onPlay={() => {
                    console.log('[WebRTC] Video is playing')
                  }}
                  onError={(e) => {
                    console.error('[WebRTC] Video error:', e)
                  }}
                />
                {connectionState !== 'connected' && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-hack-green mx-auto mb-4"></div>
                      <p className="text-white font-medium">Connecting...</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Screen
