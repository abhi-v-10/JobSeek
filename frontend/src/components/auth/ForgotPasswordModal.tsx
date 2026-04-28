import React, { useState, useEffect } from 'react';
import { X, Mail, ShieldCheck, KeyRound, CheckCircle2, ArrowRight, Loader2, Lock } from 'lucide-react';
import Input from '../ui/Input';
import Button from '../ui/Button';
import api from '../../lib/axios';

interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({ isOpen, onClose }) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setStep(1);
        setEmail('');
        setOtp('');
        setNewPassword('');
        setConfirmPassword('');
        setError('');
        setSuccess('');
      }, 300);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSendOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter your registered email.');
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/forgot-password/send-otp/', { email });
      if (response.data?.success) {
        setStep(2);
      } else {
        setError(response.data?.message || 'Failed to send OTP.');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'Failed to send OTP. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length !== 6) {
      setError('OTP must be exactly 6 digits.');
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const response = await api.post('/auth/forgot-password/verify-otp/', { email, otp });
      if (response.data?.success) {
        setStep(3);
      } else {
        setError(response.data?.message || 'Invalid OTP.');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'Invalid OTP. Please check and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.post('/auth/forgot-password/reset/', {
        email,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      if (response.data?.success) {
        setSuccess('Password reset successfully! Redirecting to login...');
        setTimeout(() => {
          onClose();
        }, 3000);
      } else {
        setError(response.data?.message || 'Failed to reset password.');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.error || err.response?.data?.detail || 'Failed to reset password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-zinc-950/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl shadow-2xl overflow-hidden transform transition-all animate-in fade-in zoom-in duration-300">
        <div className="p-8">
          <div className="flex justify-between items-start mb-6">
            <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-colors ${success ? 'bg-green-500/10 text-green-600' : 'bg-blue-500/10 text-blue-600 dark:text-blue-400'}`}>
              {success ? <CheckCircle2 size={28} /> : step === 1 ? <Mail size={28} /> : step === 2 ? <ShieldCheck size={28} /> : <Lock size={28} />}
            </div>
            <button 
              onClick={onClose}
              className="p-2 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          {!success ? (
            <>
              <h3 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
                {step === 1 ? 'Forgot Password?' : step === 2 ? 'Verify OTP' : 'Create New Password'}
              </h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-8 leading-relaxed">
                {step === 1 
                  ? "Don't worry! Enter your email address below and we'll send you an OTP to reset your password."
                  : step === 2 
                    ? `We've sent a 6-digit code to ${email}. Please enter it below to verify your identity.`
                    : "Identity verified! Please enter your new password below."
                }
              </p>

              <form onSubmit={step === 1 ? handleSendOTP : step === 2 ? handleVerifyOTP : handleResetPassword} className="space-y-5">
                {step === 1 && (
                  <Input
                    label="Email Address"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                  />
                )}
                
                {step === 2 && (
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300 flex items-center gap-2">
                      <KeyRound size={14} className="text-zinc-400" />
                      One-Time Password (OTP)
                    </label>
                    <input
                      type="text"
                      maxLength={6}
                      placeholder="000000"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                      className="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-lg font-mono tracking-[0.5em] text-center focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition-all"
                      required
                      autoFocus
                    />
                  </div>
                )}

                {step === 3 && (
                  <>
                    <Input
                      label="New Password"
                      type="password"
                      placeholder="••••••••"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      autoFocus
                    />
                    
                    <Input
                      label="Confirm New Password"
                      type="password"
                      placeholder="••••••••"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </>
                )}

                {error && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/30 rounded-xl">
                    <p className="text-xs font-medium text-red-600 dark:text-red-400">{error}</p>
                  </div>
                )}

                <div className="pt-2">
                  <Button type="submit" isLoading={isLoading} className="w-full py-4 rounded-2xl flex items-center justify-center gap-2">
                    {step === 1 ? (
                      <>
                        Send OTP
                        <ArrowRight size={18} />
                      </>
                    ) : step === 2 ? (
                      'Verify OTP'
                    ) : (
                      'Reset Password'
                    )}
                  </Button>
                </div>

                {step !== 1 && (
                  <button 
                    type="button"
                    onClick={() => setStep((step - 1) as any)}
                    className="w-full text-center text-sm font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-300 transition-colors"
                  >
                    Back to previous step
                  </button>
                )}
              </form>
            </>
          ) : (
            <div className="text-center py-4">
              <h3 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">Success!</h3>
              <p className="text-zinc-500 dark:text-zinc-400 mb-8">{success}</p>
              <div className="flex justify-center">
                <Loader2 className="animate-spin text-zinc-400" size={32} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordModal;
