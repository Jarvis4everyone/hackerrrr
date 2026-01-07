import { createContext, useContext, useState, useEffect, useRef } from 'react'

const StreamingContext = createContext()

export const useStreaming = () => {
  const context = useContext(StreamingContext)
  if (!context) {
    throw new Error('useStreaming must be used within StreamingProvider')
  }
  return context
}

export const StreamingProvider = ({ children }) => {
  const [activeStreams, setActiveStreams] = useState({
    camera: false,
    microphone: false,
    screen: false,
    terminal: false
  })
  
  const stopCallbacksRef = useRef({
    camera: null,
    microphone: null,
    screen: null,
    terminal: null
  })

  // Register stop callback for a stream type
  const registerStopCallback = (streamType, callback) => {
    stopCallbacksRef.current[streamType] = callback
  }

  // Unregister stop callback
  const unregisterStopCallback = (streamType) => {
    stopCallbacksRef.current[streamType] = null
  }

  // Set stream active state
  const setStreamActive = (streamType, isActive) => {
    setActiveStreams(prev => ({
      ...prev,
      [streamType]: isActive
    }))
  }

  // Check if any stream is active
  const hasActiveStreams = () => {
    return Object.values(activeStreams).some(active => active === true)
  }

  // Stop all active streams
  const stopAllStreams = async () => {
    const promises = []
    
    if (activeStreams.camera && stopCallbacksRef.current.camera) {
      promises.push(Promise.resolve(stopCallbacksRef.current.camera()))
    }
    if (activeStreams.microphone && stopCallbacksRef.current.microphone) {
      promises.push(Promise.resolve(stopCallbacksRef.current.microphone()))
    }
    if (activeStreams.screen && stopCallbacksRef.current.screen) {
      promises.push(Promise.resolve(stopCallbacksRef.current.screen()))
    }
    if (activeStreams.terminal && stopCallbacksRef.current.terminal) {
      promises.push(Promise.resolve(stopCallbacksRef.current.terminal()))
    }
    
    await Promise.all(promises)
    
    // Reset all states
    setActiveStreams({
      camera: false,
      microphone: false,
      screen: false,
      terminal: false
    })
  }

  // Handle beforeunload event
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasActiveStreams()) {
        // Stop all streams synchronously
        stopAllStreams()
        
        // Show browser's default confirmation dialog
        e.preventDefault()
        e.returnValue = 'You have active streams or terminal sessions. They will be stopped before you leave.'
        return e.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [activeStreams])

  // Handle route changes (React Router)
  useEffect(() => {
    const handleRouteChange = () => {
      if (hasActiveStreams()) {
        // Stop all streams before route change
        stopAllStreams()
      }
    }

    // This will be called when component unmounts or route changes
    return () => {
      handleRouteChange()
    }
  }, [activeStreams])

  const value = {
    activeStreams,
    setStreamActive,
    hasActiveStreams,
    stopAllStreams,
    registerStopCallback,
    unregisterStopCallback
  }

  return (
    <StreamingContext.Provider value={value}>
      {children}
    </StreamingContext.Provider>
  )
}

