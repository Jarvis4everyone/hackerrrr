import { useEffect, useState, useRef } from 'react'
import { Mic, Power, PowerOff, RefreshCw, Play, Download, Trash2, Loader2, Radio, Waveform, Clock, HardDrive } from 'lucide-react'
import { getPCs, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'
import { useStreaming } from '../contexts/StreamingContext'

const MicrophonePage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [audioChunks, setAudioChunks] = useState([])
  const [playingChunkId, setPlayingChunkId] = useState(null)
  const [chunkCounter, setChunkCounter] = useState(0) // Use a counter ref to ensure sequential numbering
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
    setIsLoading(true)
    try {
      const data = await getPCs()
      setPCs((data.pcs || []).filter(pc => pc.connected))
    } catch (error) {
      console.error('Error loading PCs:', error)
      showToast('Failed to load PCs', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const startStream = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'error')
      return
    }

    setIsConnecting(true)
    setAudioChunks([]) // Clear previous chunks
    setChunkCounter(0) // Reset counter

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
              const duration = data.duration || 5.0
              const sampleRate = data.sample_rate || 44100
              const channels = data.channels || 1
              
              // Use counter state to ensure sequential numbering - increment first
              setChunkCounter(prev => {
                const newChunkNumber = prev + 1
                
                // Create chunk with the new number
                const chunk = {
                  id: chunkId,
                  chunkNumber: newChunkNumber,
                  audioData: data.audio, // Base64 encoded
                  duration: duration,
                  sampleRate: sampleRate,
                  channels: channels,
                  timestamp: new Date().toISOString(),
                  size: Math.round((atob(data.audio).length / 1024) * 100) / 100 // Size in KB
                }
                
                // Add chunk to list
                setAudioChunks(prevChunks => [...prevChunks, chunk])
                showToast(`Received audio chunk ${newChunkNumber}`, 'info')
                
                return newChunkNumber
              })
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
      setChunkCounter(0)
      stopPlayback()
      showToast('All chunks cleared', 'info')
    }
  }

  const selectedPCData = pcs.find(pc => pc.pc_id === selectedPC)

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <div className="text-center">
          <div className="relative">
            <Loader2 className="animate-spin text-hack-green mx-auto mb-4" size={56} />
            <div className="absolute inset-0 flex items-center justify-center">
              <Mic className="text-hack-green/50" size={28} />
            </div>
          </div>
          <p className="text-gray-400 font-mono text-lg">Loading PCs...</p>
          <p className="text-gray-600 font-mono text-sm mt-2">Please wait while we fetch connected devices</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Enhanced Header Section */}
      <div className="bg-gradient-to-br from-hack-dark via-hack-dark to-hack-darker border border-hack-green/30 rounded-xl p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-gradient-to-br from-hack-green/20 to-hack-green/10 rounded-xl border border-hack-green/30 shadow-lg">
              <Mic className="text-hack-green" size={32} />
            </div>
            <div>
              <h2 className="text-3xl font-mono text-hack-green font-bold tracking-tight">Microphone Stream</h2>
              <p className="text-sm text-gray-400 font-mono mt-1.5">Capture and monitor real-time audio from connected PCs</p>
            </div>
          </div>
          {isStreaming && (
            <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-500/50 rounded-lg">
              <div className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse"></div>
              <span className="text-red-400 font-mono text-sm font-semibold">LIVE</span>
            </div>
          )}
        </div>

        {/* PC Selection */}
        <div className="mb-6">
          <label className="block text-sm font-mono text-gray-300 mb-3 flex items-center gap-2">
            <Radio size={18} className="text-hack-green" />
            <span>Select Target PC</span>
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
            className="w-full px-4 py-3 bg-hack-darker/80 border-2 border-hack-green/30 rounded-lg text-white font-mono focus:outline-none focus:border-hack-green disabled:opacity-50 transition-all hover:border-hack-green/50"
          >
            <option value="">-- Select a PC --</option>
            {pcs.map((pc) => (
              <option key={pc.pc_id} value={pc.pc_id}>
                {pc.name || pc.pc_id} {pc.connected ? '🟢' : '🔴'}
              </option>
            ))}
          </select>
        </div>

        {/* Enhanced Controls */}
        <div className="flex flex-wrap gap-3 mb-6">
          <button
            onClick={startStream}
            disabled={!selectedPC || isStreaming || isConnecting}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-hack-green/20 to-hack-green/10 hover:from-hack-green/30 hover:to-hack-green/20 border-2 border-hack-green text-hack-green rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-lg hover:shadow-hack-green/20"
          >
            {isConnecting ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <Power size={20} />
                <span>Start Stream</span>
              </>
            )}
          </button>

          <button
            onClick={stopStream}
            disabled={!isStreaming}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-500/20 to-red-500/10 hover:from-red-500/30 hover:to-red-500/20 border-2 border-red-500 text-red-400 rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-lg hover:shadow-red-500/20"
          >
            <PowerOff size={20} />
            <span>Stop Stream</span>
          </button>

          <button
            onClick={loadPCs}
            className="flex items-center gap-2 px-6 py-3 bg-hack-gray/80 hover:bg-hack-gray border-2 border-hack-green/30 text-white rounded-lg transition-all font-mono font-semibold shadow-lg"
          >
            <RefreshCw size={20} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Enhanced Status */}
        {selectedPCData && (
          <div className="p-5 bg-hack-darker/60 rounded-lg border border-hack-green/20 backdrop-blur-sm">
            <div className="grid grid-cols-2 gap-6 text-sm font-mono">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${isStreaming ? 'bg-hack-green animate-pulse shadow-lg shadow-hack-green/50' : 'bg-gray-500'}`}></div>
                <div>
                  <span className="text-gray-400 block text-xs">PC ID</span>
                  <span className="text-white font-semibold">{selectedPCData.pc_id}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${isStreaming ? 'bg-hack-green animate-pulse shadow-lg shadow-hack-green/50' : 'bg-gray-500'}`}></div>
                <div>
                  <span className="text-gray-400 block text-xs">Status</span>
                  <span className={isStreaming ? 'text-hack-green font-semibold' : 'text-gray-400'}>
                    {isStreaming ? 'Streaming' : 'Stopped'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Enhanced Audio Chunks List */}
      <div className="bg-gradient-to-br from-hack-dark via-hack-dark to-hack-darker border border-hack-green/30 rounded-xl p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className="p-2.5 bg-hack-green/10 rounded-lg border border-hack-green/30">
              <Waveform className="text-hack-green" size={24} />
            </div>
            <div>
              <h3 className="text-xl font-mono text-hack-green font-bold">Audio Chunks</h3>
              <p className="text-xs text-gray-400 font-mono mt-0.5">
                {audioChunks.length} {audioChunks.length === 1 ? 'chunk' : 'chunks'} recorded
              </p>
            </div>
          </div>
          {audioChunks.length > 0 && (
            <button
              onClick={clearAllChunks}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-400 rounded-lg transition-all font-mono text-sm font-semibold shadow-lg hover:shadow-red-500/20"
            >
              <Trash2 size={16} />
              Clear All
            </button>
          )}
        </div>

        {audioChunks.length === 0 ? (
          <div className="text-center py-20">
            <div className="inline-flex p-6 bg-hack-darker/60 rounded-full mb-6 border border-hack-green/20">
              <Mic className="text-gray-500" size={48} />
            </div>
            <p className="text-gray-400 font-mono text-xl mb-2 font-semibold">
              {isStreaming ? 'Waiting for audio chunks...' : 'No audio chunks received'}
            </p>
            <p className="text-gray-600 font-mono text-sm">
              {isStreaming 
                ? 'Audio will appear here as chunks are received from the PC' 
                : 'Start streaming to capture audio from the selected PC'}
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
            {audioChunks.map((chunk, index) => (
              <div
                key={chunk.id}
                className={`p-5 bg-hack-darker/60 rounded-xl border-2 transition-all backdrop-blur-sm ${
                  playingChunkId === chunk.id
                    ? 'border-hack-green shadow-xl shadow-hack-green/30 bg-hack-green/5'
                    : 'border-hack-green/20 hover:border-hack-green/40 hover:bg-hack-darker/80'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-3">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-hack-green/20 rounded border border-hack-green/30">
                          <span className="text-hack-green font-mono font-bold text-lg">
                            {chunk.chunkNumber}
                          </span>
                        </div>
                        <span className="text-gray-300 font-mono font-semibold text-base">
                          Audio Chunk
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-400">
                        <Clock size={14} />
                        <span className="font-mono text-sm">{formatTime(chunk.timestamp)}</span>
                      </div>
                      {playingChunkId === chunk.id && (
                        <span className="flex items-center gap-2 px-3 py-1 bg-hack-green/20 border border-hack-green/50 rounded-lg text-hack-green font-mono text-xs font-semibold animate-pulse">
                          <Radio size={12} className="animate-pulse" />
                          Playing
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-6 text-xs font-mono text-gray-400">
                      <div className="flex items-center gap-1.5">
                        <Clock size={12} />
                        <span>{chunk.duration}s</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Waveform size={12} />
                        <span>{chunk.sampleRate}Hz</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Radio size={12} />
                        <span>{chunk.channels === 1 ? 'Mono' : 'Stereo'}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <HardDrive size={12} />
                        <span>{chunk.size} KB</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-6">
                    {playingChunkId === chunk.id ? (
                      <button
                        onClick={stopPlayback}
                        className="px-5 py-2.5 bg-red-500/20 hover:bg-red-500/30 border-2 border-red-500 text-red-400 rounded-lg transition-all font-mono text-sm font-semibold flex items-center gap-2 shadow-lg"
                      >
                        <PowerOff size={16} />
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => playChunk(chunk)}
                        disabled={playingChunkId !== null}
                        className="px-5 py-2.5 bg-hack-green/20 hover:bg-hack-green/30 border-2 border-hack-green text-hack-green rounded-lg transition-all font-mono text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg hover:shadow-hack-green/20"
                      >
                        <Play size={16} />
                        Play
                      </button>
                    )}
                    <button
                      onClick={() => downloadChunk(chunk)}
                      className="px-5 py-2.5 bg-blue-500/20 hover:bg-blue-500/30 border-2 border-blue-500 text-blue-400 rounded-lg transition-all font-mono text-sm font-semibold flex items-center gap-2 shadow-lg hover:shadow-blue-500/20"
                    >
                      <Download size={16} />
                      Download
                    </button>
                    <button
                      onClick={() => deleteChunk(chunk.id)}
                      className="px-4 py-2.5 bg-red-500/20 hover:bg-red-500/30 border-2 border-red-500 text-red-400 rounded-lg transition-all font-mono text-sm shadow-lg hover:shadow-red-500/20"
                      title="Delete chunk"
                    >
                      <Trash2 size={16} />
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
