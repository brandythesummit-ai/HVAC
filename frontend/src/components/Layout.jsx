import { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  MapPin,
  UserCheck,
  GitBranch,
  Settings,
  Menu,
  X,
  Building2,
  ChevronLeft
} from 'lucide-react';
import HealthIndicator from './health/HealthIndicator';

const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  const navItems = [
    { to: '/counties', icon: MapPin, label: 'Counties' },
    { to: '/leads', icon: UserCheck, label: 'Lead Review' },
    { to: '/pipeline', icon: GitBranch, label: 'Pipeline' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  const getPageTitle = () => {
    const path = location.pathname;
    if (path.includes('counties')) return 'Counties';
    if (path.includes('leads')) return 'Lead Review';
    if (path.includes('pipeline')) return 'Summit.ai Pipeline';
    if (path.includes('settings')) return 'Settings';
    return 'Dashboard';
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-gray-900 transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-800">
          <div className={`flex items-center space-x-3 ${!sidebarOpen && 'justify-center w-full'}`}>
            <div className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-lg">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            {sidebarOpen && (
              <div className="animate-fade-in">
                <h1 className="text-lg font-semibold text-white">HVAC Lead Gen</h1>
                <p className="text-xs text-gray-400">By The Summit.AI</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center px-3 py-3 rounded-lg text-sm font-medium transition-all duration-150 group ${
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                } ${!sidebarOpen && 'justify-center'}`
              }
            >
              <item.icon className={`w-5 h-5 ${sidebarOpen && 'mr-3'}`} />
              {sidebarOpen && <span className="animate-fade-in">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Collapse Button */}
        <div className="p-4 border-t border-gray-800">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className={`flex items-center justify-center w-full px-3 py-2 text-sm font-medium text-gray-400 transition-all duration-150 rounded-lg hover:bg-gray-800 hover:text-white ${
              !sidebarOpen && 'px-0'
            }`}
          >
            <ChevronLeft
              className={`w-5 h-5 transition-transform duration-300 ${
                !sidebarOpen && 'rotate-180'
              }`}
            />
            {sidebarOpen && <span className="ml-2 animate-fade-in">Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${
        sidebarOpen ? 'ml-64' : 'ml-20'
      }`}>
        {/* Top Bar */}
        <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-gray-200 shadow-sm">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">{getPageTitle()}</h2>
          </div>

          <div className="flex items-center space-x-4">
            <HealthIndicator />
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-y-auto custom-scrollbar">
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-900 bg-opacity-50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}
    </div>
  );
};

export default Layout;
