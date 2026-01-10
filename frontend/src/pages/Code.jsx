import { useEffect, useState } from 'react'
import { Code2, Send, Loader2, Terminal, Package } from 'lucide-react'
import { executeCode, getPCs } from '../services/api'
import { useToast } from '../components/ToastContainer'

const Code = () => {
  const [pcs, setPCs] = useState([])
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [selectedPC, setSelectedPC] = useState('')
  const [code, setCode] = useState('')
  const [requirements, setRequirements] = useState('')
  const { showToast } = useToast()

  useEffect(() => {
    loadPCs()
  }, [])

  const loadPCs = async () => {
    try {
      const pcsData = await getPCs(true) // Only connected PCs
      setPCs(pcsData.pcs || [])
    } catch (error) {
      console.error('Error loading PCs:', error)
      showToast('Failed to load PCs', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleExecute = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'error')
      return
    }

    if (!code || !code.trim()) {
      showToast('Please enter Python code to execute', 'error')
      return
    }

    setSending(true)
    try {
      const result = await executeCode(
        selectedPC,
        code.trim(),
        requirements.trim() || null
      )
      
      showToast(
        `Code sent to PC successfully! ${result.has_requirements ? 'Requirements will be installed first.' : ''}`,
        'success'
      )
      
      // Clear form after successful send
      setCode('')
      setRequirements('')
    } catch (error) {
      console.error('Error executing code:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to execute code'
      showToast(errorMessage, 'error')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-hack-green animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Code2 className="w-8 h-8 text-hack-green" />
        <div>
          <h1 className="text-2xl font-bold text-white font-mono">Code Execution</h1>
          <p className="text-gray-400 text-sm mt-1">
            Execute custom Python code on target PCs with automatic dependency installation
          </p>
        </div>
      </div>

      {/* PC Selection */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <label className="block text-sm font-medium text-hack-green mb-2 font-mono">
          <Terminal className="inline w-4 h-4 mr-2" />
          Select Target PC
        </label>
        <select
          value={selectedPC}
          onChange={(e) => setSelectedPC(e.target.value)}
          className="w-full bg-hack-darker border border-hack-green/30 text-white rounded-lg px-4 py-2 focus:outline-none focus:border-hack-green font-mono"
          disabled={sending}
        >
          <option value="">-- Select a PC --</option>
          {pcs.map((pc) => (
            <option key={pc.id} value={pc.id}>
              {pc.name} {pc.connected ? '(Online)' : '(Offline)'}
            </option>
          ))}
        </select>
        {pcs.length === 0 && (
          <p className="text-gray-400 text-sm mt-2">No connected PCs available</p>
        )}
      </div>

      {/* Requirements Section */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <label className="block text-sm font-medium text-hack-green mb-2 font-mono">
          <Package className="inline w-4 h-4 mr-2" />
          Requirements (Optional)
        </label>
        <p className="text-gray-400 text-xs mb-3">
          Enter pip install commands (e.g., "pip install pyqt5" or "pip install requests numpy")
        </p>
        <textarea
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
          placeholder="pip install pyqt5&#10;pip install requests"
          className="w-full bg-hack-darker border border-hack-green/30 text-white rounded-lg px-4 py-3 focus:outline-none focus:border-hack-green font-mono text-sm"
          rows={3}
          disabled={sending}
        />
      </div>

      {/* Code Editor */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-6">
        <label className="block text-sm font-medium text-hack-green mb-2 font-mono">
          <Code2 className="inline w-4 h-4 mr-2" />
          Python Code
        </label>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="# Enter your Python code here&#10;# Example:&#10;import sys&#10;print('Hello from target PC!')&#10;print(f'Python version: {sys.version}')"
          className="w-full bg-hack-darker border border-hack-green/30 text-white rounded-lg px-4 py-3 focus:outline-none focus:border-hack-green font-mono text-sm"
          rows={20}
          disabled={sending}
          style={{ fontFamily: 'monospace' }}
        />
        <p className="text-gray-400 text-xs mt-2">
          The code will be executed on the target PC. All output will be captured and sent to the server.
        </p>
      </div>

      {/* Send Button */}
      <div className="flex justify-end">
        <button
          onClick={handleExecute}
          disabled={!selectedPC || !code.trim() || sending}
          className="flex items-center gap-2 px-6 py-3 bg-hack-green hover:bg-hack-green/80 text-black font-bold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-mono"
        >
          {sending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Sending...</span>
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              <span>Execute Code</span>
            </>
          )}
        </button>
      </div>

      {/* Info Box */}
      <div className="bg-hack-green/10 border border-hack-green/30 rounded-lg p-4">
        <h3 className="text-hack-green font-bold mb-2 font-mono">How it works:</h3>
        <ul className="text-gray-300 text-sm space-y-1 list-disc list-inside">
          <li>Select a target PC from the dropdown</li>
          <li>Optionally enter pip install commands in the requirements field</li>
          <li>Paste or write your Python code in the code editor</li>
          <li>Click "Execute Code" to send and run the code on the target PC</li>
          <li>Requirements will be installed first (if provided), then your code will execute</li>
          <li>All output (print statements, errors) will be captured and sent to the server</li>
        </ul>
      </div>
    </div>
  )
}

export default Code

