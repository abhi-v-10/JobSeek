import React, { useState, useEffect, useRef } from 'react';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import api from '../lib/axios';

const ProfileSettings = () => {
  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    mobile_number: '',
    user_type: 'seeker'
  });
  const [profilePic, setProfilePic] = useState<File | null>(null);
  const [existingProfilePic, setExistingProfilePic] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  const profilePicInputRef = useRef<HTMLInputElement>(null);

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
      } catch (err) {
        console.error('Failed to load profile data', err);
      }
    };
    fetchProfile();
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setProfilePic(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
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
      
      // Update local existing state
      if (response.data.profile_picture) setExistingProfilePic(response.data.profile_picture);
      
      // Notify Navbar to update profile image
      window.dispatchEvent(new Event('profileUpdated'));
      
      // Clear file inputs
      setProfilePic(null);
      if (profilePicInputRef.current) profilePicInputRef.current.value = '';
      
    } catch (err: any) {
      console.error('Update error:', err);
      setMessage({ 
        type: 'error', 
        text: err.response?.data?.detail || err.response?.data?.error || 'Failed to update profile.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ProtectedRoute>
        <div className="flex-1 flex flex-col p-6 max-w-3xl mx-auto w-full">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Profile Settings</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mb-8">Update your personal information and account preferences.</p>

          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm">
            <form onSubmit={handleSubmit} className="space-y-6">
              
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
                    <input 
                      type="radio" 
                      name="user_type" 
                      value="seeker" 
                      checked={formData.user_type === 'seeker'}
                      onChange={handleChange}
                      className="sr-only" 
                    />
                    Job Seeker
                  </label>
                  <label className={`border rounded-lg p-3 cursor-pointer transition-all flex items-center justify-center text-sm font-medium
                    ${formData.user_type === 'poster' 
                      ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900' 
                      : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900/50'}`}>
                    <input 
                      type="radio" 
                      name="user_type" 
                      value="poster" 
                      checked={formData.user_type === 'poster'}
                      onChange={handleChange}
                      className="sr-only" 
                    />
                    Job Poster
                  </label>
                </div>
              </div>

              {message.text && (
                <div className={`p-3 rounded-md text-sm font-medium ${message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                  {message.text}
                </div>
              )}

              <div className="pt-4 flex justify-end">
                <div className="w-full sm:w-auto">
                  <Button type="submit" isLoading={isLoading}>
                    Save Changes
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </ProtectedRoute>
  );
};

export default ProfileSettings;
