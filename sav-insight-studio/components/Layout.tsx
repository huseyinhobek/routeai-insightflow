import React from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Database, 
  Filter, 
  Download, 
  BarChart2, 
  Clock, 
  Home,
  CheckSquare,
  FileBarChart
} from 'lucide-react';

const Layout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === '/';

  if (isHome) {
    return <Outlet />;
  }

  const navItems = [
    { to: '/overview', icon: <LayoutDashboard size={20} />, label: 'Genel Bakış' },
    { to: '/quality', icon: <FileBarChart size={20} />, label: 'Kalite Raporu' },
    { to: '/variables', icon: <Database size={20} />, label: 'Değişken Keşfi' },
    { to: '/filters', icon: <Filter size={20} />, label: 'Akıllı Filtreler' },
    { to: '/exports', icon: <Download size={20} />, label: 'Dışa Aktar' },
  ];

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col z-10 shadow-sm">
        <div className="p-6 border-b border-gray-100 flex items-center space-x-3">
          <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-lg shadow-lg shadow-blue-200">
            <BarChart2 className="text-white" size={20} />
          </div>
          <span className="font-bold text-gray-800 text-lg tracking-tight">SAV Insight</span>
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
            <span>Önceki Analizler</span>
          </button>
          
          <button
            onClick={() => navigate('/')}
            className="w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors font-medium"
          >
            <Home size={20} />
            <span>Yeni Dosya Yükle</span>
          </button>
        </div>

        <div className="p-4 border-t border-gray-100">
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-xl border border-blue-100">
            <div className="flex items-center space-x-2 mb-2">
              <CheckSquare size={14} className="text-blue-600" />
              <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">AI Destekli</span>
            </div>
            <p className="text-sm text-gray-700 font-medium">Gemini 2.5 Flash</p>
            <p className="text-xs text-gray-500 mt-1">Akıllı filtre önerileri için</p>
          </div>
        </div>
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
