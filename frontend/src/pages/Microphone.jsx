import { useEffect, useState, useRef } from 'react'
import { Mic, Power, PowerOff, RefreshCw, Play, Download, Trash2 } from 'lucide-react'
import { getPCs, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'
import { useStreaming } from '../contexts/StreamingContext'

const MicrophonePage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [audioChunks, setAudioChunks] = useState([])
  const [playingChunkId, setPlayingChunkId] = useState(null)
  const audioContextRef = useRef(null)
  const currentSourceRef = useRef(null)
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
      if (currentSourceRef.current) {
        currentSourceRef.current.stop()
        currentSourceRef.current = null
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(e => {
          console.error('[Microphone] Error closing audio context:', e)
        })
      }
      unregisterStopCallback('microphone')
      setStreamActive('microphone', false)
    }
  }, [])

  const loadPCs = async () => {
    try {
      const data = await getPCs()
      setPCs((data.pcs || []).filter(pc => pc.connected))
    } catch (error) {
      console.error('Error loading PCs:', error)
      showToast('Failed to load PCs', 'error')
    }
  }

  const startStream = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'error')
      return
    }

    setIsConnecting(true)
    setAudioChunks([]) // Clear previous chunks

    try {
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

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === 'microphone_audio') {
          // Store audio chunk instead of auto-playing
          if (data.audio) {
            try {
              const chunkId = Date.now() + Math.random()
              // Use sequential numbering: next chunk number is current length + 1
              const chunkNumber = audioChunks.length + 1
              const duration = data.duration || 5.0
              const sampleRate = data.sample_rate || 44100
              const channels = data.channels || 1
              
              // Store chunk with metadata
              const chunk = {
                id: chunkId,
                chunkNumber: chunkNumber,
                audioData: data.audio, // Base64 encoded
                duration: duration,
                sampleRate: sampleRate,
                channels: channels,
                timestamp: new Date().toISOString(),
                size: Math.round((atob(data.audio).length / 1024) * 100) / 100 // Size in KB
              }
              
              setAudioChunks(prev => [...prev, chunk])
              showToast(`Received audio chunk ${chunkNumber}`, 'info')
            } catch (error) {
              console.error('[Microphone] Error processing audio chunk:', error)
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
        setStreamActive('microphone', false)
        unregisterStopCallback('microphone')
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
    if (currentSourceRef.current) {
      currentSourceRef.current.stop()
      currentSourceRef.current = null
    }
    setPlayingChunkId(null)
    setIsStreaming(false)
    setStreamActive('microphone', false)
    unregisterStopCallback('microphone')
    showToast('Microphone stream stopped', 'info')
  }

  const playChunk = async (chunk) => {
    try {
      // Stop current playback if any
      if (currentSourceRef.current) {
        currentSourceRef.current.stop()
        currentSourceRef.current = null
      }

      // Create audio context if needed
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      }

      const audioContext = audioContextRef.current
      
      // Resume audio context if suspended
      if (audioContext.state === 'suspended') {
        await audioContext.resume()
      }

      // Decode base64 audio to raw PCM bytes
      const binaryString = atob(chunk.audioData)
      const audioBytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        audioBytes[i] = binaryString.charCodeAt(i)
      }
      
      // Convert to Int16Array (16-bit PCM, little-endian)
      const audioData = new Int16Array(audioBytes.buffer)
      
      // Create audio buffer
      const sampleRate = chunk.sampleRate || 44100
      const numChannels = chunk.channels || 1
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
      source.connect(audioContext.destination)
      
      currentSourceRef.current = source
      setPlayingChunkId(chunk.id)
      
      source.start(0)
      
      source.onended = () => {
        setPlayingChunkId(null)
        currentSourceRef.current = null
      }
      
      showToast(`Playing chunk ${chunk.chunkNumber}`, 'info')
    } catch (error) {
      console.error('[Microphone] Error playing chunk:', error)
      showToast('Error playing audio chunk', 'error')
      setPlayingChunkId(null)
    }
  }

  const stopPlayback = () => {
    if (currentSourceRef.current) {
      currentSourceRef.current.stop()
      currentSourceRef.current = null
      setPlayingChunkId(null)
    }
  }

  const downloadChunk = (chunk) => {
    try {
      // Decode base64 to binary
      const binaryString = atob(chunk.audioData)
      const audioBytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        audioBytes[i] = binaryString.charCodeAt(i)
      }
      
      // Create WAV file from PCM data
      const sampleRate = chunk.sampleRate || 44100
      const numChannels = chunk.channels || 1
      const bitsPerSample = 16
      const byteRate = sampleRate * numChannels * bitsPerSample / 8
      const blockAlign = numChannels * bitsPerSample / 8
      const dataSize = audioBytes.length
      const fileSize = 36 + dataSize
      
      // Create WAV header
      const wavHeader = new ArrayBuffer(44)
      const view = new DataView(wavHeader)
      
      // RIFF header
      const writeString = (offset, string) => {
        for (let i = 0; i < string.length; i++) {
          view.setUint8(offset + i, string.charCodeAt(i))
        }
      }
      
      writeString(0, 'RIFF')
      view.setUint32(4, fileSize, true)
      writeString(8, 'WAVE')
      writeString(12, 'fmt ')
      view.setUint32(16, 16, true) // fmt chunk size
      view.setUint16(20, 1, true) // audio format (PCM)
      view.setUint16(22, numChannels, true)
      view.setUint32(24, sampleRate, true)
      view.setUint32(28, byteRate, true)
      view.setUint16(32, blockAlign, true)
      view.setUint16(34, bitsPerSample, true)
      writeString(36, 'data')
      view.setUint32(40, dataSize, true)
      
      // Combine header and audio data
      const wavFile = new Uint8Array(44 + dataSize)
      wavFile.set(new Uint8Array(wavHeader), 0)
      wavFile.set(audioBytes, 44)
      
      // Create blob and download
      const blob = new Blob([wavFile], { type: 'audio/wav' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audio_chunk_${chunk.chunkNumber}_${new Date(chunk.timestamp).toISOString().replace(/[:.]/g, '-')}.wav`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      showToast(`Downloaded chunk ${chunk.chunkNumber}`, 'success')
    } catch (error) {
      console.error('[Microphone] Error downloading chunk:', error)
      showToast('Error downloading audio chunk', 'error')
    }
  }

  const deleteChunk = (chunkId) => {
    setAudioChunks(prev => prev.filter(chunk => chunk.id !== chunkId))
    if (playingChunkId === chunkId) {
      stopPlayback()
    }
    showToast('Chunk deleted', 'info')
  }

  const clearAllChunks = () => {
    if (window.confirm('Delete all audio chunks?')) {
      setAudioChunks([])
      stopPlayback()
      showToast('All chunks cleared', 'info')
    }
  }

  const selectedPCData = pcs.find(pc => pc.pc_id === selectedPC)

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString()
  }

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

      {/* Audio Chunks List */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Mic className="text-hack-green" size={20} />
            <h3 className="text-lg font-mono text-hack-green">Audio Chunks ({audioChunks.length})</h3>
          </div>
          {audioChunks.length > 0 && (
            <button
              onClick={clearAllChunks}
              className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 border border-red-500 text-red-400 rounded-lg transition-all font-mono text-sm"
            >
              <Trash2 size={16} />
              Clear All
            </button>
          )}
        </div>

        {audioChunks.length === 0 ? (
          <div className="text-center py-12 text-gray-500 font-mono">
            {isStreaming ? 'Waiting for audio chunks...' : 'No audio chunks received. Start streaming to capture audio.'}
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {audioChunks.map((chunk) => (
              <div
                key={chunk.id}
                className={`p-4 bg-hack-darker rounded-lg border ${
                  playingChunkId === chunk.id
                    ? 'border-hack-green'
                    : 'border-hack-green/20'
                } transition-all`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-hack-green font-mono font-bold">
                        Chunk {chunk.chunkNumber}
                      </span>
                      <span className="text-gray-400 font-mono text-sm">
                        {formatTime(chunk.timestamp)}
                      </span>
                      {playingChunkId === chunk.id && (
                        <span className="text-hack-green font-mono text-xs animate-pulse">
                          ▶ Playing
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono text-gray-400">
                      <span>{chunk.duration}s</span>
                      <span>{chunk.sampleRate}Hz</span>
                      <span>{chunk.channels === 1 ? 'Mono' : 'Stereo'}</span>
                      <span>{chunk.size} KB</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {playingChunkId === chunk.id ? (
                      <button
                        onClick={stopPlayback}
                        className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 border border-red-500 text-red-400 rounded-lg transition-all font-mono text-sm"
                      >
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => playChunk(chunk)}
                        disabled={playingChunkId !== null}
                        className="px-3 py-1.5 bg-hack-green/20 hover:bg-hack-green/30 border border-hack-green text-hack-green rounded-lg transition-all font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                      >
                        <Play size={14} />
                        Play
                      </button>
                    )}
                    <button
                      onClick={() => downloadChunk(chunk)}
                      className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500 text-blue-400 rounded-lg transition-all font-mono text-sm flex items-center gap-2"
                    >
                      <Download size={14} />
                      Download
                    </button>
                    <button
                      onClick={() => deleteChunk(chunk.id)}
                      className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 border border-red-500 text-red-400 rounded-lg transition-all font-mono text-sm"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default MicrophonePage
