import { useEffect, useState, useRef } from 'react'
import { Monitor, Power, PowerOff, RefreshCw, Maximize2, Loader2, Radio, Monitor as ScreenIcon } from 'lucide-react'
import { getPCs, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'
import { useStreaming } from '../contexts/StreamingContext'

const ScreenPage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const screenRef = useRef(null)
  const containerRef = useRef(null)
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
      unregisterStopCallback('screen')
      setStreamActive('screen', false)
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

  const toggleFullscreen = () => {
    if (!isFullscreen) {
      if (containerRef.current?.requestFullscreen) {
        containerRef.current.requestFullscreen()
      } else if (containerRef.current?.webkitRequestFullscreen) {
        containerRef.current.webkitRequestFullscreen()
      } else if (containerRef.current?.mozRequestFullScreen) {
        containerRef.current.mozRequestFullScreen()
      } else if (containerRef.current?.msRequestFullscreen) {
        containerRef.current.msRequestFullscreen()
      }
      setIsFullscreen(true)
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen()
      } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen()
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen()
      }
      setIsFullscreen(false)
    }
  }

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
    document.addEventListener('mozfullscreenchange', handleFullscreenChange)
    document.addEventListener('MSFullscreenChange', handleFullscreenChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange)
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange)
    }
  }, [])

  const startStream = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'error')
      return
    }

    setIsConnecting(true)

    try {
      // Get WebSocket URL
      const wsUrl = getWebSocketUrl(`/ws/stream/${selectedPC}/screen`)
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Screen] WebSocket connected')
        setIsConnecting(false)
        setIsStreaming(true)
        
        // Request to start stream
        ws.send(JSON.stringify({
          type: 'start_stream'
        }))
        
        showToast('Screen share started', 'success')
        
        // Register with streaming context
        setStreamActive('screen', true)
        registerStopCallback('screen', stopStream)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'screen_frame') {
            // Display frame immediately - no queuing, no delays
            // Since we're receiving 1 FPS, we can display each frame immediately
            if (screenRef.current && data.frame) {
              // Use requestAnimationFrame for smooth display
              requestAnimationFrame(() => {
                if (screenRef.current) {
                  screenRef.current.src = `data:image/jpeg;base64,${data.frame}`
                }
              })
            }
          } else if (data.type === 'stream_status') {
            console.log('[Screen] Stream status:', data)
            if (data.pc_streaming === false && isStreaming) {
              showToast('PC stopped streaming', 'info')
              setIsStreaming(false)
            }
          } else if (data.type === 'error') {
            showToast(`Stream error: ${data.message}`, 'error')
            setIsStreaming(false)
          }
        } catch (error) {
          console.error('[Screen] Error parsing message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[Screen] WebSocket error:', error)
        showToast('Connection error', 'error')
        setIsConnecting(false)
        setIsStreaming(false)
      }

      ws.onclose = () => {
        console.log('[Screen] WebSocket closed')
        setIsStreaming(false)
        setStreamActive('screen', false)
        unregisterStopCallback('screen')
        if (screenRef.current) {
          screenRef.current.src = ''
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[Screen] Error starting stream:', error)
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
        console.error('[Screen] Error sending stop:', e)
      }
      wsRef.current.close()
      wsRef.current = null
    }
    setIsStreaming(false)
    if (screenRef.current) {
      screenRef.current.src = ''
    }
    setStreamActive('screen', false)
    unregisterStopCallback('screen')
    showToast('Screen share stopped', 'info')
  }

  const selectedPCData = pcs.find(pc => pc.pc_id === selectedPC)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="animate-spin text-hack-green mx-auto mb-4" size={48} />
          <p className="text-gray-400 font-mono">Loading PCs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-hack-green/10 rounded-lg">
            <Monitor className="text-hack-green" size={28} />
          </div>
          <div>
            <h2 className="text-2xl font-mono text-hack-green font-bold">Screen Share</h2>
            <p className="text-sm text-gray-400 font-mono mt-1">View live screen sharing from connected PCs</p>
          </div>
        </div>

        {/* PC Selection */}
        <div className="mb-6">
          <label className="block text-sm font-mono text-gray-400 mb-2 flex items-center gap-2">
            <Radio size={16} />
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
            className="w-full px-4 py-2.5 bg-hack-darker border border-hack-green/30 rounded-lg text-white font-mono focus:outline-none focus:border-hack-green disabled:opacity-50 transition-all"
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
        <div className="flex flex-wrap gap-3 mb-6">
          <button
            onClick={startStream}
            disabled={!selectedPC || isStreaming || isConnecting}
            className="flex items-center gap-2 px-5 py-2.5 bg-hack-green/20 hover:bg-hack-green/30 border border-hack-green text-hack-green rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
          >
            {isConnecting ? (
              <>
                <Loader2 className="animate-spin" size={18} />
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
            className="flex items-center gap-2 px-5 py-2.5 bg-red-500/20 hover:bg-red-500/30 border border-red-500 text-red-400 rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
          >
            <PowerOff size={18} />
            Stop Stream
          </button>

          <button
            onClick={toggleFullscreen}
            disabled={!isStreaming}
            className="flex items-center gap-2 px-5 py-2.5 bg-hack-gray hover:bg-hack-gray/80 border border-hack-green/30 text-white rounded-lg transition-all font-mono disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
          >
            <Maximize2 size={18} />
            Fullscreen
          </button>

          <button
            onClick={loadPCs}
            className="flex items-center gap-2 px-5 py-2.5 bg-hack-gray hover:bg-hack-gray/80 border border-hack-green/30 text-white rounded-lg transition-all font-mono font-semibold"
          >
            <RefreshCw size={18} />
            Refresh
          </button>
        </div>

        {/* Status */}
        {selectedPCData && (
          <div className="p-4 bg-hack-darker rounded-lg border border-hack-green/20">
            <div className="grid grid-cols-2 gap-4 text-sm font-mono">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-hack-green animate-pulse' : 'bg-gray-500'}`}></div>
                <span className="text-gray-400">PC ID:</span>
                <span className="text-white">{selectedPCData.pc_id}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-hack-green animate-pulse' : 'bg-gray-500'}`}></div>
                <span className="text-gray-400">Status:</span>
                <span className={isStreaming ? 'text-hack-green font-semibold' : 'text-gray-400'}>
                  {isStreaming ? 'Streaming' : 'Stopped'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Screen Display */}
      <div 
        ref={containerRef}
        className="bg-hack-dark border border-hack-green/20 rounded-lg p-6"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-hack-green/10 rounded-lg">
            <ScreenIcon className="text-hack-green" size={20} />
          </div>
          <h3 className="text-lg font-mono text-hack-green font-bold">Screen Feed</h3>
        </div>
        <div className="bg-black rounded-lg overflow-hidden aspect-video flex items-center justify-center relative">
          {isStreaming ? (
            <>
              <img
                ref={screenRef}
                alt="Screen share"
                className="max-w-full max-h-full object-contain"
                style={{ display: 'block' }}
              />
              <div className="absolute top-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-red-500/80 backdrop-blur-sm rounded-lg">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                <span className="text-white text-xs font-mono font-semibold">LIVE</span>
              </div>
            </>
          ) : (
            <div className="text-center py-16">
              <div className="inline-flex p-4 bg-hack-darker rounded-full mb-4">
                <Monitor className="text-gray-500" size={48} />
              </div>
              <p className="text-gray-500 font-mono text-lg mb-2">
                {selectedPC ? 'Screen feed will appear here' : 'Select a PC to start streaming'}
              </p>
              <p className="text-gray-600 font-mono text-sm">
                {selectedPC ? 'Click "Start Stream" to view screen share' : 'Choose a PC from the dropdown above'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ScreenPage
