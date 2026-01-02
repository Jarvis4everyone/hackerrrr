import { useEffect, useState, useRef } from 'react'
import { MonitorSpeaker, Play, Square, Monitor } from 'lucide-react'
import { getPCs, startScreenStream, stopStream, getStreamStatus } from '../services/api'
import AgoraRTC from 'agora-rtc-sdk-ng'

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

const Screen = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [connectionState, setConnectionState] = useState('disconnected')
  const videoRef = useRef(null)
  const clientRef = useRef(null)
  const remoteTrackRef = useRef(null)

  useEffect(() => {
    loadPCs()
    const interval = setInterval(loadPCs, 3000)
    return () => {
      clearInterval(interval)
      cleanupAgora()
    }
  }, [])

  useEffect(() => {
    if (selectedPC) {
      checkStreamStatus()
      const interval = setInterval(checkStreamStatus, 2000)
      return () => clearInterval(interval)
    } else {
      cleanupAgora()
    }
  }, [selectedPC])

  useEffect(() => {
    if (streamStatus?.has_active_stream && streamStatus?.stream_type === 'screen' && selectedPC) {
      if (connectionState === 'disconnected') {
        console.log('[Agora] Stream detected as active, connecting...')
        connectToStream(selectedPC)
      }
    } else if (!streamStatus?.has_active_stream) {
      cleanupAgora()
    }
  }, [streamStatus, selectedPC, connectionState])

  const cleanupAgora = async () => {
    try {
      if (remoteTrackRef.current) {
        try {
          remoteTrackRef.current.stop()
        } catch (e) {
          // Track may already be stopped
        }
        remoteTrackRef.current = null
      }
      if (clientRef.current) {
        try {
          await clientRef.current.leave()
          await clientRef.current.release()
        } catch (e) {
          // Client may already be released
        }
        clientRef.current = null
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null
      }
      setConnectionState('disconnected')
    } catch (error) {
      console.error('[Agora] Error during cleanup:', error)
    }
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
    } catch (error) {
      console.error('Error checking stream status:', error)
    }
  }

  const connectToStream = async (pcId) => {
    if (clientRef.current) {
      console.log('[Agora] Already connected, skipping...')
      return
    }

    try {
      setConnectionState('connecting')

      // Get subscriber token from backend
      const response = await fetch(`${API_BASE_URL}/api/streaming/${pcId}/token?stream_type=screen&uid=0`)
      if (!response.ok) {
        throw new Error('Failed to get Agora token')
      }
      const data = await response.json()
      const { channel_name, token, uid, app_id } = data.agora

      console.log('[Agora] Connecting to channel:', channel_name)

      // Create Agora client
      const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' })
      clientRef.current = client

      // Set up event handlers
      client.on('user-published', async (user, mediaType) => {
        console.log('[Agora] User published:', user.uid, mediaType)
        try {
          if (mediaType === 'video') {
            await client.subscribe(user, mediaType)
            const remoteVideoTrack = user.videoTrack
            if (remoteVideoTrack && videoRef.current) {
              remoteTrackRef.current = remoteVideoTrack
              remoteVideoTrack.play(videoRef.current)
              setConnectionState('connected')
              console.log('[Agora] ✅ Screen track subscribed and playing')
            }
          }
        } catch (error) {
          console.error('[Agora] Error handling user-published:', error)
          setConnectionState('error')
        }
      })

      client.on('user-unpublished', async (user, mediaType) => {
        console.log('[Agora] User unpublished:', user.uid, mediaType)
        try {
          if (mediaType === 'video') {
            const remoteVideoTrack = user.videoTrack
            if (remoteVideoTrack) {
              remoteVideoTrack.stop()
            }
            if (videoRef.current) {
              videoRef.current.srcObject = null
            }
            setConnectionState('disconnected')
          }
        } catch (error) {
          console.error('[Agora] Error handling user-unpublished:', error)
        }
      })

      client.on('connection-state-change', (curState, revState) => {
        console.log('[Agora] Connection state changed:', curState, revState)
        if (curState === 'CONNECTED') {
          setConnectionState('connected')
        } else if (curState === 'DISCONNECTED') {
          setConnectionState('disconnected')
        }
      })

      // Join channel
      await client.join(app_id, channel_name, token, uid)
      console.log('[Agora] ✅ Joined channel successfully')

    } catch (error) {
      console.error('[Agora] Error connecting to stream:', error)
      setConnectionState('error')
      await cleanupAgora()
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
      setTimeout(async () => {
        await checkStreamStatus()
      }, 1000)
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
      await cleanupAgora()
      await checkStreamStatus()
    } catch (error) {
      alert('Error stopping stream: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 text-green-500">
          <MonitorSpeaker className="w-8 h-8" />
          Screen Sharing
        </h1>
        <p className="text-green-400 mt-2">View PC screen in real-time using Agora</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* PC Selection */}
        <div className="lg:col-span-1">
          <div className="bg-black border border-green-500 rounded-lg shadow p-4">
            <h2 className="text-xl font-semibold mb-4 text-green-500">Select PC</h2>
            <div className="space-y-2">
              {pcs.length === 0 ? (
                <p className="text-green-400">No connected PCs</p>
              ) : (
                pcs.map((pc) => (
                  <button
                    key={pc.pc_id}
                    onClick={() => setSelectedPC(pc.pc_id)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      selectedPC === pc.pc_id
                        ? 'bg-green-500 text-black'
                        : 'bg-gray-900 border border-green-500/30 hover:border-green-500 text-green-400'
                    }`}
                  >
                    <div className="font-semibold">{pc.pc_id}</div>
                    <div className="text-sm opacity-75">{pc.hostname || 'Unknown'}</div>
                  </button>
                ))
              )}
            </div>

            {selectedPC && (
              <div className="mt-4 space-y-2">
                <button
                  onClick={handleStartStream}
                  disabled={loading || streamStatus?.has_active_stream}
                  className="w-full bg-green-500 text-black px-4 py-2 rounded-lg hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold"
                >
                  <Play className="w-4 h-4" />
                  {loading ? 'Starting...' : 'Start Screen Share'}
                </button>
                <button
                  onClick={handleStopStream}
                  disabled={loading || !streamStatus?.has_active_stream}
                  className="w-full bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold"
                >
                  <Square className="w-4 h-4" />
                  Stop Stream
                </button>
              </div>
            )}

            {streamStatus && (
              <div className="mt-4 p-3 bg-gray-900 border border-green-500/30 rounded-lg">
                <div className="text-sm">
                  <div className="flex justify-between">
                    <span className="font-semibold text-green-400">Status:</span>
                    <span className={streamStatus.has_active_stream ? 'text-green-500' : 'text-green-400'}>
                      {streamStatus.has_active_stream ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  {streamStatus.has_active_stream && (
                    <div className="flex justify-between mt-1">
                      <span className="font-semibold text-green-400">Type:</span>
                      <span className="text-green-400 capitalize">{streamStatus.stream_type}</span>
                    </div>
                  )}
                  <div className="flex justify-between mt-1">
                    <span className="font-semibold text-green-400">Connection:</span>
                    <span className={connectionState === 'connected' ? 'text-green-500' : 'text-green-400'}>
                      {connectionState}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Video Display */}
        <div className="lg:col-span-2">
          <div className="bg-black rounded-lg shadow overflow-hidden aspect-video">
            {connectionState === 'connected' ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white">
                {connectionState === 'connecting' ? (
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
                    <p>Connecting to stream...</p>
                  </div>
                ) : connectionState === 'error' ? (
                  <div className="text-center">
                    <p className="text-red-400">Connection error</p>
                    <p className="text-sm mt-2">Please try again</p>
                  </div>
                ) : (
                  <div className="text-center">
                    <Monitor className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p>No stream active</p>
                    <p className="text-sm mt-2">Select a PC and start the screen share</p>
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
