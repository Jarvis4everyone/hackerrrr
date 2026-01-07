import React, { useEffect, useState, useRef } from 'react'
import { Terminal, RefreshCw, Pause, Play, ChevronDown, ChevronRight, Monitor } from 'lucide-react'
import { getLogs, getPCLogs, getPCs } from '../services/api'

const Logs = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [isLive, setIsLive] = useState(true)
  const [expandedScripts, setExpandedScripts] = useState(new Set())
  const [selectedPC, setSelectedPC] = useState(null)
  const [pcs, setPCs] = useState([])
  const scrollContainerRef = useRef(null)
  const wasAtBottomRef = useRef(true)

  const checkIfAtBottom = () => {
    if (!scrollContainerRef.current) return false
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current
    return scrollHeight - scrollTop - clientHeight < 100
  }

  // Removed autoScroll - we'll handle scrolling directly in loadLogs

  useEffect(() => {
    loadPCs()
  }, [])

  useEffect(() => {
    loadLogs()
    
    if (!isLive) return
    
    const interval = setInterval(() => {
      loadLogs()
    }, 2000)
    
    return () => clearInterval(interval)
  }, [isLive, selectedPC])

  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    const handleScroll = () => {
      wasAtBottomRef.current = checkIfAtBottom()
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [])

  const loadPCs = async () => {
    try {
      const data = await getPCs(false)
      setPCs(data.pcs || [])
    } catch (error) {
      console.error('Error loading PCs:', error)
    }
  }

  const loadLogs = async () => {
    // Save current scroll position before updating
    const container = scrollContainerRef.current
    const wasAtBottom = container ? checkIfAtBottom() : false
    const savedScrollTop = container ? container.scrollTop : 0
    
    setLoading(true)
    try {
      const data = await getLogs(500, selectedPC, null, null)
      
      // Show all logs - don't filter by content length
      // Only filter out logs without script_name or with 'unknown' script
      const allLogs = data.logs || []
      const scriptLogs = allLogs.filter(log => {
        // Only filter out logs without a valid script name
        return log.script_name && log.script_name !== 'unknown'
      })
      
      // Sort from latest to oldest
      scriptLogs.sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
        return timeB - timeA // Latest first
      })
      
      setLogs(scriptLogs)
      
      // After DOM updates, restore scroll position or auto-scroll to bottom
      setTimeout(() => {
        if (!container) return
        
        if (wasAtBottom) {
          // User was at bottom, scroll to new bottom
          container.scrollTop = container.scrollHeight
          wasAtBottomRef.current = true
        } else {
          // User was not at bottom, preserve their scroll position
          container.scrollTop = savedScrollTop
          wasAtBottomRef.current = false
        }
      }, 100)
    } catch (error) {
      console.error('Error loading logs:', error)
    } finally {
      setLoading(false)
    }
  }

  // Group logs by script name
  const groupedByScript = logs.reduce((acc, log) => {
    const scriptName = log.script_name || 'Unknown'
    if (!acc[scriptName]) {
      acc[scriptName] = []
    }
    acc[scriptName].push(log)
    return acc
  }, {})

  // No filtering - show all scripts
  const filteredScripts = Object.entries(groupedByScript)

  const toggleScript = (scriptName) => {
    const newExpanded = new Set(expandedScripts)
    if (newExpanded.has(scriptName)) {
      newExpanded.delete(scriptName)
    } else {
      newExpanded.add(scriptName)
    }
    setExpandedScripts(newExpanded)
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getLogLevelColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400 bg-red-500/20 border-red-500/40'
      case 'WARNING':
        return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/40'
      case 'SUCCESS':
        return 'text-green-400 bg-green-500/20 border-green-500/40'
      case 'DEBUG':
        return 'text-gray-400 bg-gray-500/20 border-gray-500/40'
      case 'INFO':
      default:
        return 'text-hack-green bg-hack-green/20 border-hack-green/40'
    }
  }


  return (
    <div className="min-h-screen bg-black p-3 sm:p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
        {/* Header */}
        <div className="bg-hack-dark/90 backdrop-blur-sm border border-gray-800 rounded-xl p-4 sm:p-6 shadow-2xl">
          <div className="flex items-center justify-between flex-wrap gap-3 sm:gap-4">
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="p-2 sm:p-3 bg-hack-green/10 rounded-lg border border-hack-green/20">
                <Terminal className="text-hack-green" size={24} />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold text-white">Script Logs</h1>
                <p className="text-gray-400 text-xs sm:text-sm mt-1">View script execution logs</p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              {/* PC Filter */}
              <div className="relative">
                <select
                  value={selectedPC || ''}
                  onChange={(e) => setSelectedPC(e.target.value || null)}
                  className="bg-black/50 border border-white/10 hover:border-hack-green/50 text-white px-3 sm:px-4 py-2 rounded-lg font-medium transition-all text-sm sm:text-base appearance-none pr-8 sm:pr-10 focus:outline-none focus:border-hack-green/50 cursor-pointer"
                  style={{ backgroundImage: 'none' }}
                >
                  <option value="" className="bg-hack-dark text-white">All PCs</option>
                  {pcs.map((pc) => (
                    <option key={pc.pc_id} value={pc.pc_id} className="bg-hack-dark text-white">
                      {pc.name || pc.pc_id} {pc.hostname ? `(${pc.hostname})` : ''}
                    </option>
                  ))}
                </select>
                <Monitor className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none" size={16} />
              </div>
              <button
                onClick={() => setIsLive(!isLive)}
                className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 text-sm sm:text-base ${
                  isLive
                    ? 'bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 text-green-400'
                    : 'bg-hack-gray hover:bg-hack-gray/80 border border-gray-700 text-gray-300'
                }`}
              >
                {isLive ? <Pause size={16} /> : <Play size={16} />}
                <span className="hidden sm:inline">{isLive ? 'Pause' : 'Resume'}</span>
              </button>
              <button
                onClick={loadLogs}
                className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 sm:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 text-sm sm:text-base"
              >
                <RefreshCw size={16} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Logs Display */}
        <div className="bg-hack-dark/90 backdrop-blur-sm border border-gray-800 rounded-xl overflow-hidden shadow-xl">
          {loading && logs.length === 0 ? (
            <div className="text-center py-8 sm:py-12">
              <div className="animate-spin rounded-full h-10 w-10 sm:h-12 sm:w-12 border-t-2 border-b-2 border-hack-green mx-auto mb-4"></div>
              <p className="text-gray-400 font-medium text-sm sm:text-base">Loading...</p>
            </div>
          ) : (
            <div 
              ref={scrollContainerRef}
              className="overflow-y-auto max-h-[500px] sm:max-h-[600px] md:max-h-[700px] custom-scrollbar"
            >
              {filteredScripts.length === 0 ? (
                <div className="text-center py-8 sm:py-12">
                  <Terminal className="mx-auto text-gray-600 mb-4" size={40} />
                  <p className="text-gray-400 font-medium text-sm sm:text-base">No script logs found</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-800">
                  {filteredScripts.map(([scriptName, scriptLogs]) => {
                    const isExpanded = expandedScripts.has(scriptName)
                    return (
                      <div key={scriptName} className="bg-hack-dark/30 hover:bg-hack-dark/50 transition-colors">
                        {/* Script Header - Clickable */}
                        <button
                          onClick={() => toggleScript(scriptName)}
                          className="w-full text-left bg-hack-gray/50 p-3 sm:p-4 border-b border-gray-700 hover:bg-hack-gray/70 transition-colors"
                        >
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                              {isExpanded ? (
                                <ChevronDown className="text-hack-green flex-shrink-0" size={18} />
                              ) : (
                                <ChevronRight className="text-hack-green flex-shrink-0" size={18} />
                              )}
                              <div className="p-1.5 sm:p-2 bg-hack-green/10 rounded-lg border border-hack-green/20 flex-shrink-0">
                                <Terminal size={16} className="text-hack-green" />
                              </div>
                              <div className="min-w-0 flex-1">
                                <h3 className="text-white font-semibold text-sm sm:text-base truncate">{scriptName}</h3>
                                <p className="text-gray-400 text-xs mt-1">
                                  {scriptLogs.length} log{scriptLogs.length !== 1 ? 's' : ''} • Latest: {formatDate(scriptLogs[0]?.timestamp)}
                                </p>
                              </div>
                            </div>
                            <div className="text-right flex-shrink-0">
                              <p className="text-gray-500 text-xs">
                                {formatDate(scriptLogs[scriptLogs.length - 1]?.timestamp)}
                              </p>
                            </div>
                          </div>
                        </button>
                        
                        {/* Logs - Expandable */}
                        {isExpanded && (
                          <div className="p-3 sm:p-4 space-y-2 sm:space-y-3">
                            {scriptLogs.map((log, idx) => (
                              <div
                                key={idx}
                                className="bg-hack-gray/50 border border-gray-700 rounded-lg p-3 sm:p-4 hover:border-gray-600 transition-colors"
                              >
                                <div className="flex flex-col sm:flex-row items-start gap-3 sm:gap-4">
                                  {/* Log Level Badge */}
                                  <span className={`px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg border text-xs font-medium flex-shrink-0 ${getLogLevelColor(log.log_level)}`}>
                                    {log.log_level}
                                  </span>
                                  
                                  {/* Log Content */}
                                  <div className="flex-1 min-w-0 w-full">
                                    <div className="flex items-center gap-2 sm:gap-3 mb-2 flex-wrap">
                                      <span className="text-gray-500 text-xs font-mono">
                                        {formatDate(log.timestamp)}
                                      </span>
                                      <span className="text-gray-600 text-xs">•</span>
                                      <span className="text-gray-400 text-xs font-mono truncate">
                                        {log.pc_id}
                                      </span>
                                    </div>
                                    <pre className="text-gray-200 whitespace-pre-wrap break-words text-xs sm:text-sm font-mono leading-relaxed overflow-x-auto">
                                      {log.log_content}
                                    </pre>
                                    {log.log_file_path && (
                                      <div className="mt-2 pt-2 border-t border-gray-700">
                                        <p className="text-gray-500 text-xs flex items-center gap-1.5">
                                          <Terminal size={12} />
                                          <span className="font-mono truncate">{log.log_file_path}</span>
                                        </p>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Logs
