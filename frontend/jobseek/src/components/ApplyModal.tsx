import React, { useState } from 'react';
import { X, ShieldCheck, Check, MessageSquareText } from 'lucide-react';

interface ApplyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (message: string) => void;
  isSubmitting: boolean;
  jobTitle: string;
}

const ApplyModal: React.FC<ApplyModalProps> = ({ isOpen, onClose, onConfirm, isSubmitting, jobTitle }) => {
  const [agreed, setAgreed] = useState(false);
  const [message, setMessage] = useState('');

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (agreed) {
      onConfirm(message);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop with heavy blur */}
      <div 
        className="fixed inset-0 bg-zinc-950/40 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal with glassmorphism */}
      <div className="relative w-full max-w-lg bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl border border-white/20 dark:border-zinc-800/50 rounded-3xl shadow-2xl overflow-hidden transform transition-all scale-100 opacity-100">
        <div className="p-8">
          <div className="flex justify-between items-start mb-6">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 dark:bg-blue-400/10 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <ShieldCheck size={28} />
            </div>
            <button 
              onClick={onClose}
              className="p-2 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
            >
              <X size={20} />
            </button>
          </div>

          <h3 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
            Confirm Application
          </h3>
          <p className="text-zinc-600 dark:text-zinc-400 mb-6">
            You are applying for <span className="font-semibold text-zinc-900 dark:text-zinc-50">{jobTitle}</span>. 
            Please review the following information sharing agreement.
          </p>

          <div className="space-y-6 mb-8">
            {/* Optional Message Field */}
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
                <MessageSquareText size={16} className="text-zinc-400" />
                Add a message (Optional)
              </label>
              <textarea
                rows={3}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Write a brief note to the employer..."
                className="w-full px-4 py-3 bg-white/50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 rounded-2xl text-sm text-zinc-900 dark:text-zinc-50 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all resize-none"
              />
            </div>

            {/* Consent Box */}
            <div className="bg-zinc-50/50 dark:bg-zinc-800/30 rounded-2xl p-5 border border-zinc-100 dark:border-zinc-800/50">
              <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed mb-4">
                By clicking on apply you hereby agree to share your <span className="font-medium text-zinc-900 dark:text-zinc-100 px-1 py-0.5 bg-blue-100 dark:bg-blue-900/40 rounded">resume</span>, 
                <span className="font-medium text-zinc-900 dark:text-zinc-100 px-1 py-0.5 bg-blue-100 dark:bg-blue-900/40 rounded mx-1">LinkedIn</span> 
                and <span className="font-medium text-zinc-900 dark:text-zinc-100 px-1 py-0.5 bg-blue-100 dark:bg-blue-900/40 rounded mx-1">GitHub</span> 
                profiles and your <span className="font-medium text-zinc-900 dark:text-zinc-100 px-1 py-0.5 bg-blue-100 dark:bg-blue-900/40 rounded">skills</span> to the job poster.
              </p>
              
              <label className="flex items-start gap-3 cursor-pointer group">
                <div className="relative mt-0.5 shrink-0">
                  <input 
                    type="checkbox" 
                    className="sr-only" 
                    checked={agreed}
                    onChange={() => setAgreed(!agreed)}
                  />
                  <div className={`w-5 h-5 rounded border-2 transition-all duration-200 flex items-center justify-center
                    ${agreed ? 'bg-zinc-900 border-zinc-900 dark:bg-zinc-50 dark:border-zinc-50' : 'border-zinc-300 dark:border-zinc-700 group-hover:border-zinc-400 dark:group-hover:border-zinc-600'}
                  `}>
                    {agreed && <Check size={14} className="text-white dark:text-zinc-900 stroke-[3]" />}
                  </div>
                </div>
                <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 select-none">
                  I agree to share my information with the employer
                </span>
              </label>
            </div>
          </div>

          <div className="flex gap-4">
            <button
              onClick={onClose}
              className="flex-1 py-3 px-6 text-sm font-bold rounded-2xl border-2 border-zinc-900 dark:border-zinc-50 text-zinc-900 dark:text-zinc-50 bg-transparent hover:bg-zinc-900 hover:text-white dark:hover:bg-zinc-50 dark:hover:text-zinc-900 transition-all duration-200 cursor-pointer"
            >
              Cancel
            </button>
            
            <button
              onClick={handleConfirm}
              disabled={!agreed || isSubmitting}
              className={`flex-1 py-3 px-6 text-sm font-bold rounded-2xl border-2 transition-all duration-200 cursor-pointer
                ${agreed 
                  ? 'border-zinc-900 dark:border-zinc-50 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-transparent hover:text-zinc-900 dark:hover:bg-transparent dark:hover:text-zinc-50' 
                  : 'border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-800 text-zinc-400 dark:text-zinc-500 cursor-not-allowed'}
              `}
            >
              {isSubmitting ? 'Processing…' : 'Apply Now'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApplyModal;
