import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Activity, 
  Monitor, 
  FileCode, 
  Zap, 
  FileText,
  ArrowRight,
  Terminal,
  Folder
} from 'lucide-react'
import { getHealth, getPCs, getScripts, getExecutions } from '../services/api'

const Dashboard = () => {
  const [stats, setStats] = useState({
    connected: 0,
    total: 0,
    scripts: 0,
    executions: 0
  })
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [healthData, pcsData, scriptsData, executionsData] = await Promise.all([
        getHealth(),
        getPCs(),
        getScripts(),
        getExecutions(10)
      ])
      
      setHealth(healthData)
      setStats({
        connected: pcsData.connected || 0,
        total: pcsData.total || 0,
        scripts: scriptsData.total || 0,
        executions: executionsData.total || 0
      })
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const statCards = [
    {
      icon: Monitor,
      label: 'Connected PCs',
      value: stats.connected,
      valueColor: 'text-green-400'
    },
    {
      icon: Activity,
      label: 'Total PCs',
      value: stats.total,
      valueColor: 'text-white'
    },
    {
      icon: FileCode,
      label: 'Available Scripts',
      value: stats.scripts,
      valueColor: 'text-yellow-400'
    },
    {
      icon: Zap,
      label: 'Recent Executions',
      value: stats.executions,
      valueColor: 'text-hack-green'
    },
  ]

  const routes = [
    {
      path: '/pcs',
      icon: Monitor,
      title: 'PCs',
      description: 'View and manage all connected devices'
    },
    {
      path: '/scripts',
      icon: FileCode,
      title: 'Scripts',
      description: 'Execute scripts on connected devices'
    },
    {
      path: '/directory',
      icon: Folder,
      title: 'Directory',
      description: 'Browse and download files from PCs'
    },
    {
      path: '/terminal',
      icon: Terminal,
      title: 'Terminal',
      description: 'Remote terminal access to PCs'
    },
    {
      path: '/logs',
      icon: FileText,
      title: 'Logs',
      description: 'View script execution logs and results'
    }
  ]

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Hero Section - Real Life Tony Stark */}
      <div className="bg-hack-dark/90 backdrop-blur-sm border border-hack-green/30 rounded-xl p-6 sm:p-8 shadow-2xl text-center">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-hack-green font-mono mb-2 animate-glow">
          <span className="cursor">X1</span>
        </h1>
        <p className="text-xl sm:text-2xl md:text-3xl text-white/90 font-mono mb-1">
          created by
        </p>
        <p className="text-2xl sm:text-3xl md:text-4xl font-bold text-hack-green font-mono tracking-wider">
          REAL LIFE TONY STARK
        </p>
        <div className="mt-4 flex items-center justify-center gap-2">
          <div className="w-2 h-2 bg-hack-green rounded-full animate-pulse"></div>
          <span className="text-hack-green/70 font-mono text-sm">SYSTEM OPERATIONAL</span>
          <div className="w-2 h-2 bg-hack-green rounded-full animate-pulse"></div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {statCards.map((stat, index) => {
          const Icon = stat.icon
          return (
            <div
              key={index}
              className="bg-hack-dark border border-hack-green/20 rounded-lg p-4 sm:p-6 hover:border-hack-green/40 transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-xs sm:text-sm font-mono mb-2">{stat.label}</p>
                  <p className={`text-2xl sm:text-3xl font-bold ${stat.valueColor}`}>
                    {loading ? '...' : stat.value}
                  </p>
                </div>
                <Icon className="text-white opacity-50" size={32} />
              </div>
            </div>
          )
        })}
      </div>

      {/* System Status */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-4 sm:p-6">
        <h3 className="text-hack-green font-mono text-base sm:text-lg mb-4 flex items-center gap-2">
          <Activity size={20} />
          System Status
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="flex justify-between items-center p-3 bg-black/30 rounded border border-white/10">
            <span className="text-gray-400 font-mono text-sm">Status</span>
            <span className="text-hack-green font-mono font-bold">
              {health?.status === 'healthy' ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
          <div className="flex justify-between items-center p-3 bg-black/30 rounded border border-white/10">
            <span className="text-gray-400 font-mono text-sm">Connected PCs</span>
            <span className="text-hack-green font-mono font-bold">{health?.connected_pcs || 0}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-black/30 rounded border border-white/10">
            <span className="text-gray-400 font-mono text-sm">Last Update</span>
            <span className="text-gray-500 font-mono text-xs">
              {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* All Routes & Functionality */}
      <div className="bg-hack-dark border border-hack-green/20 rounded-lg p-4 sm:p-6">
        <h3 className="text-hack-green font-mono text-base sm:text-lg mb-6 flex items-center gap-2">
          <Terminal size={20} />
          System Modules
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((route, index) => {
            const Icon = route.icon
            return (
              <Link
                key={index}
                to={route.path}
                className="group bg-black/50 hover:bg-black/70 border border-white/10 hover:border-hack-green/50 rounded-lg p-4 sm:p-5 transition-all"
              >
                <div className="flex items-start justify-between mb-3">
                  <Icon className="text-white" size={24} />
                  <ArrowRight className="text-white/30 group-hover:text-hack-green group-hover:translate-x-1 transition-all" size={20} />
                </div>
                <h4 className="text-white font-mono font-bold text-lg mb-2 group-hover:text-hack-green transition-colors">
                  {route.title}
                </h4>
                <p className="text-white/50 font-mono text-sm">
                  {route.description}
                </p>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default Dashboard

