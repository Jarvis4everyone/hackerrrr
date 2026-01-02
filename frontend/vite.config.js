import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Function to read Serverurl from parent .env file
function getServerUrlFromParentEnv() {
  try {
    const parentEnvPath = resolve(__dirname, '..', '.env')
    const envContent = readFileSync(parentEnvPath, 'utf-8')
    
    for (const line of envContent.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      
      // Handle both "Serverurl = VALUE" and "Serverurl=VALUE" formats
      if (trimmed.startsWith('Serverurl') || trimmed.startsWith('SERVER_URL')) {
        const match = trimmed.match(/^Serverurl\s*=\s*(.+)$/i)
        if (match) {
          let value = match[1].trim()
          // Remove quotes if present
          value = value.replace(/^["']|["']$/g, '')
          // Remove trailing slash if present
          value = value.replace(/\/$/, '')
          return value
        }
      }
    }
  } catch (error) {
    // If parent .env doesn't exist or can't be read, return null
    console.warn('Could not read parent .env file:', error.message)
  }
  return null
}

export default defineConfig(({ mode }) => {
  // Load env file from frontend directory first
  const env = loadEnv(mode, __dirname, '')
  
  // Try to get API URL from parent .env file's Serverurl
  const parentServerUrl = getServerUrlFromParentEnv()
  
  // Get API URL from environment variable (frontend .env takes precedence)
  const apiUrl = env.VITE_API_URL || parentServerUrl || 'http://localhost:8000'
  
  // Convert HTTP URL to WebSocket URL
  const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://')
  
  return {
  plugins: [react()],
  server: {
      port: parseInt(process.env.PORT || '3000'),
    proxy: {
      '/api': {
          target: apiUrl,
        changeOrigin: true
      },
      '/ws': {
          target: wsUrl,
        ws: true
        }
      }
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false
    }
  }
})

