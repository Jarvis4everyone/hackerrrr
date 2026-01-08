import { useEffect, useState } from 'react'
import { Monitor, Trash2, Power, PowerOff, Wifi, WifiOff } from 'lucide-react'
import { getPCs, deletePC, checkConnection, stopPC } from '../services/api'
import { useToast } from '../components/ToastContainer'

const PCs = () => {
  const [pcs, setPCs] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedPC, setSelectedPC] = useState(null)
  const [stoppingPC, setStoppingPC] = useState(null)
  const { showToast } = useToast()

  useEffect(() => {
    loadPCs()
    const interval = setInterval(loadPCs, 3000)
    return () => clearInterval(interval)
  }, [])

  const loadPCs = async () => {
    try {
      const data = await getPCs()
      setPCs(data.pcs || [])
    } catch (error) {
      console.error('Error loading PCs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (pcId) => {
    if (!confirm(`Delete PC ${pcId}?`)) return
    try {
      await deletePC(pcId)
      loadPCs()
    } catch (error) {
      alert('Error deleting PC')
    }
  }

  const handleStop = async (pcId, e) => {
    e.stopPropagation() // Prevent opening the details modal
    if (!confirm(`Stop PC client ${pcId}?\n\nThe PC client will terminate completely. If it auto-starts, you'll need to stop it again.`)) return
    
    setStoppingPC(pcId)
    try {
      await stopPC(pcId)
      showToast(`Stop command sent to ${pcId}. The PC client will terminate shortly.`, 'success')
      // Refresh the list after a short delay
      setTimeout(() => {
        loadPCs()
        setStoppingPC(null)
      }, 2000)
    } catch (error) {
      showToast(`Failed to stop PC ${pcId}: ${error.response?.data?.detail || error.message}`, 'error')
      setStoppingPC(null)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-0">
        <h2 className="text-xl sm:text-2xl font-mono text-hack-green">Connected PCs</h2>
        <button
          onClick={loadPCs}
          className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 sm:px-4 py-2 rounded font-mono text-xs sm:text-sm transition-all"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-400 font-mono">Loading...</p>
        </div>
      ) : pcs.length === 0 ? (
        <div className="text-center py-12">
          <Monitor className="mx-auto text-gray-500 mb-4" size={48} />
          <p className="text-gray-400 font-mono">No PCs connected</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {pcs.map((pc) => (
            <div
              key={pc.pc_id}
              className={`bg-hack-dark border rounded-lg p-4 sm:p-6 hover:border-hack-green/40 transition-all ${
                pc.connected ? 'border-hack-green/20' : 'border-gray-700'
              }`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Monitor className={pc.connected ? 'text-hack-green' : 'text-gray-500'} size={24} />
                  <div>
                    <h3 className="text-hack-green font-mono font-bold">{pc.pc_id}</h3>
                    <p className="text-gray-400 text-sm font-mono">{pc.name || 'Unknown'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {pc.connected ? (
                    <Wifi className="text-hack-green" size={16} />
                  ) : (
                    <WifiOff className="text-gray-500" size={16} />
                  )}
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400 font-mono">Status</span>
                  <span className={pc.connected ? 'text-hack-green font-mono' : 'text-gray-500 font-mono'}>
                    {pc.connected ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
                {pc.hostname && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400 font-mono">Hostname</span>
                    <span className="text-gray-300 font-mono text-xs truncate ml-2" title={pc.hostname}>
                      {pc.hostname}
                    </span>
                  </div>
                )}
                {pc.ip_address && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400 font-mono">IP Address</span>
                    <span className="text-gray-300 font-mono text-xs">
                      {pc.ip_address}
                    </span>
                  </div>
                )}
                {pc.os_info && pc.os_info.platform && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400 font-mono">OS</span>
                    <span className="text-gray-300 font-mono text-xs">
                      {pc.os_info.platform} {pc.os_info.version ? `(${pc.os_info.version})` : ''}
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400 font-mono">Last Seen</span>
                  <span className="text-gray-500 font-mono text-xs">
                    {formatDate(pc.last_seen)}
                  </span>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedPC(pc)}
                  className="flex-1 bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 py-2 rounded font-mono text-xs transition-all"
                >
                  View
                </button>
                {pc.connected && (
                  <button
                    onClick={(e) => handleStop(pc.pc_id, e)}
                    disabled={stoppingPC === pc.pc_id}
                    className="bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/30 text-orange-400 px-3 py-2 rounded font-mono text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Stop PC client (one-time action)"
                  >
                    {stoppingPC === pc.pc_id ? (
                      <PowerOff size={14} className="animate-pulse" />
                    ) : (
                      <PowerOff size={14} />
                    )}
                  </button>
                )}
                <button
                  onClick={() => handleDelete(pc.pc_id)}
                  className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 px-3 py-2 rounded font-mono text-xs transition-all"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* PC Details Modal */}
      {selectedPC && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-auto">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-mono text-hack-green font-bold">{selectedPC.pc_id}</h3>
              <button
                onClick={() => setSelectedPC(null)}
                className="text-gray-400 hover:text-white text-2xl leading-none"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-6">
              {/* Basic Information */}
              <div>
                <h4 className="text-hack-green font-mono font-bold mb-3 text-sm border-b border-hack-green/20 pb-2">
                  BASIC INFORMATION
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">PC ID</p>
                    <p className="text-white font-mono text-sm">{selectedPC.pc_id || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">Name</p>
                    <p className="text-hack-green font-mono text-sm">{selectedPC.name || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">Status</p>
                    <p className={selectedPC.connected ? 'text-hack-green font-mono text-sm' : 'text-gray-500 font-mono text-sm'}>
                      {selectedPC.connected ? 'ONLINE' : 'OFFLINE'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">Hostname</p>
                    <p className="text-gray-300 font-mono text-sm">{selectedPC.hostname || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">IP Address</p>
                    <p className="text-gray-300 font-mono text-sm">{selectedPC.ip_address || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">Connected At</p>
                    <p className="text-gray-300 font-mono text-sm">{formatDate(selectedPC.connected_at) || 'N/A'}</p>
                  </div>
                  <div>
                    <p className="text-gray-400 font-mono text-xs mb-1">Last Seen</p>
                    <p className="text-gray-300 font-mono text-sm">{formatDate(selectedPC.last_seen) || 'N/A'}</p>
                  </div>
                </div>
              </div>

              {/* Operating System Information */}
              {selectedPC.os_info && Object.keys(selectedPC.os_info).length > 0 && (
                <div>
                  <h4 className="text-hack-green font-mono font-bold mb-3 text-sm border-b border-hack-green/20 pb-2">
                    OPERATING SYSTEM
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {selectedPC.os_info.platform && (
                      <div>
                        <p className="text-gray-400 font-mono text-xs mb-1">Platform</p>
                        <p className="text-white font-mono text-sm">{selectedPC.os_info.platform}</p>
                      </div>
                    )}
                    {selectedPC.os_info.version && (
                      <div>
                        <p className="text-gray-400 font-mono text-xs mb-1">Version</p>
                        <p className="text-white font-mono text-sm">{selectedPC.os_info.version}</p>
                      </div>
                    )}
                    {selectedPC.os_info.architecture && (
                      <div>
                        <p className="text-gray-400 font-mono text-xs mb-1">Architecture</p>
                        <p className="text-white font-mono text-sm">{selectedPC.os_info.architecture}</p>
                      </div>
                    )}
                    {Object.entries(selectedPC.os_info).map(([key, value]) => {
                      if (['platform', 'version', 'architecture'].includes(key)) return null
                      return (
                        <div key={key}>
                          <p className="text-gray-400 font-mono text-xs mb-1">{key.charAt(0).toUpperCase() + key.slice(1)}</p>
                          <p className="text-white font-mono text-sm">{String(value)}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Metadata Information */}
              {selectedPC.metadata && Object.keys(selectedPC.metadata).length > 0 && (
                <div>
                  <h4 className="text-hack-green font-mono font-bold mb-3 text-sm border-b border-hack-green/20 pb-2">
                    SYSTEM METADATA
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {Object.entries(selectedPC.metadata).map(([key, value]) => (
                      <div key={key}>
                        <p className="text-gray-400 font-mono text-xs mb-1">
                          {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                        </p>
                        <p className="text-white font-mono text-sm break-words">
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw JSON View (Optional) */}
              <div>
                <details className="bg-black/30 border border-white/10 rounded p-3">
                  <summary className="text-hack-green font-mono text-xs cursor-pointer hover:text-hack-green/80">
                    View Raw JSON
                  </summary>
                  <pre className="mt-3 text-gray-400 font-mono text-xs overflow-x-auto">
                    {JSON.stringify(selectedPC, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PCs

