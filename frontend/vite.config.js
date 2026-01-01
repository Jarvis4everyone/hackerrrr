import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get API URL from environment or default to localhost
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Listen on all interfaces for remote access
    port: 3000,
    hmr: {
      // Use the public IP or hostname if accessing remotely
      // Set VITE_HMR_HOST environment variable to override
      host: process.env.VITE_HMR_HOST || process.env.HOST || 'localhost',
      clientPort: parseInt(process.env.VITE_HMR_PORT || process.env.PORT || '3000'),
      protocol: process.env.VITE_HMR_PROTOCOL || 'ws'
    },
    proxy: {
      '/api': {
        target: API_URL,
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: API_URL.replace('http://', 'ws://').replace('https://', 'wss://'),
        ws: true,
        changeOrigin: true
      }
    }
  }
})

