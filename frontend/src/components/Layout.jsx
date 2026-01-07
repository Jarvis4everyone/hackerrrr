import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { 
  LayoutDashboard, 
  Monitor, 
  FileCode, 
  FileText,
  Folder,
  Terminal,
  Menu,
  X,
  LogOut
} from 'lucide-react'

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const { logout, username } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/pcs', icon: Monitor, label: 'PCs' },
    { path: '/scripts', icon: FileCode, label: 'Scripts' },
    { path: '/logs', icon: FileText, label: 'Logs' },
    { path: '/directory', icon: Folder, label: 'Directory' },
    { path: '/terminal', icon: Terminal, label: 'Terminal' },
  ]

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-hack-darker flex">
      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-hack-dark border-r border-hack-green/20
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex flex-col p-6 border-b border-hack-green/20">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-xl font-bold text-hack-green animate-glow">
              <span className="cursor">X1</span>
            </h1>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-hack-green hover:text-white"
            >
              <X size={24} />
            </button>
          </div>
          <p className="text-xs text-white/40 font-mono">
            created by real life tony stark
          </p>
        </div>
        
        <nav className="p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.path)
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-all duration-200
                  ${active 
                    ? 'bg-hack-green/20 text-hack-green border-l-2 border-hack-green' 
                    : 'text-gray-400 hover:bg-hack-gray hover:text-hack-green'
                  }
                `}
              >
                <Icon size={20} />
                <span className="font-mono">{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="bg-hack-dark border-b border-hack-green/20 px-4 py-4 lg:px-6">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden text-hack-green hover:text-white"
            >
              <Menu size={24} />
            </button>
            <div className="flex-1 text-center lg:text-left">
              <h2 className="text-lg font-mono text-hack-green">
                {navItems.find(item => isActive(item.path))?.label || 'Control Panel'}
              </h2>
            </div>
            <div className="hidden lg:flex items-center gap-4">
              {username && (
                <span className="text-sm text-white/70 font-mono">{username}</span>
              )}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-1.5 bg-hack-green/10 hover:bg-hack-green/20 border border-hack-green/30 text-hack-green rounded-lg transition-all font-mono text-sm"
                title="Logout"
              >
                <LogOut size={16} />
                <span>Logout</span>
              </button>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-hack-green rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-400 font-mono">ONLINE</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-6 overflow-auto">
          {children}
        </main>
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}

export default Layout

