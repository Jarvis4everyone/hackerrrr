import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { StreamingProvider } from './contexts/StreamingContext'
import { ToastProvider } from './components/ToastContainer'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import PCs from './pages/PCs'
import Scripts from './pages/Scripts'
import Logs from './pages/Logs'
import Directory from './pages/Directory'
import Terminal from './pages/Terminal'
import Camera from './pages/Camera'
import Microphone from './pages/Microphone'
import Screen from './pages/Screen'
import Code from './pages/Code'

function App() {
  return (
    <AuthProvider>
      <StreamingProvider>
      <ToastProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/pcs" element={<PCs />} />
                      <Route path="/scripts" element={<Scripts />} />
                      <Route path="/code" element={<Code />} />
                        <Route path="/directory" element={<Directory />} />
                        <Route path="/terminal" element={<Terminal />} />
                      <Route path="/camera" element={<Camera />} />
                      <Route path="/microphone" element={<Microphone />} />
                      <Route path="/screen" element={<Screen />} />
                      <Route path="/logs" element={<Logs />} />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </Router>
      </ToastProvider>
      </StreamingProvider>
    </AuthProvider>
  )
}

export default App
