import { useEffect, useState, useRef } from 'react'
import { Camera as CameraIcon, Play, Square, Monitor } from 'lucide-react'
import { getPCs, startCameraStream, stopStream, getStreamStatus } from '../services/api'
import { createPeerConnection } from '../utils/webrtc'

// Get API URL from environment or construct from current location
let API_BASE_URL = import.meta.env.VITE_API_URL
if (!API_BASE_URL && import.meta.env.PROD) {
  // In production, construct backend URL (assuming backend is on same domain or known pattern)
  // For Render: backend might be hackerrrr-backend.onrender.com
  const hostname = window.location.hostname
  if (hostname.includes('onrender.com')) {
    // Extract subdomain and construct backend URL
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

// Construct WebSocket URL
const WS_BASE_URL = API_BASE_URL 
  ? API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://')
  : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

const Camera = () => {
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
    if (streamStatus?.has_active_stream && streamStatus?.stream_type === 'camera' && selectedPC) {
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
      
      if (status.has_active_stream && status.stream_type === 'camera') {
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
      
      const wsUrl = `${WS_BASE_URL}/ws/frontend/${pcId}/camera`
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
        console.log('[WebRTC] WebSocket closed', event.code, event.reason || 'No reason')
        connectingRef.current = false
        setConnectionState('disconnected')
        
        // Don't auto-reconnect if it's a normal closure or if we're already connected
        if (event.code === 1000 || peerConnectionRef.current?.connectionState === 'connected') {
          console.log('[WebRTC] Normal closure or already connected, not reconnecting')
          return
        }
        
        // Only reconnect if connection failed
        if (event.code !== 1000 && event.code !== 1001) {
          console.log('[WebRTC] Unexpected closure, will reconnect if needed')
        }
      }

      pc.ontrack = (event) => {
        console.log('[WebRTC] ===== TRACK RECEIVED =====')
        console.log('[WebRTC] Track kind:', event.track.kind)
        console.log('[WebRTC] Track enabled:', event.track.enabled)
        console.log('[WebRTC] Track muted:', event.track.muted)
        console.log('[WebRTC] Track readyState:', event.track.readyState)
        console.log('[WebRTC] Streams:', event.streams.length)
        
        if (event.track.kind === 'video') {
          console.log('[WebRTC] Video track received!')
          
          if (!videoRef.current) {
            console.error('[WebRTC] videoRef.current is null!')
            return
          }
          
          // Get stream from event or create new one
          let stream = event.streams[0]
          if (!stream || stream.getVideoTracks().length === 0) {
            console.log('[WebRTC] Creating new MediaStream from track')
            stream = new MediaStream([event.track])
          }
          
          // Ensure track is enabled and unmuted
          if (!event.track.enabled) {
            console.log('[WebRTC] Enabling video track')
            event.track.enabled = true
          }
          
          // Note: Track muted state is read-only in browsers, but we can work around it
          // The muted state might be due to the relay or initial connection state
          if (event.track.muted) {
            console.log('[WebRTC] Track is muted (this is often normal during connection establishment)')
            console.log('[WebRTC] Track will unmute automatically when media starts flowing')
          }
          
          console.log('[WebRTC] Setting video srcObject')
          console.log('[WebRTC] Stream video tracks:', stream.getVideoTracks().length)
          console.log('[WebRTC] Track enabled:', event.track.enabled, 'muted:', event.track.muted, 'readyState:', event.track.readyState)
          
          // Clear any existing stream first
          if (videoRef.current.srcObject) {
            const oldStream = videoRef.current.srcObject
            oldStream.getTracks().forEach(track => track.stop())
          }
          
          // Ensure all tracks in the stream are enabled
          stream.getVideoTracks().forEach(track => {
            track.enabled = true
            // Note: muted property is read-only, but track will unmute when media flows
            console.log('[WebRTC] Track configured - enabled:', track.enabled, 'muted:', track.muted, 'readyState:', track.readyState)
            
            // Monitor track state changes
            track.onmute = () => {
              console.warn('[WebRTC] Track was muted')
            }
            track.onunmute = () => {
              console.log('[WebRTC] ✅ Track was unmuted!')
              if (videoRef.current && videoRef.current.paused) {
                videoRef.current.play().catch(console.error)
              }
            }
          })
          
          videoRef.current.srcObject = stream
          setConnectionState('connected')
          
          // Force play with multiple attempts
          const attemptPlay = (attempts = 0) => {
            if (!videoRef.current) return
            
            if (attempts < 5) {
              videoRef.current.play()
                .then(() => {
                  console.log('[WebRTC] ✅ Video is playing successfully!')
                  console.log('[WebRTC] Video dimensions:', videoRef.current.videoWidth, 'x', videoRef.current.videoHeight)
                  console.log('[WebRTC] Video readyState:', videoRef.current.readyState)
                })
                .catch((error) => {
                  console.error('[WebRTC] ❌ Error playing video (attempt ' + (attempts + 1) + '):', error)
                  if (attempts < 4) {
                    setTimeout(() => attemptPlay(attempts + 1), 200)
                  }
                })
            }
          }
          
          // Try playing immediately and then retry
          setTimeout(() => attemptPlay(0), 100)
          setTimeout(() => attemptPlay(1), 500)
          setTimeout(() => attemptPlay(2), 1000)
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
          console.log('[WebRTC] ✅ Connection established!')
          // When connected, ensure video is playing
          if (videoRef.current && videoRef.current.srcObject) {
            const tracks = videoRef.current.srcObject.getVideoTracks()
            console.log('[WebRTC] Active video tracks on connection:', tracks.length)
            tracks.forEach(track => {
              console.log('[WebRTC] Track state:', track.readyState, 'enabled:', track.enabled)
            })
            // Force play attempt when connection is established
            setTimeout(() => {
              if (videoRef.current) {
                videoRef.current.play().catch(console.error)
              }
            }, 100)
          }
        } else if (pc.connectionState === 'connecting') {
          console.log('[WebRTC] Connecting...')
        } else if (pc.connectionState === 'disconnected') {
          console.warn('[WebRTC] Disconnected')
        } else if (pc.connectionState === 'failed') {
          console.error('[WebRTC] ❌ Connection failed!')
          cleanupWebRTC()
        } else if (pc.connectionState === 'closed') {
          console.log('[WebRTC] Connection closed')
          cleanupWebRTC()
        }
      }
      
      // Also monitor ICE connection state
      pc.oniceconnectionstatechange = () => {
        console.log('[WebRTC] ICE connection state:', pc.iceConnectionState)
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          console.log('[WebRTC] ✅ ICE connection established!')
          // Force video play when ICE connects
          if (videoRef.current && videoRef.current.srcObject) {
            setTimeout(() => {
              if (videoRef.current) {
                videoRef.current.play().catch(console.error)
              }
            }, 100)
          }
        } else if (pc.iceConnectionState === 'failed') {
          console.error('[WebRTC] ❌ ICE connection failed!')
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
      await startCameraStream(selectedPC)
      setTimeout(async () => {
        await checkStreamStatus()
        setTimeout(() => {
          if (!connectingRef.current && !wsRef.current) {
            console.log('[WebRTC] Starting frontend connection after stream start...')
            connectToStream(selectedPC)
          }
        }, 2000)
      }, 1000)
    } catch (error) {
      alert('Error starting camera stream: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleStopStream = async () => {
    if (!selectedPC) return
    setLoading(true)
    try {
      cleanupWebRTC()
      await stopStream(selectedPC)
      await checkStreamStatus()
    } catch (error) {
      alert('Error stopping stream: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const isStreaming = streamStatus?.has_active_stream && streamStatus?.stream_type === 'camera'

  const getConnectionStatusColor = (state) => {
    switch (state) {
      case 'connected':
        return 'text-green-400'
      case 'connecting':
        return 'text-yellow-400'
      case 'disconnected':
        return 'text-white/50'
      case 'failed':
      case 'closed':
      case 'error':
        return 'text-red-400'
      default:
        return 'text-white/70'
    }
  }

  return (
    <div className="min-h-screen bg-black p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-hack-green/10 rounded-lg border border-hack-green/20">
                <CameraIcon className="text-hack-green" size={28} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Camera Stream</h1>
                <p className="text-white/70 text-sm mt-1">Monitor camera feed from connected devices</p>
              </div>
            </div>
            {isStreaming && (
              <div className="flex items-center gap-2 px-4 py-2 bg-green-500/10 border border-green-500/30 rounded-lg">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-400 font-medium text-sm">LIVE</span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Sidebar - PC Selection & Controls */}
          <div className="lg:col-span-4 space-y-6">
            {/* PC Selection Card */}
            <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-xl">
              <div className="flex items-center gap-3 mb-6">
                <Monitor className="text-hack-green" size={20} />
                <h2 className="text-lg font-semibold text-white">Connected Devices</h2>
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
                      onClick={() => {
                        setSelectedPC(pc.pc_id)
                        cleanupWebRTC()
                      }}
                      className={`w-full text-left p-4 rounded-lg border transition-all duration-200 ${
                        selectedPC === pc.pc_id
                          ? 'bg-hack-green/10 border-hack-green/50 text-hack-green shadow-lg shadow-hack-green/20'
                          : 'bg-black/50 border-white/10 text-white hover:border-hack-green/30 hover:bg-black/70'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded ${selectedPC === pc.pc_id ? 'bg-hack-green/20' : 'bg-black/50'}`}>
                          <Monitor size={16} className={selectedPC === pc.pc_id ? 'text-hack-green' : 'text-white/70'} />
                        </div>
                        <span className="font-medium">{pc.pc_id}</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Controls Card */}
            {selectedPC && (
              <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-xl">
                <h2 className="text-lg font-semibold text-white mb-6">Stream Controls</h2>
                <div className="space-y-3">
                  {!isStreaming ? (
                    <button
                      onClick={handleStartStream}
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-hack-green/20 to-green-600/20 hover:from-hack-green/30 hover:to-green-600/30 border border-hack-green/50 text-hack-green px-6 py-4 rounded-lg font-medium transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-hack-green/20"
                    >
                      <Play size={20} />
                      <span>Start Camera</span>
                    </button>
                  ) : (
                    <button
                      onClick={handleStopStream}
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-red-500/20 to-red-600/20 hover:from-red-500/30 hover:to-red-600/30 border border-red-500/50 text-red-400 px-6 py-4 rounded-lg font-medium transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20"
                    >
                      <Square size={20} />
                      <span>Stop Stream</span>
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Status Card */}
            {selectedPC && streamStatus && (
              <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-xl">
                <h2 className="text-lg font-semibold text-white mb-6">Stream Status</h2>
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-2 border-b border-white/10">
                    <span className="text-white/70 text-sm">Stream Type</span>
                    <span className="text-white font-medium">
                      {streamStatus.stream_type ? streamStatus.stream_type.charAt(0).toUpperCase() + streamStatus.stream_type.slice(1) : 'None'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-white/10">
                    <span className="text-white/70 text-sm">Status</span>
                    <span className={`font-medium ${isStreaming ? 'text-hack-green' : 'text-white/50'}`}>
                      {isStreaming ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-white/70 text-sm">Connection</span>
                    <span className={`font-medium ${getConnectionStatusColor(connectionState)}`}>
                      {connectionState.charAt(0).toUpperCase() + connectionState.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Side - Video Display */}
          <div className="lg:col-span-8">
            <div className="bg-black backdrop-blur-sm border border-white/10 rounded-xl overflow-hidden shadow-xl">
              {!selectedPC ? (
                <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                  <div className="text-center">
                    <CameraIcon className="mx-auto text-white/30 mb-4" size={48} />
                    <p className="text-white font-medium">Select a PC to view camera</p>
                  </div>
                </div>
              ) : !isStreaming ? (
                <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                  <div className="text-center">
                    <CameraIcon className="mx-auto text-white/30 mb-4" size={48} />
                    <p className="text-white font-medium">Camera stream not active</p>
                    <p className="text-white/50 text-sm mt-2">Click "Start Camera" to begin</p>
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
                    muted={false}
                    className="w-full h-full object-contain bg-black"
                    style={{ aspectRatio: '16/9' }}
                    onLoadedMetadata={() => {
                      console.log('[WebRTC] Video metadata loaded')
                      console.log('[WebRTC] Video dimensions:', videoRef.current?.videoWidth, 'x', videoRef.current?.videoHeight)
                      console.log('[WebRTC] Video muted:', videoRef.current?.muted)
                      if (videoRef.current) {
                        // Ensure video is not muted
                        videoRef.current.muted = false
                        videoRef.current.play().catch(error => {
                          console.error('[WebRTC] Error playing on metadata:', error)
                        })
                      }
                    }}
                    onLoadedData={() => {
                      console.log('[WebRTC] Video data loaded')
                      if (videoRef.current) {
                        videoRef.current.play().catch(console.error)
                      }
                    }}
                    onCanPlay={() => {
                      console.log('[WebRTC] Video can play')
                      console.log('[WebRTC] Video dimensions:', videoRef.current?.videoWidth, 'x', videoRef.current?.videoHeight)
                      if (videoRef.current) {
                        videoRef.current.muted = false
                        videoRef.current.play().catch(console.error)
                      }
                    }}
                    onPlay={() => {
                      console.log('[WebRTC] ✅ Video is playing!')
                      console.log('[WebRTC] Video dimensions:', videoRef.current?.videoWidth, 'x', videoRef.current?.videoHeight)
                      console.log('[WebRTC] Video muted:', videoRef.current?.muted)
                      // Check track states
                      if (videoRef.current?.srcObject) {
                        const tracks = videoRef.current.srcObject.getVideoTracks()
                        tracks.forEach(track => {
                          console.log('[WebRTC] Track on play - enabled:', track.enabled, 'muted:', track.muted, 'readyState:', track.readyState)
                        })
                      }
                    }}
                    onPlaying={() => {
                      console.log('[WebRTC] Video playing event fired')
                    }}
                    onWaiting={() => {
                      console.log('[WebRTC] Video waiting for data')
                    }}
                    onStalled={() => {
                      console.warn('[WebRTC] Video stalled')
                    }}
                    onError={(e) => {
                      console.error('[WebRTC] Video error:', e)
                      console.error('[WebRTC] Video error code:', videoRef.current?.error?.code)
                      console.error('[WebRTC] Video error message:', videoRef.current?.error?.message)
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
                  {videoRef.current && videoRef.current.videoWidth === 0 && connectionState === 'connected' && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                      <div className="text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-hack-green mx-auto mb-4"></div>
                        <p className="text-white font-medium">Waiting for video data...</p>
                        <p className="text-white/50 text-sm mt-2">ICE connection may still be establishing</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Camera
