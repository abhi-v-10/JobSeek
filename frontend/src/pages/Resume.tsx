import React, { useState, useEffect, useRef } from 'react';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import Button from '../components/ui/Button';
import { FileText, Upload, Trash2, CheckCircle2 } from 'lucide-react';
import api from '../lib/axios';

const Resume = () => {
  const [resume, setResume] = useState<File | null>(null);
  const [existingResume, setExistingResume] = useState<string | null>(null);
  const [resumeUploadedAt, setResumeUploadedAt] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  
  const resumeInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await api.get('/users/profile/');
        setExistingResume(response.data.resume);
        setResumeUploadedAt(response.data.resume_uploaded_at);
      } catch (err) {
        console.error('Failed to load profile data', err);
      }
    };
    fetchProfile();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setResume(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setResume(e.dataTransfer.files[0]);
    }
  };

  const handleUploadClick = () => {
    resumeInputRef.current?.click();
  };

  const handleClearFile = () => {
    setResume(null);
    if (resumeInputRef.current) resumeInputRef.current.value = '';
  };

  const handleDeleteResume = async () => {
    if (!window.confirm('Are you sure you want to remove your resume?')) return;
    
    setIsLoading(true);
    try {
      // Send null to clear the resume field
      const response = await api.patch('/users/profile/', { resume: null });
      
      setExistingResume(null);
      setResumeUploadedAt(null);
      setMessage({ type: 'success', text: 'Resume removed successfully!' });
      
      // Notify Navbar to update state
      window.dispatchEvent(new Event('profileUpdated'));
    } catch (err: any) {
      console.error('Delete error:', err);
      setMessage({ 
        type: 'error', 
        text: err.response?.data?.detail || 'Failed to remove resume.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resume) return;

    setIsLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const payload = new FormData();
      payload.append('resume', resume);

      const response = await api.patch('/users/profile/', payload, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setMessage({ type: 'success', text: 'Resume uploaded successfully!' });
      
      // Update local existing state
      if (response.data.resume) setExistingResume(response.data.resume);
      if (response.data.resume_uploaded_at) setResumeUploadedAt(response.data.resume_uploaded_at);
      
      // Notify Navbar to update resume state
      window.dispatchEvent(new Event('profileUpdated'));
      
      // Clear file inputs
      handleClearFile();
      
    } catch (err: any) {
      console.error('Upload error:', err);
      setMessage({ 
        type: 'error', 
        text: err.response?.data?.detail || err.response?.data?.error || 'Failed to upload resume.' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ProtectedRoute>
        <div className="flex-1 flex flex-col p-6 max-w-4xl mx-auto w-full">
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Resume Manager</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mb-8">Upload, view, and manage your CV to apply for jobs.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Upload Section */}
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm flex flex-col">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-6">Upload New Resume</h2>
              
              <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
                <div 
                  className={`flex-1 flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl transition-colors
                    ${resume ? 'border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50' : 'border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 cursor-pointer'}
                  `}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  onClick={!resume ? handleUploadClick : undefined}
                >
                  <input 
                    type="file" 
                    accept=".pdf,.doc,.docx"
                    onChange={handleFileChange}
                    ref={resumeInputRef}
                    className="hidden"
                  />
                  
                  {resume ? (
                    <div className="flex flex-col items-center text-center w-full">
                      <div className="w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-4 text-blue-600 dark:text-blue-400">
                        <FileText size={32} />
                      </div>
                      <p className="font-medium text-zinc-900 dark:text-zinc-50 mb-1 truncate w-full px-4">{resume.name}</p>
                      <p className="text-sm text-zinc-500 mb-6">{(resume.size / 1024 / 1024).toFixed(2)} MB</p>
                      
                      <button 
                        type="button" 
                        onClick={handleClearFile}
                        className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 hover:underline"
                      >
                        <Trash2 size={16} />
                        Remove file
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center text-center">
                      <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-4 text-zinc-500">
                        <Upload size={32} />
                      </div>
                      <p className="font-medium text-zinc-900 dark:text-zinc-50 mb-1">Click to upload or drag and drop</p>
                      <p className="text-sm text-zinc-500">PDF, DOC, DOCX up to 10MB</p>
                    </div>
                  )}
                </div>

                {message.text && (
                  <div className={`mt-4 p-3 rounded-md text-sm font-medium ${message.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                    {message.text}
                  </div>
                )}

                <div className="pt-6 mt-auto">
                  <Button type="submit" isLoading={isLoading} disabled={!resume}>
                    Upload Resume
                  </Button>
                </div>
              </form>
            </div>

            {/* Current Resume Section */}
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-8 shadow-sm flex flex-col">
              <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-6">Current Resume</h2>
              
              <div className="flex-1 flex flex-col justify-center">
                {existingResume ? (
                  <div className="flex flex-col items-center text-center p-8 bg-zinc-50 dark:bg-zinc-800/30 rounded-xl border border-zinc-100 dark:border-zinc-800">
                    <div className="relative">
                      <div className="w-20 h-20 rounded-2xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center mb-4 text-green-600 dark:text-green-400">
                        <FileText size={40} />
                      </div>
                      <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-white dark:bg-zinc-900 flex items-center justify-center">
                        <CheckCircle2 size={24} className="text-green-500" />
                      </div>
                    </div>
                    
                    <h3 className="font-bold text-zinc-900 dark:text-zinc-50 mb-2">Resume Active</h3>
                    {resumeUploadedAt && (
                      <p className="text-sm text-zinc-500 mb-6">
                        Uploaded on {new Date(resumeUploadedAt).toLocaleDateString()}
                      </p>
                    )}
                    
                    <div className="flex gap-3 w-full max-w-[280px]">
                      <a 
                        href={existingResume.startsWith('http') ? existingResume : `http://127.0.0.1:8000${existingResume}`} 
                        target="_blank" 
                        rel="noreferrer"
                        className="flex-1 inline-flex items-center justify-center px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 text-sm font-medium rounded-lg hover:bg-zinc-800 dark:hover:bg-white/90 transition-colors"
                      >
                        View
                      </a>
                      <button 
                        onClick={handleDeleteResume}
                        disabled={isLoading}
                        className="flex-1 inline-flex items-center justify-center px-4 py-2 border border-red-200 dark:border-red-900/30 text-red-600 dark:text-red-400 text-sm font-medium rounded-lg hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors disabled:opacity-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center text-center p-8 bg-zinc-50 dark:bg-zinc-800/30 rounded-xl border border-zinc-100 dark:border-zinc-800">
                    <div className="w-20 h-20 rounded-2xl bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center mb-4 text-zinc-400">
                      <FileText size={40} opacity={0.5} />
                    </div>
                    <h3 className="font-bold text-zinc-900 dark:text-zinc-50 mb-2">No Resume Found</h3>
                    <p className="text-sm text-zinc-500">
                      You haven't uploaded a resume yet. Upload one to start applying for jobs.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </ProtectedRoute>
  );
};

export default Resume;
