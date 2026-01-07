import axios from 'axios'

// Use environment variable for API URL
// In production, if VITE_API_URL is not set, try to auto-detect from current hostname
let API_BASE_URL = import.meta.env.VITE_API_URL

if (!API_BASE_URL) {
  if (import.meta.env.PROD) {
    // In production, try to construct backend URL from current host
    const hostname = window.location.hostname
    // Handle Render.com URLs: hackerrrr-frontend.onrender.com -> hackerrrr-backend.onrender.com
    if (hostname.includes('onrender.com')) {
      const parts = hostname.split('.')
      if (parts[0] === 'hackerrrr-frontend') {
        API_BASE_URL = `https://hackerrrr-backend.${parts.slice(1).join('.')}`
      } else {
        // Try to replace frontend with backend in subdomain
        const subdomain = parts[0]
        if (subdomain.includes('frontend')) {
          API_BASE_URL = `https://${subdomain.replace('frontend', 'backend')}.${parts.slice(1).join('.')}`
        } else {
          API_BASE_URL = 'https://hackerrrr-backend.onrender.com' // Fallback
        }
      }
    } else {
      // For other domains, try same origin
      API_BASE_URL = ''
    }
  } else {
    // Development fallback
    API_BASE_URL = 'http://localhost:8000'
  }
}

// Remove trailing slash if present
API_BASE_URL = API_BASE_URL.replace(/\/$/, '')

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors (unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid, clear it
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// PCs API
export const getPCs = async (connectedOnly = false) => {
  const response = await api.get('/api/pcs', {
    params: { connected_only: connectedOnly }
  })
  return response.data
}

export const getPC = async (pcId) => {
  const response = await api.get(`/api/pcs/${pcId}`)
  return response.data
}

export const deletePC = async (pcId) => {
  const response = await api.delete(`/api/pcs/${pcId}`)
  return response.data
}

export const checkConnection = async (pcId) => {
  const response = await api.get(`/api/pcs/${pcId}/connected`)
  return response.data
}

// Scripts API
export const getScripts = async () => {
  const response = await api.get('/api/scripts')
  return response.data
}

export const syncScripts = async () => {
  const response = await api.get('/api/scripts/sync')
  return response.data
}

export const sendScript = async (pcId, scriptName, serverUrl = null, scriptParams = null) => {
  const response = await api.post('/api/scripts/send', {
    pc_id: pcId,
    script_name: scriptName,
    server_url: serverUrl,
    script_params: scriptParams
  })
  return response.data
}

export const broadcastScript = async (scriptName, serverUrl = null, scriptParams = null) => {
  const response = await api.post('/api/scripts/broadcast', {
    script_name: scriptName,
    server_url: serverUrl,
    script_params: scriptParams
  })
  return response.data
}

// Executions API
export const getExecutions = async (limit = 100) => {
  const response = await api.get('/api/executions', {
    params: { limit }
  })
  return response.data
}

export const getPCExecutions = async (pcId, limit = 50) => {
  const response = await api.get(`/api/executions/pc/${pcId}`, {
    params: { limit }
  })
  return response.data
}

export const getScriptExecutions = async (scriptName, limit = 50) => {
  const response = await api.get(`/api/executions/script/${scriptName}`, {
    params: { limit }
  })
  return response.data
}

// Health API
export const getHealth = async () => {
  const response = await api.get('/api/health')
  return response.data
}

// Logs API
export const getLogs = async (limit = 200, pcId = null, scriptName = null, logLevel = null) => {
  const response = await api.get('/api/logs', {
    params: {
      limit,
      pc_id: pcId,
      script_name: scriptName,
      log_level: logLevel
    }
  })
  return response.data
}

export const getLog = async (logId) => {
  const response = await api.get(`/api/logs/${logId}`)
  return response.data
}

export const getPCLogs = async (pcId, limit = 100) => {
  const response = await api.get(`/api/logs/pc/${pcId}`, {
    params: { limit }
  })
  return response.data
}

export const getScriptLogs = async (scriptName, limit = 100) => {
  const response = await api.get(`/api/logs/script/${scriptName}`, {
    params: { limit }
  })
  return response.data
}

export const getExecutionLogs = async (executionId) => {
  const response = await api.get(`/api/logs/execution/${executionId}`)
  return response.data
}

export const createLog = async (logData) => {
  const response = await api.post('/api/logs', logData)
  return response.data
}

// Files API
export const requestFileDownload = async (pcId, filePath) => {
  const response = await api.post('/api/files/download', null, {
    params: {
      pc_id: pcId,
      file_path: filePath
    }
  })
  return response.data
}

export const listFiles = async (pcId = null) => {
  const response = await api.get('/api/files', {
    params: pcId ? { pc_id: pcId } : {}
  })
  return response.data
}

export const downloadFile = async (fileId, pcId) => {
  const response = await api.get(`/api/files/${fileId}`, {
    params: { pc_id: pcId },
    responseType: 'blob'
  })
  return response
}

export const deleteFile = async (fileId, pcId) => {
  const response = await api.delete(`/api/files/${fileId}`, {
    params: { pc_id: pcId }
  })
  return response.data
}

// Terminal API
export const startTerminalSession = async (pcId) => {
  const response = await api.post('/api/terminal/start', null, {
    params: { pc_id: pcId }
  })
  return response.data
}

export const stopTerminalSession = async (sessionId, pcId) => {
  const response = await api.post('/api/terminal/stop', null, {
    params: { session_id: sessionId, pc_id: pcId }
  })
  return response.data
}

export const getTerminalSession = async (sessionId) => {
  const response = await api.get(`/api/terminal/session/${sessionId}`)
  return response.data
}

// Auth API
export const login = async (username, password) => {
  const response = await api.post('/api/auth/login', {
    username,
    password
  })
  return response.data
}

export const logout = async () => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    try {
      await api.post('/api/auth/logout', {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } catch (error) {
      // Ignore errors on logout
    }
  }
  localStorage.removeItem('auth_token')
}

export const checkAuthStatus = async () => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return { authenticated: false }
  }
  try {
    const response = await api.get('/api/auth/status', {
      headers: { Authorization: `Bearer ${token}` }
    })
    return response.data
  } catch (error) {
    return { authenticated: false }
  }
}

export const verifyToken = async () => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return false
  }
  try {
    await api.get('/api/auth/verify', {
      headers: { Authorization: `Bearer ${token}` }
    })
    return true
  } catch (error) {
    return false
  }
}

// Helper function to get WebSocket URL
export const getWebSocketUrl = (path = '') => {
  // Determine the base URL for WebSocket connections
  let wsBaseUrl = API_BASE_URL
  
  // If API_BASE_URL is empty (same origin), use current location
  if (!wsBaseUrl) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${path}`
  }
  
  // Convert HTTP/HTTPS URL to WS/WSS
  const protocol = wsBaseUrl.startsWith('https') ? 'wss:' : 'ws:'
  const host = wsBaseUrl.replace(/^https?:\/\//, '')
  
  return `${protocol}//${host}${path}`
}

export default api

