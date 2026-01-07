import { useEffect, useState, useRef } from 'react'
import { Terminal as TerminalIcon, Power, PowerOff, RefreshCw, Copy } from 'lucide-react'
import { getPCs, startTerminalSession, stopTerminalSession, getWebSocketUrl } from '../services/api'
import { useToast } from '../components/ToastContainer'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const TerminalPage = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [commandInput, setCommandInput] = useState('')
  const terminalRef = useRef(null)
  const terminalInstanceRef = useRef(null)
  const fitAddonRef = useRef(null)
  const wsRef = useRef(null)
  const promptTimeoutRef = useRef(null)
  const lastCommandTimeRef = useRef(null)
  const inputRef = useRef(null)
  const { showToast } = useToast()

  useEffect(() => {
    loadPCs()
    
    // Initialize terminal after a short delay to ensure DOM is ready
    const initTerminal = () => {
      if (!terminalInstanceRef.current && terminalRef.current) {
        const term = new Terminal({
          theme: {
            background: '#000000',
            foreground: '#00ff00',
            cursor: '#00ff00',
            selection: '#00ff00',
            selectionBackground: '#00ff0040',
            black: '#000000',
            red: '#ff0000',
            green: '#00ff00',
            yellow: '#ffff00',
            blue: '#0000ff',
            magenta: '#ff00ff',
            cyan: '#00ffff',
            white: '#ffffff',
            brightBlack: '#808080',
            brightRed: '#ff8080',
            brightGreen: '#80ff80',
            brightYellow: '#ffff80',
            brightBlue: '#8080ff',
            brightMagenta: '#ff80ff',
            brightCyan: '#80ffff',
            brightWhite: '#ffffff'
          },
          fontSize: 14,
          fontFamily: 'Consolas, "Courier New", monospace',
          cursorBlink: true,
          cursorStyle: 'block',
          allowTransparency: false,
          rows: 24,
          cols: 80,
          disableStdin: false,  // Always allow input
          allowProposedApi: true,
          scrollback: 10000,  // Large scrollback buffer for scrolling
          rightClickSelectsWord: true,  // Right-click selects word
          copyOnSelect: false,  // Don't auto-copy on select (let user use Ctrl+C)
          wordSeparator: ' ()[]{}"\''  // Word separators for double-click selection
        })
        
        const fitAddon = new FitAddon()
        term.loadAddon(fitAddon)
        term.open(terminalRef.current)
        
        // Fit terminal to container
        setTimeout(() => {
          if (fitAddon) {
            fitAddon.fit()
          }
          // Force scroll to bottom after initial fit
          if (terminalInstanceRef.current) {
            terminalInstanceRef.current.scrollToBottom()
          }
        }, 100)
        
        terminalInstanceRef.current = term
        fitAddonRef.current = fitAddon
        
        // Show welcome message
        term.clear()
        term.writeln('\r\n\x1b[32m=== PowerShell Terminal ===\x1b[0m\r\n')
        term.writeln('\x1b[33mSelect a PC and click "Start Session" to begin\x1b[0m\r\n')
        term.write('> ')
        // Scroll to bottom after welcome message
        setTimeout(() => {
          if (terminalInstanceRef.current) {
            terminalInstanceRef.current.scrollToBottom()
          }
        }, 50)
        
        // Disable terminal input - we use the input box instead
        term.options.disableStdin = true
        
        // Handle keyboard events in terminal
        term.attachCustomKeyEventHandler((event) => {
          // Handle Ctrl+C - copy if text is selected, otherwise send interrupt
          if (event.ctrlKey && event.key === 'c') {
            const selection = term.getSelection()
            if (selection && selection.length > 0) {
              // Text is selected - copy it
              event.preventDefault()
              navigator.clipboard.writeText(selection).then(() => {
                showToast('Copied to clipboard', 'success')
              }).catch(() => {
                // Fallback
                const textArea = document.createElement('textarea')
                textArea.value = selection
                textArea.style.position = 'fixed'
                textArea.style.opacity = '0'
                document.body.appendChild(textArea)
                textArea.select()
                try {
                  document.execCommand('copy')
                  showToast('Copied to clipboard', 'success')
                } catch (err) {
                  showToast('Failed to copy', 'error')
                }
                document.body.removeChild(textArea)
              })
              return false
            }
            // No selection - allow default behavior (will be handled by onData)
          }
          // Handle Ctrl+V - paste
          if (event.ctrlKey && event.key === 'v') {
            event.preventDefault()
            navigator.clipboard.readText().then(text => {
              if (inputRef.current) {
                inputRef.current.value = text
                setCommandInput(text)
                inputRef.current.focus()
              }
            }).catch(() => {
              // Fallback or clipboard not available
            })
            return false
          }
          return true
        })
        
        // Still handle Ctrl+C if user clicks in terminal and presses it
        term.onData((data) => {
          // Check for Ctrl+C (interrupt signal)
          if (data === '\x03' || data === '\u0003') {
            // Check if text is selected first
            const selection = term.getSelection()
            if (selection && selection.length > 0) {
              // Text is selected - copy it (handled by key handler above)
              return
            }
            
            // No selection - send interrupt signal
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              // Clear any pending timeout
              if (promptTimeoutRef.current) {
                clearTimeout(promptTimeoutRef.current)
                promptTimeoutRef.current = null
              }
              
              // Send interrupt signal
              wsRef.current.send(JSON.stringify({
                type: 'interrupt'
              }))
              
              // Show interrupt message and new prompt
              if (terminalInstanceRef.current) {
                terminalInstanceRef.current.write('\r\n^C\r\n')
                // Scroll to bottom
                setTimeout(() => {
                  if (terminalInstanceRef.current) {
                    terminalInstanceRef.current.scrollToBottom()
                  }
                }, 10)
                // Show prompt after interrupt
                setTimeout(() => {
                  if (terminalInstanceRef.current) {
                    terminalInstanceRef.current.write('PS C:\\Users\\shres> ')
                    terminalInstanceRef.current.scrollToBottom()
                  }
                  // Focus input box
                  if (inputRef.current) {
                    inputRef.current.focus()
                  }
                }, 100)
              }
            }
            return
          }
        })
        
        // Focus input box after line feeds
        term.onLineFeed(() => {
          setTimeout(() => {
            if (inputRef.current) {
              inputRef.current.focus()
            }
          }, 50)
        })
        
        // Focus terminal after initialization
        setTimeout(() => {
          if (terminalInstanceRef.current) {
            terminalInstanceRef.current.focus()
          }
        }, 200)
      }
    }
    
    // Try to initialize immediately, then retry after a short delay
    initTerminal()
    const timeout = setTimeout(initTerminal, 100)
    
    // Cleanup on unmount
    return () => {
      clearTimeout(timeout)
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (terminalInstanceRef.current) {
        // Cleanup resize observer
        if (terminalInstanceRef.current._resizeObserver) {
          terminalInstanceRef.current._resizeObserver.disconnect()
        }
        terminalInstanceRef.current.dispose()
        terminalInstanceRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    // Resize terminal when window resizes
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
      }
    }
    
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const loadPCs = async () => {
    try {
      const data = await getPCs(true) // Only connected PCs
      setPCs(data.pcs || [])
      if (data.pcs && data.pcs.length > 0 && !selectedPC) {
        setSelectedPC(data.pcs[0].pc_id)
      }
    } catch (error) {
      console.error('Error loading PCs:', error)
      showToast('Error loading PCs', 'error')
    }
  }

  const connectWebSocket = (pcId, sessId) => {
    // Use the backend WebSocket URL instead of frontend URL
    const wsUrl = getWebSocketUrl(`/ws/terminal/${pcId}/${sessId}`)
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    
    ws.onopen = () => {
      setIsConnected(true)
      setIsStarting(false)
      if (terminalInstanceRef.current) {
        // Don't clear - wait for PC to send PowerShell welcome message
        terminalInstanceRef.current.writeln('\r\n\x1b[32m[+] Terminal session connected - waiting for PowerShell...\x1b[0m\r\n')
        // Scroll to bottom to show connection message
        setTimeout(() => {
          if (terminalInstanceRef.current) {
            terminalInstanceRef.current.scrollToBottom()
          }
        }, 50)
      }
      // Focus input box
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus()
        }
      }, 300)
      showToast('Terminal session connected', 'success')
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      if (data.type === 'output') {
        if (terminalInstanceRef.current) {
          // Write output to terminal exactly as received from PC
          if (data.output) {
            terminalInstanceRef.current.write(data.output)
            // Always scroll to bottom after writing to show latest output
            setTimeout(() => {
              if (terminalInstanceRef.current) {
                terminalInstanceRef.current.scrollToBottom()
              }
            }, 10)
          }
          
          // Check if output contains a prompt
          const output = data.output || ''
          const hasPrompt = output.includes('PS ') && output.includes('>') && 
                           (output.trim().endsWith('>') || output.includes('\nPS ') || output.includes('\r\nPS '))
          
          // If command is complete and has prompt, clear timeout and ensure terminal is ready
          if (data.is_complete && hasPrompt) {
            if (promptTimeoutRef.current) {
              clearTimeout(promptTimeoutRef.current)
              promptTimeoutRef.current = null
            }
            lastCommandTimeRef.current = null
            
            // Focus input box after command completes
            setTimeout(() => {
              if (inputRef.current) {
                inputRef.current.focus()
              }
            }, 100)
          } else if (data.is_complete && !hasPrompt) {
            // Command complete but no prompt - start 10 second timeout
            if (promptTimeoutRef.current) {
              clearTimeout(promptTimeoutRef.current)
            }
            lastCommandTimeRef.current = Date.now()
            promptTimeoutRef.current = setTimeout(() => {
              // 10 seconds passed, show prompt anyway
              if (terminalInstanceRef.current) {
                terminalInstanceRef.current.write('\r\nPS C:\\Users\\shres> ')
                terminalInstanceRef.current.scrollToBottom()
              }
              // Focus input box
              if (inputRef.current) {
                inputRef.current.focus()
              }
              promptTimeoutRef.current = null
              lastCommandTimeRef.current = null
            }, 10000)
          }
        }
      } else if (data.type === 'error') {
        if (terminalInstanceRef.current) {
          terminalInstanceRef.current.writeln(`\r\n\x1b[31m[ERROR] ${data.message}\x1b[0m\r\n`)
          // Scroll to bottom to show error
          setTimeout(() => {
            if (terminalInstanceRef.current) {
              terminalInstanceRef.current.scrollToBottom()
            }
          }, 10)
        }
        showToast(data.message, 'error')
      } else if (data.type === 'pong') {
        // Heartbeat response
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.writeln('\r\n\x1b[31m[ERROR] WebSocket connection error\x1b[0m\r\n')
      }
      showToast('Terminal connection error', 'error')
    }
    
    ws.onclose = () => {
      setIsConnected(false)
      // Clear any pending timeouts
      if (promptTimeoutRef.current) {
        clearTimeout(promptTimeoutRef.current)
        promptTimeoutRef.current = null
      }
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.writeln('\r\n\x1b[33m[!] Terminal session disconnected\x1b[0m\r\n')
      }
    }
  }

  const handleStartSession = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'warning')
      return
    }
    
    setIsStarting(true)
    try {
      const response = await startTerminalSession(selectedPC)
      const sessId = response.session_id
      setSessionId(sessId)
      
      // Wait a moment for PC to initialize terminal
      setTimeout(() => {
        connectWebSocket(selectedPC, sessId)
        setIsStarting(false)
      }, 1500)
    } catch (error) {
      console.error('Error starting terminal session:', error)
      showToast(error.response?.data?.detail || 'Error starting terminal session', 'error')
      setIsStarting(false)
    }
  }

  const handleSendCommand = () => {
    if (!isConnected || !commandInput.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return
    }
    
    const command = commandInput.trim()
    
    // Display command in terminal
    if (terminalInstanceRef.current) {
      terminalInstanceRef.current.write(`\r\nPS C:\\Users\\shres> ${command}\r\n`)
      // Scroll to bottom to show the command
      setTimeout(() => {
        if (terminalInstanceRef.current) {
          terminalInstanceRef.current.scrollToBottom()
        }
      }, 10)
    }
    
    // Send command to server
    wsRef.current.send(JSON.stringify({
      type: 'command',
      command: command + '\r\n'  // Add Enter key
    }))
    
    // Clear input and refocus
    setCommandInput('')
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus()
      }
    }, 50)
  }

  const handleCopySelected = () => {
    if (!terminalInstanceRef.current) return
    
    const selection = terminalInstanceRef.current.getSelection()
    if (selection) {
      navigator.clipboard.writeText(selection).then(() => {
        showToast('Copied to clipboard', 'success')
      }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea')
        textArea.value = selection
        textArea.style.position = 'fixed'
        textArea.style.opacity = '0'
        document.body.appendChild(textArea)
        textArea.select()
        try {
          document.execCommand('copy')
          showToast('Copied to clipboard', 'success')
        } catch (err) {
          showToast('Failed to copy', 'error')
        }
        document.body.removeChild(textArea)
      })
    } else {
      showToast('No text selected', 'warning')
    }
  }

  const handleStopSession = async () => {
    if (!sessionId || !selectedPC) return
    
    const currentSessionId = sessionId
    const currentPcId = selectedPC
    
    try {
      // Close WebSocket first
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      
      // Clear session state before API call to prevent double calls
      setSessionId(null)
      setIsConnected(false)
      
      // Try to stop session on server (ignore errors if already stopped)
      try {
        await stopTerminalSession(currentSessionId, currentPcId)
      } catch (error) {
        // Session might already be stopped, that's okay
        console.log('Session already stopped or not found')
      }
      
      if (terminalInstanceRef.current) {
        terminalInstanceRef.current.writeln('\r\n\x1b[33m[!] Terminal session stopped\x1b[0m\r\n')
        terminalInstanceRef.current.writeln('\x1b[33mWaiting for new session...\x1b[0m\r\n')
      }
      
      showToast('Terminal session stopped', 'success')
    } catch (error) {
      console.error('Error stopping terminal session:', error)
      // Don't show error if it's just a 404 (session already ended)
      if (error.response?.status !== 404) {
        showToast('Error stopping terminal session', 'error')
      }
    }
  }

  // Cleanup on page close/unmount
  useEffect(() => {
    return () => {
      // Clear timeouts
      if (promptTimeoutRef.current) {
        clearTimeout(promptTimeoutRef.current)
        promptTimeoutRef.current = null
      }
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (sessionId && selectedPC) {
        // Try to stop session silently
        stopTerminalSession(sessionId, selectedPC).catch(() => {})
      }
    }
  }, [sessionId, selectedPC])

  return (
    <div className="flex flex-col space-y-3 sm:space-y-4" style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Control Panel */}
      <div className="bg-hack-dark/90 backdrop-blur-sm border border-hack-green/30 rounded-xl p-4 sm:p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-hack-green/10 rounded-lg border border-hack-green/20">
            <TerminalIcon className="text-hack-green" size={24} />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white font-mono">PowerShell Terminal</h2>
            <p className="text-gray-400 text-xs sm:text-sm mt-1">Remote terminal session for connected PCs</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
          {/* PC Selection */}
          <div className="flex-1 w-full sm:w-auto">
            <label className="block text-gray-400 font-mono text-sm mb-2">Select PC</label>
            <select
              value={selectedPC}
              onChange={(e) => setSelectedPC(e.target.value)}
              disabled={isConnected || isStarting}
              className="w-full bg-black/50 border border-white/10 hover:border-hack-green/50 text-white px-4 py-2 rounded-lg font-mono text-sm focus:outline-none focus:border-hack-green/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="" className="bg-hack-dark">Select a PC</option>
              {pcs.map((pc) => (
                <option key={pc.pc_id} value={pc.pc_id} className="bg-hack-dark">
                  {pc.name || pc.pc_id} {pc.connected ? '(Online)' : '(Offline)'}
                </option>
              ))}
            </select>
          </div>

          {/* Session Controls */}
          <div className="flex gap-2">
            {!isConnected && !sessionId ? (
              <button
                onClick={handleStartSession}
                disabled={!selectedPC || isStarting}
                className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-4 sm:px-6 py-2 rounded-lg font-mono text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isStarting ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Starting...</span>
                  </>
                ) : (
                  <>
                    <Power size={16} />
                    <span>Start Session</span>
                  </>
                )}
              </button>
            ) : (
              <button
                onClick={handleStopSession}
                className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 px-4 sm:px-6 py-2 rounded-lg font-mono text-sm transition-all flex items-center gap-2"
              >
                <PowerOff size={16} />
                <span>Stop Session</span>
              </button>
            )}
            
            <button
              onClick={loadPCs}
              className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 sm:px-4 py-2 rounded-lg font-mono text-xs sm:text-sm transition-all flex items-center gap-2"
            >
              <RefreshCw size={16} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {/* Status */}
        <div className="mt-4 flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-hack-green animate-pulse' : 'bg-gray-500'}`}></div>
          <span className="text-xs font-mono text-gray-400">
            {isConnected ? 'Connected' : sessionId ? 'Connecting...' : 'Not Connected'}
          </span>
          {sessionId && (
            <span className="text-xs font-mono text-gray-500 ml-2">
              Session: {sessionId.substring(0, 8)}...
            </span>
          )}
        </div>
      </div>

      {/* Command Input Box */}
      <div className="bg-hack-dark/90 backdrop-blur-sm border border-hack-green/30 rounded-xl p-3 sm:p-4 shadow-2xl flex-shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <TerminalIcon className="text-hack-green" size={16} sm:size={18} />
          <span className="text-xs sm:text-sm font-mono text-gray-400">Command Input</span>
        </div>
        <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center">
          <span className="text-hack-green font-mono text-xs sm:text-sm whitespace-nowrap">PS C:\Users\shres&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={commandInput}
            onChange={(e) => setCommandInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSendCommand()
              } else if (e.key === 'Escape') {
                setCommandInput('')
              } else if (e.key === 'c' && e.ctrlKey) {
                // Ctrl+C - check if text is selected in terminal first
                if (terminalInstanceRef.current) {
                  const selection = terminalInstanceRef.current.getSelection()
                  if (selection && selection.length > 0) {
                    // Text is selected - copy it
                    e.preventDefault()
                    navigator.clipboard.writeText(selection).then(() => {
                      showToast('Copied to clipboard', 'success')
                    }).catch(() => {
                      // Fallback
                      const textArea = document.createElement('textarea')
                      textArea.value = selection
                      textArea.style.position = 'fixed'
                      textArea.style.opacity = '0'
                      document.body.appendChild(textArea)
                      textArea.select()
                      try {
                        document.execCommand('copy')
                        showToast('Copied to clipboard', 'success')
                      } catch (err) {
                        showToast('Failed to copy', 'error')
                      }
                      document.body.removeChild(textArea)
                    })
                    return
                  }
                }
                // No selection - send interrupt
                e.preventDefault()
                if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                  wsRef.current.send(JSON.stringify({
                    type: 'interrupt'
                  }))
                  if (terminalInstanceRef.current) {
                    terminalInstanceRef.current.write('\r\n^C\r\n')
                  }
                  setCommandInput('')
                }
              }
            }}
            placeholder="Type command and press Enter..."
            disabled={!isConnected}
            className="flex-1 bg-black/50 border border-white/10 hover:border-hack-green/50 focus:border-hack-green text-hack-green px-3 sm:px-4 py-2 rounded-lg font-mono text-xs sm:text-sm focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-600"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={handleSendCommand}
              disabled={!isConnected || !commandInput.trim()}
              className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 sm:px-4 py-2 rounded-lg font-mono text-xs sm:text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 flex-1 sm:flex-initial justify-center"
            >
              <span>Send</span>
            </button>
            <button
              onClick={() => {
                setCommandInput('')
                if (inputRef.current) {
                  inputRef.current.focus()
                }
              }}
              className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 px-3 py-2 rounded-lg font-mono text-xs transition-all flex items-center gap-2"
            >
              <span>Clear</span>
            </button>
          </div>
        </div>
      </div>

      {/* Terminal Display */}
      <div className="flex-1 bg-hack-dark/90 backdrop-blur-sm border border-hack-green/30 rounded-xl p-3 sm:p-4 shadow-2xl flex flex-col" style={{ minHeight: 0, height: '100%', overflow: 'hidden' }}>
        <div className="flex items-center justify-between mb-2 flex-shrink-0">
          <div className="flex items-center gap-2">
            <TerminalIcon className="text-hack-green" size={16} />
            <span className="text-xs sm:text-sm font-mono text-gray-400">Terminal Output</span>
          </div>
          <button
            onClick={handleCopySelected}
            className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 py-1.5 rounded-lg font-mono text-xs transition-all flex items-center gap-2"
            title="Copy selected text (Ctrl+C)"
          >
            <Copy size={14} />
            <span className="hidden sm:inline">Copy</span>
          </button>
        </div>
        <div 
          ref={terminalRef} 
          className="w-full bg-black rounded-lg flex-1"
          style={{ 
            padding: '8px',
            minHeight: '300px',
            height: '100%',
            width: '100%',
            position: 'relative',
            userSelect: 'text',
            WebkitUserSelect: 'text',
            MozUserSelect: 'text',
            msUserSelect: 'text'
          }}
        />
      </div>
    </div>
  )
}

export default TerminalPage

