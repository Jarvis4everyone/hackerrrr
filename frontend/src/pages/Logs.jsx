import React, { useEffect, useState, useMemo } from 'react'
import { 
  FileText, 
  RefreshCw, 
  Pause, 
  Play, 
  Monitor, 
  Search, 
  Filter,
  X,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  Info,
  Bug
} from 'lucide-react'
import { getLogs, getPCs, getScripts } from '../services/api'

const Logs = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [isLive, setIsLive] = useState(true)
  const [pcs, setPCs] = useState([])
  const [scripts, setScripts] = useState([])
  
  // Filters
  const [selectedPC, setSelectedPC] = useState(null)
  const [selectedScript, setSelectedScript] = useState(null)
  const [selectedLevel, setSelectedLevel] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    loadPCs()
    loadScripts()
  }, [])

  useEffect(() => {
    loadLogs()
    
    if (!isLive) return
    
    const interval = setInterval(() => {
      loadLogs()
    }, 2000)
    
    return () => clearInterval(interval)
  }, [isLive, selectedPC, selectedScript, selectedLevel])

  const loadPCs = async () => {
    try {
      const data = await getPCs(false)
      setPCs(data.pcs || [])
    } catch (error) {
      console.error('Error loading PCs:', error)
    }
  }

  const loadScripts = async () => {
    try {
      const data = await getScripts()
      setScripts(data.scripts || [])
    } catch (error) {
      console.error('Error loading scripts:', error)
    }
  }

  const loadLogs = async () => {
    setLoading(true)
    try {
      const data = await getLogs(500, selectedPC, selectedScript, selectedLevel)
      
      // Filter logs - only show logs with valid script names
      const allLogs = (data.logs || []).filter(log => {
        return log.script_name && log.script_name !== 'unknown'
      })
      
      // Sort from latest to oldest
      allLogs.sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
        return timeB - timeA // Latest first
      })
      
      setLogs(allLogs)
    } catch (error) {
      console.error('Error loading logs:', error)
    } finally {
      setLoading(false)
    }
  }

  // Filter logs by search query
  const filteredLogs = useMemo(() => {
    let filtered = logs

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(log => {
        const content = (log.log_content || '').toLowerCase()
        const scriptName = (log.script_name || '').toLowerCase()
        const pcId = (log.pc_id || '').toLowerCase()
        return content.includes(query) || scriptName.includes(query) || pcId.includes(query)
      })
    }

    return filtered
  }, [logs, searchQuery])

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getLogLevelIcon = (level) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
        return <AlertCircle className="text-red-400" size={16} />
      case 'WARNING':
        return <AlertTriangle className="text-yellow-400" size={16} />
      case 'SUCCESS':
        return <CheckCircle className="text-green-400" size={16} />
      case 'DEBUG':
        return <Bug className="text-gray-400" size={16} />
      case 'INFO':
      default:
        return <Info className="text-hack-green" size={16} />
    }
  }

  const getLogLevelColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400 bg-red-500/10 border-red-500/30'
      case 'WARNING':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
      case 'SUCCESS':
        return 'text-green-400 bg-green-500/10 border-green-500/30'
      case 'DEBUG':
        return 'text-gray-400 bg-gray-500/10 border-gray-500/30'
      case 'INFO':
      default:
        return 'text-hack-green bg-hack-green/10 border-hack-green/30'
    }
  }

  const clearFilters = () => {
    setSelectedPC(null)
    setSelectedScript(null)
    setSelectedLevel(null)
    setSearchQuery('')
  }

  const hasActiveFilters = selectedPC || selectedScript || selectedLevel || searchQuery.trim()

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 bg-hack-green/10 rounded-lg border border-hack-green/20">
              <FileText className="text-hack-green" size={24} />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white font-mono">Script Logs</h1>
              <p className="text-gray-400 text-xs sm:text-sm mt-1 font-mono">
                {filteredLogs.length} log{filteredLogs.length !== 1 ? 's' : ''} {hasActiveFilters && '(filtered)'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 text-sm sm:text-base font-mono ${
                showFilters || hasActiveFilters
                  ? 'bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green'
                  : 'bg-hack-gray hover:bg-hack-gray/80 border border-gray-700 text-gray-300'
              }`}
            >
              <Filter size={16} />
              <span className="hidden sm:inline">Filters</span>
            </button>
            
            <button
              onClick={() => setIsLive(!isLive)}
              className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 text-sm sm:text-base font-mono ${
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
              className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 sm:px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 text-sm sm:text-base font-mono"
            >
              <RefreshCw size={16} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Filters Panel */}
        {(showFilters || hasActiveFilters) && (
          <div className="mt-4 pt-4 border-t border-gray-700 space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              {/* Search */}
              <div className="flex-1 min-w-[200px] relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                <input
                  type="text"
                  placeholder="Search logs..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-black/50 border border-white/10 hover:border-hack-green/50 focus:border-hack-green/50 text-white px-10 py-2 rounded-lg font-mono text-sm focus:outline-none transition-all"
                />
              </div>

              {/* PC Filter */}
              <div className="relative min-w-[150px]">
                <Monitor className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                <select
                  value={selectedPC || ''}
                  onChange={(e) => setSelectedPC(e.target.value || null)}
                  className="w-full bg-black/50 border border-white/10 hover:border-hack-green/50 focus:border-hack-green/50 text-white pl-10 pr-8 py-2 rounded-lg font-mono text-sm appearance-none focus:outline-none transition-all cursor-pointer"
                >
                  <option value="" className="bg-hack-dark text-white">All PCs</option>
                  {pcs.map((pc) => (
                    <option key={pc.pc_id} value={pc.pc_id} className="bg-hack-dark text-white">
                      {pc.name || pc.pc_id}
                    </option>
                  ))}
                </select>
              </div>

              {/* Script Filter */}
              <div className="relative min-w-[150px]">
                <FileText className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                <select
                  value={selectedScript || ''}
                  onChange={(e) => setSelectedScript(e.target.value || null)}
                  className="w-full bg-black/50 border border-white/10 hover:border-hack-green/50 focus:border-hack-green/50 text-white pl-10 pr-8 py-2 rounded-lg font-mono text-sm appearance-none focus:outline-none transition-all cursor-pointer"
                >
                  <option value="" className="bg-hack-dark text-white">All Scripts</option>
                  {scripts.map((script) => (
                    <option key={script.name} value={script.name} className="bg-hack-dark text-white">
                      {script.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Level Filter */}
              <div className="relative min-w-[120px]">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                <select
                  value={selectedLevel || ''}
                  onChange={(e) => setSelectedLevel(e.target.value || null)}
                  className="w-full bg-black/50 border border-white/10 hover:border-hack-green/50 focus:border-hack-green/50 text-white pl-10 pr-8 py-2 rounded-lg font-mono text-sm appearance-none focus:outline-none transition-all cursor-pointer"
                >
                  <option value="" className="bg-hack-dark text-white">All Levels</option>
                  <option value="INFO" className="bg-hack-dark text-white">INFO</option>
                  <option value="SUCCESS" className="bg-hack-dark text-white">SUCCESS</option>
                  <option value="WARNING" className="bg-hack-dark text-white">WARNING</option>
                  <option value="ERROR" className="bg-hack-dark text-white">ERROR</option>
                  <option value="DEBUG" className="bg-hack-dark text-white">DEBUG</option>
                </select>
              </div>

              {/* Clear Filters */}
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="px-3 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 rounded-lg font-mono text-sm transition-all flex items-center gap-2"
                >
                  <X size={16} />
                  <span className="hidden sm:inline">Clear</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Logs List */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-hack-green mx-auto mb-4"></div>
            <p className="text-gray-400 font-mono">Loading logs...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="mx-auto text-gray-600 mb-4" size={48} />
            <p className="text-gray-400 font-mono text-lg mb-2">
              {hasActiveFilters ? 'No logs match your filters' : 'No logs found'}
            </p>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-hack-green hover:text-hack-green/80 font-mono text-sm mt-2"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {filteredLogs.map((log, index) => (
              <div
                key={log.id || index}
                className="bg-hack-dark/30 hover:bg-hack-dark/50 transition-colors p-4 sm:p-6"
              >
                <div className="flex flex-col gap-3 sm:gap-4">
                  {/* Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4">
                    <div className="flex items-start sm:items-center gap-3 flex-1 min-w-0">
                      {/* Log Level Badge */}
                      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border flex-shrink-0 ${getLogLevelColor(log.log_level)}`}>
                        {getLogLevelIcon(log.log_level)}
                        <span className="text-xs font-medium font-mono">{log.log_level || 'INFO'}</span>
                      </div>
                      
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-white font-semibold font-mono text-sm sm:text-base truncate">
                            {log.script_name}
                          </h3>
                          <span className="text-gray-500 text-xs">•</span>
                          <span className="text-gray-400 text-xs font-mono truncate" title={log.pc_id}>
                            {log.pc_id}
                          </span>
                        </div>
                        <p className="text-gray-500 text-xs font-mono mt-1">
                          {formatDate(log.timestamp)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Log Content */}
                  {log.log_content && (
                    <div className="bg-black/40 border border-gray-700 rounded-lg p-3 sm:p-4">
                      <pre className="text-white whitespace-pre-wrap break-words text-sm sm:text-base font-mono leading-relaxed overflow-x-auto max-h-[500px] overflow-y-auto">
                        {log.log_content}
                      </pre>
                    </div>
                  )}

                  {/* Log File Path */}
                  {log.log_file_path && (
                    <div className="flex items-center gap-2 text-gray-500 text-xs font-mono">
                      <FileText size={12} />
                      <span className="truncate" title={log.log_file_path}>
                        {log.log_file_path}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Logs
