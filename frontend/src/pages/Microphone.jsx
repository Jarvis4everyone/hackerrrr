import { useEffect, useState, useRef } from 'react'
import { Mic, Power, PowerOff, RefreshCw, Volume2 } from 'lucide-react'
import { getPCs, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'
import { useStreaming } from '../contexts/StreamingContext'

const MicrophonePage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const audioRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const gainNodeRef = useRef(null)
  const audioQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const wsRef = useRef(null)
  const { showToast } = useToast()
  const { setStreamActive, registerStopCallback, unregisterStopCallback } = useStreaming()

  useEffect(() => {
    loadPCs()
    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        stopStream()
      }
      unregisterStopCallback('microphone')
      setStreamActive('microphone', false)
    }
  }, [])

  const loadPCs = async () => {
    try {
      const data = await getPCs()
      setPCs(data.filter(pc => pc.connected))
    } catch (error) {
      showToast('Failed to load PCs', 'error')
    }
  }

  const startStream = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'error')
      return
    }

    setIsConnecting(true)

    try {
      // Create audio context for playback
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      
      // Resume audio context if suspended (required by some browsers)
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }
      
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      
      const gainNode = audioContext.createGain()
      gainNode.gain.value = 1.0
      
      audioContextRef.current = audioContext
      analyserRef.current = analyser
      gainNodeRef.current = gainNode
      audioQueueRef.current = []
      isPlayingRef.current = false

      // Get WebSocket URL
      const wsUrl = getWebSocketUrl(`/ws/stream/${selectedPC}/microphone`)
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Microphone] WebSocket connected')
        setIsConnecting(false)
        setIsStreaming(true)
        
        // Request to start stream
        ws.send(JSON.stringify({
          type: 'start_stream'
        }))
        
        showToast('Microphone stream started', 'success')
        
        // Register with streaming context
        setStreamActive('microphone', true)
        registerStopCallback('microphone', stopStream)
      }

      // Audio playback function
      const playAudioChunk = async (audioData) => {
        try {
          const audioContext = audioContextRef.current
          const analyser = analyserRef.current
          const gainNode = gainNodeRef.current
          
          if (!audioContext || !analyser || !gainNode) return
          
          // Create audio buffer from raw PCM data
          // Assuming: 44100 Hz, mono, 16-bit PCM
          const sampleRate = 44100
          const numChannels = 1
          const length = audioData.length
          
          const audioBuffer = audioContext.createBuffer(numChannels, length, sampleRate)
          const channelData = audioBuffer.getChannelData(0)
          
          // Convert Int16 to Float32 (-1.0 to 1.0)
          for (let i = 0; i < length; i++) {
            channelData[i] = Math.max(-1, Math.min(1, audioData[i] / 32768.0))
          }
          
          // Play audio
          const source = audioContext.createBufferSource()
          source.buffer = audioBuffer
          source.connect(gainNode)
          gainNode.connect(analyser)
          analyser.connect(audioContext.destination)
          
          const currentTime = audioContext.currentTime
          source.start(currentTime)
          
          // Update audio level visualization
          const dataArray = new Uint8Array(analyser.frequencyBinCount)
          analyser.getByteFrequencyData(dataArray)
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length
          setAudioLevel(average)
          
          // Clean up source after playback
          source.onended = () => {
            source.disconnect()
          }
        } catch (error) {
          console.error('[Microphone] Error playing audio chunk:', error)
        }
      }

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'microphone_audio') {
          // Decode and play audio
          if (data.audio) {
            try {
              // Decode base64 audio to raw PCM bytes
              const binaryString = atob(data.audio)
              const audioBytes = new Uint8Array(binaryString.length)
              for (let i = 0; i < binaryString.length; i++) {
                audioBytes[i] = binaryString.charCodeAt(i)
              }
              
              // Convert to Int16Array (16-bit PCM, little-endian)
              const audioData = new Int16Array(audioBytes.buffer)
              
              // Play audio chunk
              await playAudioChunk(audioData)
            } catch (error) {
              console.error('[Microphone] Error processing audio:', error)
            }
          }
        } else if (data.type === 'stream_status') {
          console.log('[Microphone] Stream status:', data)
          if (data.pc_streaming === false && isStreaming) {
            showToast('PC stopped streaming', 'info')
            setIsStreaming(false)
          }
        } else if (data.type === 'error') {
          showToast(`Stream error: ${data.message}`, 'error')
        }
      }

      ws.onerror = (error) => {
        console.error('[Microphone] WebSocket error:', error)
        showToast('Connection error', 'error')
        setIsConnecting(false)
        setIsStreaming(false)
      }

      ws.onclose = () => {
        console.log('[Microphone] WebSocket closed')
        setIsStreaming(false)
        setAudioLevel(0)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[Microphone] Error starting stream:', error)
      showToast('Failed to start stream', 'error')
      setIsConnecting(false)
    }
  }

  const stopStream = () => {
    if (wsRef.current) {
      // Request to stop stream
      try {
        wsRef.current.send(JSON.stringify({
          type: 'stop_stream'
        }))
      } catch (e) {
        console.error('[Microphone] Error sending stop:', e)
      }
      wsRef.current.close()
      wsRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(e => {
        console.error('[Microphone] Error closing audio context:', e)
      })
      audioContextRef.current = null
    }
    analyserRef.current = null
    gainNodeRef.current = null
    audioQueueRef.current = []
    isPlayingRef.current = false
    setIsStreaming(false)
    setAudioLevel(0)
    setStreamActive('microphone', false)
    unregisterStopCallback('microphone')
    showToast('Microphone stream stopped', 'info')
  }

  const selectedPCData = pcs.find(pc => pc.pc_id === selectedPC)

  return (
    <div className="space-y-6">
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Mic className="text-hack-green" size={24} />
          <h2 className="text-xl font-mono text-hack-green">Microphone Stream</h2>
        </div>

        {/* PC Selection */}
        <div className="mb-6">
          <label className="block text-sm font-mono text-gray-400 mb-2">
            Select PC
          </label>
          <select
            value={selectedPC}
            onChange={(e) => {
              setSelectedPC(e.target.value)
              if (isStreaming) {
                stopStream()
              }
            }}
            disabled={isStreaming || isConnecting}
            className="w-full px-4 py-2 bg-hack-darker border border-hack-green/30 rounded-lg text-white font-mono focus:outline-none focus:border-hack-green disabled:opacity-50"
          >
            <option value="">-- Select a PC --</option>
            {pcs.map((pc) => (
              <option key={pc.pc_id} value={pc.pc_id}>
                {pc.name || pc.pc_id} {pc.connected ? '🟢' : '🔴'}
              </option>
            ))}
          </select>
        </div>

        {/* Controls */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={startStream}
            disabled={!selectedPC || isStreaming || isConnecting}
            className="flex items-center gap-2 px-4 py-2 bg-hack-green/20 hover:bg-hack-green/30 border border-hack-green text-hack-green rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isConnecting ? (
              <>
                <RefreshCw className="animate-spin" size={18} />
                Connecting...
              </>
            ) : (
              <>
                <Power size={18} />
                Start Stream
              </>
            )}
          </button>

          <button
            onClick={stopStream}
            disabled={!isStreaming}
            className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500 text-red-400 rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PowerOff size={18} />
            Stop Stream
          </button>

          <button
            onClick={loadPCs}
            className="flex items-center gap-2 px-4 py-2 bg-hack-gray hover:bg-hack-gray/80 border border-hack-green/30 text-white rounded-lg transition-all font-mono"
          >
            <RefreshCw size={18} />
            Refresh
          </button>
        </div>

        {/* Status */}
        {selectedPCData && (
          <div className="mb-4 p-4 bg-hack-darker rounded-lg border border-hack-green/20">
            <div className="grid grid-cols-2 gap-4 text-sm font-mono">
              <div>
                <span className="text-gray-400">PC ID:</span>
                <span className="text-white ml-2">{selectedPCData.pc_id}</span>
              </div>
              <div>
                <span className="text-gray-400">Status:</span>
                <span className={`ml-2 ${isStreaming ? 'text-hack-green' : 'text-gray-400'}`}>
                  {isStreaming ? 'Streaming' : 'Stopped'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Audio Visualization */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <Volume2 className="text-hack-green" size={20} />
          <h3 className="text-lg font-mono text-hack-green">Audio Level</h3>
        </div>
        <div className="bg-black rounded-lg p-6">
          {isStreaming ? (
            <div className="space-y-4">
              <div className="h-8 bg-hack-darker rounded-lg overflow-hidden relative">
                <div
                  className="h-full bg-gradient-to-r from-hack-green to-green-400 transition-all duration-100"
                  style={{ width: `${Math.min(100, (audioLevel / 255) * 100)}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-mono text-white">
                    {Math.round((audioLevel / 255) * 100)}%
                  </span>
                </div>
              </div>
              <div className="text-center text-gray-400 font-mono text-sm">
                Listening to microphone audio...
              </div>
            </div>
          ) : (
            <div className="text-center text-gray-500 font-mono">
              {selectedPC ? 'Click "Start Stream" to listen to microphone' : 'Select a PC to start streaming'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default MicrophonePage

