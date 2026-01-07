import { useEffect, useState, useRef } from 'react'
import { Camera, Power, PowerOff, RefreshCw } from 'lucide-react'
import { getPCs, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'

const CameraPage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const videoRef = useRef(null)
  const wsRef = useRef(null)
  const { showToast } = useToast()

  useEffect(() => {
    loadPCs()
    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close()
      }
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

    try {
      // Get WebSocket URL
      const wsUrl = getWebSocketUrl(`/ws/stream/${selectedPC}/camera`)
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Camera] WebSocket connected')
        setIsConnecting(false)
        setIsStreaming(true)
        
        // Request to start stream
        ws.send(JSON.stringify({
          type: 'start_stream'
        }))
        
        showToast('Camera stream started', 'success')
        
        // Register with streaming context
        setStreamActive('camera', true)
        registerStopCallback('camera', stopStream)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.type === 'camera_frame') {
            // Display frame
            if (videoRef.current && data.frame) {
              videoRef.current.src = `data:image/jpeg;base64,${data.frame}`
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
      }

      ws.onclose = () => {
        console.log('[Camera] WebSocket closed')
        setIsStreaming(false)
        if (videoRef.current) {
          videoRef.current.src = ''
        }
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
      // Request to stop stream
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
    setIsStreaming(false)
    if (videoRef.current) {
      videoRef.current.src = ''
    }
    setStreamActive('camera', false)
    unregisterStopCallback('camera')
    showToast('Camera stream stopped', 'info')
  }

  const selectedPCData = pcs.find(pc => pc.pc_id === selectedPC)

  return (
    <div className="space-y-6">
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Camera className="text-hack-green" size={24} />
          <h2 className="text-xl font-mono text-hack-green">Camera Stream</h2>
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

      {/* Video Display */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <h3 className="text-lg font-mono text-hack-green mb-4">Camera Feed</h3>
        <div className="bg-black rounded-lg overflow-hidden aspect-video flex items-center justify-center">
          {isStreaming ? (
            <img
              ref={videoRef}
              alt="Camera feed"
              className="max-w-full max-h-full object-contain"
              style={{ display: 'block' }}
            />
          ) : (
            <div className="text-gray-500 font-mono text-center">
              {selectedPC ? 'Click "Start Stream" to view camera feed' : 'Select a PC to start streaming'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default CameraPage

