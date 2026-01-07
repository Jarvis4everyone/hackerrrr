import { useEffect, useState, useRef } from 'react'
import { Camera, Power, PowerOff, RefreshCw, Loader2, Video, Radio, Wifi, WifiOff } from 'lucide-react'
import { getPCs, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'
import { useStreaming } from '../contexts/StreamingContext'

const CameraPage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [waitingForFrame, setWaitingForFrame] = useState(false)
  const [hasReceivedFrame, setHasReceivedFrame] = useState(false)
  const videoRef = useRef(null)
  const wsRef = useRef(null)
  const frameTimeoutRef = useRef(null)
  const { showToast } = useToast()
  const { setStreamActive, registerStopCallback, unregisterStopCallback } = useStreaming()

  useEffect(() => {
    loadPCs()
    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        stopStream()
      }
      if (frameTimeoutRef.current) {
        clearTimeout(frameTimeoutRef.current)
      }
      unregisterStopCallback('camera')
      setStreamActive('camera', false)
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
    setHasReceivedFrame(false)
    setWaitingForFrame(false)

    try {
      // Get WebSocket URL
      const wsUrl = getWebSocketUrl(`/ws/stream/${selectedPC}/camera`)
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Camera] WebSocket connected')
        setIsConnecting(false)
        setIsStreaming(true)
        setWaitingForFrame(true)
        
        // Request to start stream
        ws.send(JSON.stringify({
          type: 'start_stream'
        }))
        
        showToast('Camera stream started', 'success')
        
        // Set timeout to show waiting state if no frame received
        frameTimeoutRef.current = setTimeout(() => {
          if (!hasReceivedFrame) {
            setWaitingForFrame(true)
          }
        }, 2000)
        
        // Register with streaming context
        setStreamActive('camera', true)
        registerStopCallback('camera', stopStream)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'camera_frame') {
            // Clear waiting state when frame is received
            setWaitingForFrame(false)
            setHasReceivedFrame(true)
            if (frameTimeoutRef.current) {
              clearTimeout(frameTimeoutRef.current)
            }
            
            // Display frame immediately
            if (videoRef.current && data.frame) {
              requestAnimationFrame(() => {
                if (videoRef.current) {
                  videoRef.current.src = `data:image/jpeg;base64,${data.frame}`
                }
              })
            }
          } else if (data.type === 'stream_status') {
            console.log('[Camera] Stream status:', data)
            if (data.pc_streaming === false && isStreaming) {
              showToast('PC stopped streaming', 'info')
              setIsStreaming(false)
            }
          } else if (data.type === 'error') {
            showToast(`Stream error: ${data.message}`, 'error')
            setIsStreaming(false)
          }
        } catch (error) {
          console.error('[Camera] Error parsing message:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('[Camera] WebSocket error:', error)
        showToast('Connection error', 'error')
        setIsConnecting(false)
        setIsStreaming(false)
        setWaitingForFrame(false)
      }

      ws.onclose = () => {
        console.log('[Camera] WebSocket closed')
        setIsStreaming(false)
        setWaitingForFrame(false)
        setHasReceivedFrame(false)
        if (videoRef.current) {
          videoRef.current.src = ''
        }
        if (frameTimeoutRef.current) {
          clearTimeout(frameTimeoutRef.current)
        }
        setStreamActive('camera', false)
        unregisterStopCallback('camera')
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[Camera] Error starting stream:', error)
      showToast('Failed to start stream', 'error')
      setIsConnecting(false)
    }
  }

  const stopStream = () => {
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({
          type: 'stop_stream'
        }))
      } catch (e) {
        console.error('[Camera] Error sending stop:', e)
      }
      wsRef.current.close()
      wsRef.current = null
    }
    if (frameTimeoutRef.current) {
      clearTimeout(frameTimeoutRef.current)
    }
    setIsStreaming(false)
    setWaitingForFrame(false)
    setHasReceivedFrame(false)
    if (videoRef.current) {
      videoRef.current.src = ''
    }
    setStreamActive('camera', false)
    unregisterStopCallback('camera')
    showToast('Camera stream stopped', 'info')
  }

  const selectedPCData = pcs.find(pc => pc.pc_id === selectedPC)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[600px]">
        <div className="text-center">
          <div className="relative">
            <Loader2 className="animate-spin text-hack-green mx-auto mb-4" size={56} />
            <div className="absolute inset-0 flex items-center justify-center">
              <Camera className="text-hack-green/50" size={28} />
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
              <Camera className="text-hack-green" size={32} />
            </div>
            <div>
              <h2 className="text-3xl font-mono text-hack-green font-bold tracking-tight">Camera Stream</h2>
              <p className="text-sm text-gray-400 font-mono mt-1.5">View live camera feed from connected PCs</p>
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

      {/* Enhanced Video Display */}
      <div className="bg-gradient-to-br from-hack-dark via-hack-dark to-hack-darker border border-hack-green/30 rounded-xl p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 bg-hack-green/10 rounded-lg border border-hack-green/30">
            <Video className="text-hack-green" size={24} />
          </div>
          <h3 className="text-xl font-mono text-hack-green font-bold">Camera Feed</h3>
        </div>
        <div className="bg-black rounded-xl overflow-hidden aspect-video flex items-center justify-center relative border-2 border-hack-green/20">
          {isStreaming && waitingForFrame && !hasReceivedFrame ? (
            <div className="text-center py-20">
              <div className="relative mb-6">
                <Loader2 className="animate-spin text-hack-green mx-auto" size={64} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Camera className="text-hack-green/50" size={32} />
                </div>
              </div>
              <div className="flex items-center justify-center gap-2 mb-3">
                <Wifi className="text-hack-green animate-pulse" size={20} />
                <p className="text-hack-green font-mono text-lg font-semibold">Waiting for camera feed...</p>
              </div>
              <p className="text-gray-400 font-mono text-sm">Establishing connection with PC camera</p>
              <div className="mt-4 flex items-center justify-center gap-2">
                <div className="w-2 h-2 bg-hack-green rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-hack-green rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-hack-green rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          ) : isStreaming && hasReceivedFrame ? (
            <>
              <img
                ref={videoRef}
                alt="Camera feed"
                className="max-w-full max-h-full object-contain"
                style={{ display: 'block' }}
              />
              <div className="absolute top-4 right-4 flex items-center gap-2 px-4 py-2 bg-red-500/90 backdrop-blur-sm rounded-lg border border-red-400/50 shadow-xl">
                <div className="w-2.5 h-2.5 bg-white rounded-full animate-pulse"></div>
                <span className="text-white text-xs font-mono font-bold">LIVE</span>
              </div>
            </>
          ) : (
            <div className="text-center py-20">
              <div className="inline-flex p-6 bg-hack-darker/60 rounded-full mb-6 border border-hack-green/20">
                <Camera className="text-gray-500" size={56} />
              </div>
              <p className="text-gray-400 font-mono text-xl mb-2 font-semibold">
                {selectedPC ? 'Camera feed will appear here' : 'Select a PC to start streaming'}
              </p>
              <p className="text-gray-600 font-mono text-sm">
                {selectedPC ? 'Click "Start Stream" to view camera feed' : 'Choose a PC from the dropdown above'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CameraPage
