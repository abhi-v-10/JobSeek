import React, { useState, useEffect, useRef } from 'react';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import ForgotPasswordModal from '../components/auth/ForgotPasswordModal';
import api from '../lib/axios';
import { TECHNICAL_SKILLS, LANGUAGES } from '../constants/skills';
import { Shield, Key, Mail, Fingerprint } from 'lucide-react';

const ProfileSettings = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'skills' | 'security'>('profile');
  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    mobile_number: '',
    user_type: 'seeker',
    linkedin_url: '',
    github_url: ''
  });
  const [profilePic, setProfilePic] = useState<File | null>(null);
  const [existingProfilePic, setExistingProfilePic] = useState<string | null>(null);
  
  // Security state
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);

  // Skills state
  const [selectedTech, setSelectedTech] = useState<string[]>([]);
  const [selectedLangs, setSelectedLangs] = useState<string[]>([]);
  const [otherSkills, setOtherSkills] = useState<string[]>([]);
  const [isEditingSkills, setIsEditingSkills] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState<'technical' | 'language' | 'other' | null>(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  const profilePicInputRef = useRef<HTMLInputElement>(null);
  const techDropdownRef = useRef<HTMLDivElement>(null);
  const langDropdownRef = useRef<HTMLDivElement>(null);
  
  const [techSearch, setTechSearch] = useState('');
  const [langSearch, setLangSearch] = useState('');
  const [otherSearch, setOtherSearch] = useState('');
  const [showTechDropdown, setShowTechDropdown] = useState(false);
  const [showLangDropdown, setShowLangDropdown] = useState(false);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (techDropdownRef.current && !techDropdownRef.current.contains(event.target as Node)) {
        setShowTechDropdown(false);
      }
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target as Node)) {
        setShowLangDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await api.get('/users/profile/');
        const data = response.data;
        setFormData({
          username: data.username || '',
          full_name: data.full_name || '',
          mobile_number: data.mobile_number || '',
          user_type: data.user_type || 'seeker',
          linkedin_url: data.linkedin_url || '',
          github_url: data.github_url || ''
        });
        setExistingProfilePic(data.profile_picture);
        
        // Load skills
        if (data.skills) {
          const tech = data.skills.filter((s: any) => s.category === 'technical').map((s: any) => s.name);
          const langs = data.skills.filter((s: any) => s.category === 'language').map((s: any) => s.name);
          const others = data.skills.filter((s: any) => s.category === 'other').map((s: any) => s.name);
          
          setSelectedTech(tech);
          setSelectedLangs(langs);
          setOtherSkills(others);
        }
      } catch (err) {
        console.error('Failed to load profile data', err);
      }
    };
    fetchProfile();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPasswordData({ ...passwordData, [e.target.name]: e.target.value });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setProfilePic(e.target.files[0]);
    }
  };

  const handleSubmitProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const payload = new FormData();
      payload.append('username', formData.username);
      payload.append('full_name', formData.full_name);
      payload.append('mobile_number', formData.mobile_number);
      payload.append('user_type', formData.user_type);
      payload.append('linkedin_url', formData.linkedin_url);
      payload.append('github_url', formData.github_url);
      
      if (profilePic) {
        payload.append('profile_picture', profilePic);
      }

      const response = await api.patch('/users/profile/', payload, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
      if (response.data.profile_picture) setExistingProfilePic(response.data.profile_picture);
      window.dispatchEvent(new Event('profileUpdated'));
      setProfilePic(null);
      if (profilePicInputRef.current) profilePicInputRef.current.value = '';
      
    } catch (err: any) {
      console.error('Update error:', err);
      setMessage({ 
        type: 'error', 
        text: err.response?.data?.message || err.response?.data?.detail || err.response?.data?.error || 'Failed to update profile.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitSkills = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage({ type: '', text: '' });

    const formattedSkills = [
      ...selectedTech.map(name => ({ name, category: 'technical' })),
      ...selectedLangs.map(name => ({ name, category: 'language' })),
      ...otherSkills.map(name => ({ name, category: 'other' }))
    ];

    try {
      await api.post('/users/skills/bulk/', { skills: formattedSkills });
      setMessage({ type: 'success', text: 'Skills updated successfully!' });
      setIsEditingSkills(false);
    } catch (err: any) {
      console.error('Skills update error:', err);
      setMessage({ 
        type: 'error', 
        text: err.response?.data?.message || err.response?.data?.detail || 'Failed to update skills.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });

    if (!passwordData.old_password || !passwordData.new_password || !passwordData.confirm_password) {
      setMessage({ type: 'error', text: 'All fields are required.' });
      return;
    }

    if (passwordData.new_password.length < 8) {
      setMessage({ type: 'error', text: 'New password must be at least 8 characters long.' });
      return;
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      setMessage({ type: 'error', text: 'Passwords do not match.' });
      return;
    }

    if (passwordData.new_password === passwordData.old_password) {
      setMessage({ type: 'error', text: 'New password cannot be the same as your current password.' });
      return;
    }

    setIsLoading(true);
    try {
      await api.post('/profile/change-password/', passwordData);
      setMessage({ type: 'success', text: 'Password changed successfully!' });
      setPasswordData({
        old_password: '',
        new_password: '',
        confirm_password: ''
      });
    } catch (err: any) {
      setMessage({ 
        type: 'error', 
        text: err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'Failed to change password.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const addTech = (skill: string) => {
    if (!selectedTech.includes(skill)) {
      setSelectedTech([...selectedTech, skill]);
    }
    setTechSearch('');
    setShowTechDropdown(false);
  };

  const removeTech = (skill: string) => {
    setSelectedTech(selectedTech.filter(s => s !== skill));
  };

  const addLang = (lang: string) => {
    if (!selectedLangs.includes(lang)) {
      setSelectedLangs([...selectedLangs, lang]);
    }
    setLangSearch('');
    setShowLangDropdown(false);
  };

  const removeLang = (lang: string) => {
    setSelectedLangs(selectedLangs.filter(l => l !== lang));
  };

  const addOther = (skill: string) => {
    const trimmed = skill.trim();
    if (trimmed && !otherSkills.includes(trimmed)) {
      setOtherSkills([...otherSkills, trimmed]);
    }
    setOtherSearch('');
  };

  const removeOther = (skill: string) => {
    setOtherSkills(otherSkills.filter(s => s !== skill));
  };

  const handleOtherKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addOther(otherSearch);
    }
  };

  const filteredTech = TECHNICAL_SKILLS.filter(s => 
    s.toLowerCase().includes(techSearch.toLowerCase()) && !selectedTech.includes(s)
  );

  const filteredLangs = LANGUAGES.filter(l => 
    l.toLowerCase().includes(langSearch.toLowerCase()) && !selectedLangs.includes(l)
  );

  return (
    <ProtectedRoute>
      <div className="flex-1 p-6 max-w-6xl mx-auto w-full">
        <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Profile Settings</h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8">Update your personal information and account preferences.</p>

        <div className="flex flex-col md:flex-row gap-8">
          {/* Left Sidebar Tabs */}
          <div className="w-full md:w-64 shrink-0">
            <nav className="flex flex-row md:flex-col gap-1">
              <button
                onClick={() => setActiveTab('profile')}
                className={`flex-1 md:flex-none text-left px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'profile'
                    ? 'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shadow-md'
                    : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                }`}
              >
                Edit Profile
              </button>
              <button
                onClick={() => {
                  setActiveTab('skills');
                  setIsEditingSkills(false);
                }}
                className={`flex-1 md:flex-none text-left px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'skills'
                    ? 'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shadow-md'
                    : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                }`}
              >
                Manage Skills
              </button>
              <button
                onClick={() => setActiveTab('security')}
                className={`flex-1 md:flex-none text-left px-4 py-3 rounded-xl text-sm font-medium transition-all cursor-pointer ${
                  activeTab === 'security'
                    ? 'bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shadow-md'
                    : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                }`}
              >
                Account Security
              </button>
            </nav>
          </div>

          {/* Right Content Area */}
          <div className="flex-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm min-h-[500px]">
            {activeTab === 'profile' ? (
              <form onSubmit={handleSubmitProfile} className="space-y-6">
                <div className="flex flex-col md:flex-row gap-6 items-start md:items-center">
                  <div className="shrink-0 relative">
                    {profilePic ? (
                      <img src={URL.createObjectURL(profilePic)} alt="New Profile" className="w-24 h-24 rounded-full object-cover border-2 border-zinc-200 dark:border-zinc-700" />
                    ) : existingProfilePic ? (
                      <img 
                        src={
                          existingProfilePic.startsWith('http') 
                            ? existingProfilePic 
                            : existingProfilePic.startsWith('/media/')
                              ? `http://127.0.0.1:8000${existingProfilePic}`
                              : `http://127.0.0.1:8000/media/${existingProfilePic.startsWith('/') ? existingProfilePic.substring(1) : existingProfilePic}`
                        } 
                        alt="Profile" 
                        className="w-24 h-24 rounded-full object-cover border-2 border-zinc-200 dark:border-zinc-700" 
                      />
                    ) : (
                      <div className="w-24 h-24 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center border-2 border-zinc-200 dark:border-zinc-700">
                        <span className="text-zinc-400 text-xs">No image</span>
                      </div>
                    )}
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">Profile Picture</label>
                    <input 
                      type="file" 
                      accept="image/*"
                      onChange={handleFileChange}
                      ref={profilePicInputRef}
                      className="block w-full text-sm text-zinc-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-zinc-100 file:text-zinc-700 hover:file:bg-zinc-200 dark:file:bg-zinc-800 dark:file:text-zinc-300 dark:hover:file:bg-zinc-700 transition-colors"
                    />
                    <p className="text-xs text-zinc-500 mt-2">Recommended: Square image, max 2MB.</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Input
                    label="Username"
                    name="username"
                    placeholder="johndoe"
                    value={formData.username}
                    onChange={handleChange}
                  />
                  <Input
                    label="Full Name"
                    name="full_name"
                    placeholder="Your full name"
                    value={formData.full_name}
                    onChange={handleChange}
                  />
                  <Input
                    label="Mobile Number"
                    name="mobile_number"
                    placeholder="e.g. +1234567890"
                    value={formData.mobile_number}
                    onChange={handleChange}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Input
                    label="LinkedIn Profile URL"
                    name="linkedin_url"
                    placeholder="https://linkedin.com/in/username"
                    value={formData.linkedin_url}
                    onChange={handleChange}
                  />
                  <Input
                    label="GitHub Profile URL"
                    name="github_url"
                    placeholder="https://github.com/username"
                    value={formData.github_url}
                    onChange={handleChange}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Account Type</label>
                  <div className="grid grid-cols-2 gap-2">
                    <label className={`border rounded-lg p-3 cursor-pointer transition-all flex items-center justify-center text-sm font-medium
                      ${formData.user_type === 'seeker' 
                        ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900' 
                        : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50'}`}>
                      <input type="radio" name="user_type" value="seeker" checked={formData.user_type === 'seeker'} onChange={handleChange} className="sr-only" />
                      Job Seeker
                    </label>
                    <label className={`border rounded-lg p-3 cursor-pointer transition-all flex items-center justify-center text-sm font-medium
                      ${formData.user_type === 'poster' 
                        ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900' 
                        : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50'}`}>
                      <input type="radio" name="user_type" value="poster" checked={formData.user_type === 'poster'} onChange={handleChange} className="sr-only" />
                      Job Poster
                    </label>
                  </div>
                </div>

                <div className="pt-4 flex justify-end">
                  <Button type="submit" isLoading={isLoading}>Save Profile</Button>
                </div>
              </form>
            ) : activeTab === 'skills' ? (
              !isEditingSkills ? (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">Skill Summary</h2>
                  <button
                    onClick={() => setIsEditingSkills(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-xl text-sm font-semibold hover:opacity-90 transition-all shadow-sm cursor-pointer"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                    Edit Skills
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                  {/* Technical Card */}
                  <div 
                    onClick={() => setExpandedCategory(expandedCategory === 'technical' ? null : 'technical')}
                    className={`p-6 rounded-2xl border transition-all cursor-pointer group ${
                      expandedCategory === 'technical' 
                        ? 'border-zinc-900 dark:border-white bg-zinc-50 dark:bg-zinc-800/50 ring-1 ring-zinc-900 dark:ring-white' 
                        : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 hover:border-zinc-400 dark:hover:border-zinc-600'
                    }`}
                  >
                    <div className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">{selectedTech.length}</div>
                    <div className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Technical Skills</div>
                    <div className="mt-2 text-[10px] text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors">
                      {expandedCategory === 'technical' ? 'Click to collapse' : 'Click to view all'}
                    </div>
                  </div>

                  {/* Language Card */}
                  <div 
                    onClick={() => setExpandedCategory(expandedCategory === 'language' ? null : 'language')}
                    className={`p-6 rounded-2xl border transition-all cursor-pointer group ${
                      expandedCategory === 'language' 
                        ? 'border-zinc-900 dark:border-white bg-zinc-50 dark:bg-zinc-800/50 ring-1 ring-zinc-900 dark:ring-white' 
                        : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 hover:border-zinc-400 dark:hover:border-zinc-600'
                    }`}
                  >
                    <div className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">{selectedLangs.length}</div>
                    <div className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Languages</div>
                    <div className="mt-2 text-[10px] text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors">
                      {expandedCategory === 'language' ? 'Click to collapse' : 'Click to view all'}
                    </div>
                  </div>

                  {/* Other Card */}
                  <div 
                    onClick={() => setExpandedCategory(expandedCategory === 'other' ? null : 'other')}
                    className={`p-6 rounded-2xl border transition-all cursor-pointer group ${
                      expandedCategory === 'other' 
                        ? 'border-zinc-900 dark:border-white bg-zinc-50 dark:bg-zinc-800/50 ring-1 ring-zinc-900 dark:ring-white' 
                        : 'border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 hover:border-zinc-400 dark:hover:border-zinc-600'
                    }`}
                  >
                    <div className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">{otherSkills.length}</div>
                    <div className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Other Skills</div>
                    <div className="mt-2 text-[10px] text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors">
                      {expandedCategory === 'other' ? 'Click to collapse' : 'Click to view all'}
                    </div>
                  </div>
                </div>

                {/* Collapsible Drop Section */}
                <div className={`overflow-hidden transition-all duration-500 ease-in-out ${expandedCategory ? 'max-h-[1000px] opacity-100 mt-6' : 'max-h-0 opacity-0'}`}>
                  <div className="p-6 bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                    <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-4 uppercase tracking-wider">
                      {expandedCategory === 'technical' ? 'Technical Skills' : expandedCategory === 'language' ? 'Languages' : 'Other Skills'}
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {expandedCategory === 'technical' && selectedTech.map(s => (
                        <span key={s} className="px-3 py-1.5 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm shadow-sm">{s}</span>
                      ))}
                      {expandedCategory === 'language' && selectedLangs.map(s => (
                        <span key={s} className="px-3 py-1.5 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm shadow-sm">{s}</span>
                      ))}
                      {expandedCategory === 'other' && otherSkills.map(s => (
                        <span key={s} className="px-3 py-1.5 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm shadow-sm">{s}</span>
                      ))}
                      {((expandedCategory === 'technical' && selectedTech.length === 0) || 
                        (expandedCategory === 'language' && selectedLangs.length === 0) || 
                        (expandedCategory === 'other' && otherSkills.length === 0)) && (
                        <p className="text-sm text-zinc-500 italic">No skills added in this category yet.</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="p-8 text-center border-t border-zinc-100 dark:border-zinc-800 mt-8">
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm">
                    You have listed <span className="font-bold text-zinc-900 dark:text-zinc-50">{selectedTech.length + selectedLangs.length + otherSkills.length}</span> total skills.
                  </p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmitSkills} className="space-y-8">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">Edit Skills</h2>
                  <button
                    type="button"
                    onClick={() => setIsEditingSkills(false)}
                    className="text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 flex items-center gap-1 cursor-pointer"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                    Back to Summary
                  </button>
                </div>

                {/* Technical Skills */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Technical Skills</label>
                  <div className="relative" ref={techDropdownRef}>
                    <div className="flex flex-wrap gap-2 p-2 min-h-[42px] border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-900/50 focus-within:ring-2 focus-within:ring-zinc-900 dark:focus-within:ring-white transition-all">
                      {selectedTech.map(skill => (
                        <span key={skill} className="inline-flex items-center gap-1 px-2.5 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-md text-xs font-medium">
                          {skill}
                          <button type="button" onClick={() => removeTech(skill)} className="hover:text-zinc-300 dark:hover:text-zinc-600 transition-colors">×</button>
                        </span>
                      ))}
                      <input
                        type="text"
                        value={techSearch}
                        onChange={(e) => {
                          setTechSearch(e.target.value);
                          setShowTechDropdown(true);
                        }}
                        onFocus={() => setShowTechDropdown(true)}
                        placeholder={selectedTech.length === 0 ? "Search programming languages, cloud, design..." : ""}
                        className="flex-1 bg-transparent border-none outline-none text-sm min-w-[120px] dark:text-zinc-100"
                      />
                    </div>
                    {showTechDropdown && techSearch && (
                      <div className="absolute z-10 w-full mt-1 max-h-60 overflow-auto bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xl">
                        {filteredTech.length > 0 ? (
                          filteredTech.map(skill => (
                            <button
                              key={skill}
                              type="button"
                              onClick={() => addTech(skill)}
                              className="w-full text-left px-4 py-2.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 dark:text-zinc-100 transition-colors"
                            >
                              {skill}
                            </button>
                          ))
                        ) : (
                          <div className="px-4 py-2 text-sm text-zinc-500">No results found</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Languages */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Languages Known</label>
                  <div className="relative" ref={langDropdownRef}>
                    <div className="flex flex-wrap gap-2 p-2 min-h-[42px] border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-900/50 focus-within:ring-2 focus-within:ring-zinc-900 dark:focus-within:ring-white transition-all">
                      {selectedLangs.map(lang => (
                        <span key={lang} className="inline-flex items-center gap-1 px-2.5 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-md text-xs font-medium">
                          {lang}
                          <button type="button" onClick={() => removeLang(lang)} className="hover:text-zinc-300 dark:hover:text-zinc-600 transition-colors">×</button>
                        </span>
                      ))}
                      <input
                        type="text"
                        value={langSearch}
                        onChange={(e) => {
                          setLangSearch(e.target.value);
                          setShowLangDropdown(true);
                        }}
                        onFocus={() => setShowLangDropdown(true)}
                        placeholder={selectedLangs.length === 0 ? "Search languages..." : ""}
                        className="flex-1 bg-transparent border-none outline-none text-sm min-w-[120px] dark:text-zinc-100"
                      />
                    </div>
                    {showLangDropdown && langSearch && (
                      <div className="absolute z-10 w-full mt-1 max-h-48 overflow-auto bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-xl">
                        {filteredLangs.length > 0 ? (
                          filteredLangs.map(lang => (
                            <button
                              key={lang}
                              type="button"
                              onClick={() => addLang(lang)}
                              className="w-full text-left px-4 py-2.5 text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 dark:text-zinc-100 transition-colors"
                            >
                              {lang}
                            </button>
                          ))
                        ) : (
                          <div className="px-4 py-2 text-sm text-zinc-500">No results found</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Other Skills */}
                <div className="space-y-3">
                  <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Other Skills</label>
                  <div className="flex flex-wrap gap-2 p-2 min-h-[100px] border border-zinc-200 dark:border-zinc-800 rounded-lg bg-zinc-50 dark:bg-zinc-900/50 focus-within:ring-2 focus-within:ring-zinc-900 dark:focus-within:ring-white transition-all">
                    {otherSkills.map(skill => (
                      <span key={skill} className="inline-flex items-center gap-1 px-2.5 py-1 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-md text-xs font-medium h-fit">
                        {skill}
                        <button type="button" onClick={() => removeOther(skill)} className="hover:text-zinc-300 dark:hover:text-zinc-600 transition-colors">×</button>
                      </span>
                    ))}
                    <input
                      type="text"
                      value={otherSearch}
                      onChange={(e) => setOtherSearch(e.target.value)}
                      onKeyDown={handleOtherKeyDown}
                      placeholder="Prompt Engineering... (Enter or comma to add)"
                      className="flex-1 bg-transparent border-none outline-none text-sm min-w-[200px] dark:text-zinc-100 h-fit py-1"
                    />
                  </div>
                  <p className="text-xs text-zinc-500 mt-1">Type a skill and press Enter or use a comma to add it.</p>
                </div>

                <div className="pt-6 flex justify-end gap-4 border-t border-zinc-100 dark:border-zinc-800 mt-6">
                  <button 
                    type="button" 
                    onClick={() => setIsEditingSkills(false)}
                    className="px-6 py-2.5 rounded-xl text-sm font-semibold border border-zinc-900 dark:border-zinc-100 text-zinc-900 dark:text-zinc-100 bg-transparent hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-100 dark:hover:text-zinc-900 transition-all duration-200 cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit" 
                    disabled={isLoading}
                    className="px-6 py-2.5 rounded-xl text-sm font-semibold border border-zinc-900 dark:border-zinc-100 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 hover:bg-transparent hover:text-zinc-900 dark:hover:text-zinc-100 transition-all duration-200 flex items-center gap-2 cursor-pointer"
                  >
                    {isLoading && <svg className="animate-spin h-4 w-4 text-current" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>}
                    Save Skills
                  </button>
                </div>
              </form>
              )
            ) : (
              <div className="space-y-10">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <Shield className="text-zinc-900 dark:text-zinc-50" size={24} />
                    <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Change Password</h2>
                  </div>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8">Update your password to keep your account secure.</p>
                  
                  <form onSubmit={handleSubmitChangePassword} className="max-w-md space-y-5">
                    <Input
                      label="Current Password"
                      type="password"
                      name="old_password"
                      placeholder="••••••••"
                      value={passwordData.old_password}
                      onChange={handlePasswordChange}
                      required
                    />
                    <Input
                      label="New Password"
                      type="password"
                      name="new_password"
                      placeholder="••••••••"
                      value={passwordData.new_password}
                      onChange={handlePasswordChange}
                      required
                    />
                    <Input
                      label="Confirm New Password"
                      type="password"
                      name="confirm_password"
                      placeholder="••••••••"
                      value={passwordData.confirm_password}
                      onChange={handlePasswordChange}
                      required
                    />

                    <div className="pt-2 flex flex-col gap-4">
                      <Button type="submit" isLoading={isLoading} className="w-full">
                        Update Password
                      </Button>
                      
                      <button 
                        type="button" 
                        onClick={() => setIsForgotModalOpen(true)}
                        className="text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 transition-colors flex items-center justify-center gap-2"
                      >
                        <Key size={14} />
                        Forgot Password? Reset via OTP
                      </button>
                    </div>
                  </form>
                </div>

                <div className="pt-8 border-t border-zinc-100 dark:border-zinc-800">
                  <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-50 mb-4 flex items-center gap-2">
                    <Fingerprint size={20} className="text-zinc-400" />
                    Security Preferences
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-zinc-50 dark:bg-zinc-800/50 rounded-2xl border border-zinc-100 dark:border-zinc-800">
                      <div>
                        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Two-Factor Authentication</p>
                        <p className="text-xs text-zinc-500">Add an extra layer of security to your account.</p>
                      </div>
                      <span className="px-3 py-1 bg-zinc-200 dark:bg-zinc-700 text-zinc-600 dark:text-zinc-400 text-[10px] font-bold uppercase rounded-full">Coming Soon</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {message.text && (
              <div className={`mt-6 p-3 rounded-xl text-sm font-medium animate-in fade-in slide-in-from-top-2 duration-300 ${message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400 border border-green-100 dark:border-green-900/50' : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-100 dark:border-red-900/50'}`}>
                {message.text}
              </div>
            )}
          </div>
        </div>
        
        <ForgotPasswordModal 
          isOpen={isForgotModalOpen} 
          onClose={() => setIsForgotModalOpen(false)} 
        />
      </div>
    </ProtectedRoute>
  );
};

export default ProfileSettings;
