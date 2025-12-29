import React, { useState, useRef, useEffect } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Database, 
  Filter, 
  Download, 
  Clock, 
  Home,
  CheckSquare,
  FileBarChart,
  Sparkles,
  LogOut,
  User,
  Settings,
  Building2,
  ScrollText,
  ChevronUp,
  Shield,
  MessageCircle,
  Users
} from 'lucide-react';
import aletheiaLogo from '../aletheia-logo.png';
import { useAuth } from '../contexts/AuthContext';

const Layout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, hasPermission } = useAuth();
  const isHome = location.pathname === '/';
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (isHome) {
    return <Outlet />;
  }

  const navItems = [
    { to: '/overview', icon: <LayoutDashboard size={20} />, label: 'Overview' },
    { to: '/audiences', icon: <Users size={20} />, label: 'Audiences' },
    { to: '/threads', icon: <MessageCircle size={20} />, label: 'Threads' },
    { to: '/quality', icon: <FileBarChart size={20} />, label: 'Quality Report' },
    { to: '/variables', icon: <Database size={20} />, label: 'Variable Explorer' },
    { to: '/filters', icon: <Filter size={20} />, label: 'Smart Filters' },
    { to: '/twin-transformer', icon: <Sparkles size={20} />, label: 'Twin Transformer' },
    { to: '/digital-insight', icon: <MessageCircle size={20} />, label: 'Dijital Insight' },
    { to: '/participant-data', icon: <Users size={20} />, label: 'Katılımcı Verileri' },
    { to: '/exports', icon: <Download size={20} />, label: 'Export' },
  ];

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col z-10 shadow-sm">
        <div className="p-5 border-b border-gray-100 flex flex-col items-center">
          <img src={aletheiaLogo} alt="Aletheia Logo" className="w-48 h-auto" />
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-4 py-3 rounded-xl transition-all font-medium ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 shadow-sm'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Bottom Actions */}
        <div className="p-4 space-y-3 border-t border-gray-100">
          <button
            onClick={() => navigate('/history')}
            className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors font-medium"
          >
            <Clock size={20} />
            <span>Previous Analyses</span>
          </button>
          
          <button
            onClick={() => navigate('/')}
            className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors font-medium"
          >
            <Home size={20} />
            <span>Upload New File</span>
          </button>
        </div>

        <div className="p-4 border-t border-gray-100">
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-xl border border-blue-100">
            <div className="flex items-center space-x-2 mb-2">
              <CheckSquare size={14} className="text-blue-600" />
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">AI Powered</span>
            </div>
            <p className="text-sm text-gray-700 font-medium">Aletheia</p>
            <p className="text-xs text-gray-500 mt-1">Smart filter suggestions</p>
          </div>
        </div>

        {/* User Profile Menu */}
        {user && (
          <div className="p-4 border-t border-gray-100 relative" ref={profileMenuRef}>
            {/* Profile Button - Clickable */}
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="w-full flex items-center space-x-3 p-3 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer group"
            >
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm shadow-sm">
                {user.name?.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-gray-900 truncate">{user.name || 'User'}</p>
                <p className="text-xs text-gray-500 truncate">{user.org_name || 'No Organization'}</p>
              </div>
              <ChevronUp 
                size={18} 
                className={`text-gray-400 transition-transform duration-200 ${showProfileMenu ? 'rotate-180' : ''}`}
              />
            </button>

            {/* Dropdown Menu */}
            {showProfileMenu && (
              <div className="absolute bottom-full left-4 right-4 mb-2 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden z-50">
                {/* Profile Info Header */}
                <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100">
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-md">
                      {user.name?.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{user.name || 'User'}</p>
                      <p className="text-xs text-gray-600 truncate">{user.email}</p>
                      <div className="flex items-center space-x-1 mt-1">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                          {user.role?.replace('_', ' ') || 'User'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Organization Info */}
                <div className="p-3 border-b border-gray-100">
                  <div className="flex items-center space-x-3 text-sm text-gray-600">
                    <Building2 size={16} className="text-gray-400" />
                    <div>
                      <p className="font-medium text-gray-900">{user.org_name || 'No Organization'}</p>
                      <p className="text-xs text-gray-500">Organization</p>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="p-2">
                  {/* Admin Page - Only for users with users:manage permission */}
                  {hasPermission('users:manage') && (
                    <button
                      onClick={() => {
                        navigate('/admin');
                        setShowProfileMenu(false);
                      }}
                      className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-colors text-sm font-medium"
                    >
                      <Settings size={18} />
                      <span>User Management</span>
                    </button>
                  )}

                  {/* Audit Logs - Only for users with audit:read permission */}
                  {hasPermission('audit:read') && (
                    <button
                      onClick={() => {
                        navigate('/audit-logs');
                        setShowProfileMenu(false);
                      }}
                      className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors text-sm font-medium"
                    >
                      <ScrollText size={18} />
                      <span>Audit Logs</span>
                    </button>
                  )}

                  {/* Super Admin - Only for super_admin role */}
                  {user.role === 'super_admin' && (
                    <button
                      onClick={() => {
                        navigate('/super-admin');
                        setShowProfileMenu(false);
                      }}
                      className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-gray-700 hover:bg-amber-50 hover:text-amber-700 transition-colors text-sm font-medium"
                    >
                      <Shield size={18} />
                      <span>Super Admin</span>
                    </button>
                  )}

                  {/* Divider */}
                  <div className="my-2 border-t border-gray-100"></div>

                  {/* Sign Out */}
                  <button
                    onClick={() => {
                      handleLogout();
                      setShowProfileMenu(false);
                    }}
                    className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-red-600 hover:bg-red-50 transition-colors text-sm font-medium"
                  >
                    <LogOut size={18} />
                    <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-gray-50/50">
        <div className="max-w-7xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
