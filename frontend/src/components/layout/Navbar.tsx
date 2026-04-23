import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Briefcase, MessageSquare, Bot, PlusCircle, Search, LogIn, LogOut, LayoutDashboard, User, Settings, Upload, FileText, List, X } from 'lucide-react';
import api from '../../lib/axios';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isLoggedIn = !!localStorage.getItem('access_token');
  const [profile, setProfile] = useState<any>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchProfile = () => {
      if (isLoggedIn) {
        api.get('/users/profile/')
          .then(res => {
            setProfile(res.data);
          })
          .catch(err => console.error('Failed to fetch profile', err));
      }
    };

    // Only fetch on initial mount if not already loaded
    fetchProfile();

    window.addEventListener('profileUpdated', fetchProfile);
    return () => window.removeEventListener('profileUpdated', fetchProfile);
  }, []); // Run ONLY once on mount to prevent calls on every route change

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsDropdownOpen(false);
    navigate('/');
  };

  const navLinks = [
    { name: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { name: 'Jobs', path: '/jobs', icon: <Briefcase size={18} /> },
    { name: 'Messages', path: '/messages', icon: <MessageSquare size={18} /> },
    { name: 'SeekBot', path: '/seekbot', icon: <Bot size={18} /> },
    { name: 'Post Job', path: '/post-job', icon: <PlusCircle size={18} /> },
  ];

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <nav className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 sticky top-0 z-50">
      <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-12">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex-shrink-0">
              <span className="text-xl font-bold text-zinc-900 dark:text-zinc-50">JobSeek</span>
            </Link>
            
            <div className="hidden md:block">
              <div className="flex items-center space-x-6">
                {navLinks.map((link) => {
                  const isActive = location.pathname.startsWith(link.path);
                  return (
                    <Link
                      key={link.name}
                      to={link.path}
                      className={`flex items-center gap-2 text-sm font-medium transition-colors ${
                        isActive
                          ? 'text-zinc-900 dark:text-zinc-50'
                          : 'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50'
                      }`}
                    >
                      {link.icon}
                      {link.name}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 sm:gap-6">
            <button className="text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50">
              <Search size={20} />
            </button>
            
            {isLoggedIn ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-900 bg-zinc-100 rounded-md hover:bg-zinc-200 dark:text-zinc-50 dark:bg-zinc-800 dark:hover:bg-zinc-700 transition-colors"
                >
                  {profile?.profile_picture ? (
                    <img 
                      src={
                        profile.profile_picture.startsWith('http') 
                          ? profile.profile_picture 
                          : profile.profile_picture.startsWith('/media/')
                            ? `http://127.0.0.1:8000${profile.profile_picture}`
                            : `http://127.0.0.1:8000/media/${profile.profile_picture.startsWith('/') ? profile.profile_picture.substring(1) : profile.profile_picture}`
                      } 
                      alt="Profile" 
                      className="w-5 h-5 rounded-full object-cover" 
                    />
                  ) : (
                    <User size={16} />
                  )}
                  <span className="hidden sm:inline">Profile</span>
                </button>

                {isDropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg overflow-hidden py-1">
                    <Link 
                      to="/profile" 
                      onClick={() => setIsDropdownOpen(false)}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
                    >
                      <Settings size={16} />
                      Profile Settings
                    </Link>
                    
                    {profile?.user_type === 'poster' && (
                      <Link
                        to="/my-jobs"
                        onClick={() => setIsDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
                      >
                        <List size={16} />
                        My Job Postings
                      </Link>
                    )}
                    
                    {profile?.resume ? (
                      <Link 
                        to="/resume" 
                        onClick={() => setIsDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
                      >
                        <FileText size={16} />
                        View Resume
                      </Link>
                    ) : (
                      <Link 
                        to="/resume" 
                        onClick={() => setIsDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
                      >
                        <Upload size={16} />
                        Upload Resume
                      </Link>
                    )}
                    
                    <div className="h-px bg-zinc-200 dark:bg-zinc-800 my-1"></div>
                    
                    <button 
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 text-left"
                    >
                      <LogOut size={16} />
                      Log Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => navigate('/login')}
                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-900 bg-zinc-100 rounded-md hover:bg-zinc-200 dark:text-zinc-50 dark:bg-zinc-800 dark:hover:bg-zinc-700 transition-colors"
              >
                <LogIn size={16} />
                <span>Sign in</span>
              </button>
            )}

            {/* Mobile Menu Button */}
            <button 
              className="md:hidden p-2 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-50"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X size={24} /> : <List size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Overlay */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-16 left-0 w-full bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 shadow-xl z-40 animate-in slide-in-from-top-2 duration-200">
          <div className="px-4 py-6 space-y-4">
            {navLinks.map((link) => {
              const isActive = location.pathname.startsWith(link.path);
              return (
                <Link
                  key={link.name}
                  to={link.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`flex items-center gap-4 px-4 py-3 rounded-xl text-base font-medium transition-all ${
                    isActive
                      ? 'bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900 shadow-lg shadow-zinc-900/10'
                      : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50'
                  }`}
                >
                  <span className={isActive ? 'text-white dark:text-zinc-900' : 'text-zinc-400'}>
                    {link.icon}
                  </span>
                  {link.name}
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
