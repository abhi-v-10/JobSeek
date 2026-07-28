import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X, Mail, Phone, FileText, MessageSquare,
  Loader2, Calendar,
} from 'lucide-react';
import { jobsService } from '../../services/jobs';
import type { ApplicantDetail } from '../../services/jobs';

const LinkedinIcon = () => (
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="w-[15px] h-[15px] fill-current">
    <path d="M20.4,20.4h-3.6v-5.6c0-1.3,0-3-1.9-3s-2.1,1.4-2.1,2.9v5.7H9.2V9h3.4v1.6h0 c0.5-0.9,1.6-1.9,3.4-1.9c3.6,0,4.3,2.4,4.3,5.5V20.4z M5.3,7.4c-1.1,0-2.1-0.9-2.1-2.1c0-1.1,0.9-2.1,2.1-2.1 c1.1,0,2.1,0.9,2.1,2.1C7.4,6.4,6.5,7.4,5.3,7.4z M7.1,20.4H3.6V9h3.6V20.4z" />
  </svg>
);

const GithubIcon = () => (
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" className="w-[15px] h-[15px] fill-current">
    <path d="M10.9,2.1c-4.6,0.5-8.3,4.2-8.8,8.7c-0.6,5,2.5,9.3,6.9,10.7v-2.3c0,0-0.4,0.1-0.9,0.1c-1.4,0-2-1.2-2.1-1.9 c-0.1-0.4-0.3-0.7-0.6-1C5.1,16.3,5,16.3,5,16.2C5,16,5.3,16,5.4,16c0.6,0,1.1,0.7,1.3,1c0.5,0.8,1.1,1,1.4,1c0.4,0,0.7-0.1,0.9-0.2 c0.1-0.7,0.4-1.4,1-1.8c-2.3-0.5-4-1.8-4-4c0-1.1,0.5-2.2,1.2-3C7.1,8.8,7,8.3,7,7.6C7,7.2,7,6.6,7.3,6c0,0,1.4,0,2.8,1.3 C10.6,7.1,11.3,7,12,7s1.4,0.1,2,0.3C15.3,6,16.8,6,16.8,6C17,6.6,17,7.2,17,7.6c0,0.8-0.1,1.2-0.2,1.4c0.7,0.8,1.2,1.8,1.2,3 c0,2.2-1.7,3.5-4,4c0.6,0.5,1,1.4,1,2.3v3.3c4.1-1.3,7-5.1,7-9.5C22,6.1,16.9,1.4,10.9,2.1z" />
  </svg>
);

const STATUS_BADGE: Record<string, string> = {
  applied:   'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  reviewing: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  accepted:  'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected:  'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const SKILL_CATEGORY_LABEL: Record<string, string> = {
  technical: 'Technical',
  language: 'Language',
  other: 'Other',
};

interface ApplicantProfileModalProps {
  jobId: number | string;
  applicationId: number | string;
  onClose: () => void;
}

const ApplicantProfileModal: React.FC<ApplicantProfileModalProps> = ({ jobId, applicationId, onClose }) => {
  const navigate = useNavigate();
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const handleMessage = () => {
    if (!applicant?.conversation_id) return;
    onClose();
    navigate(`/messages?conversation=${applicant.conversation_id}`);
  };

  useEffect(() => {
    let cancelled = false;
    jobsService.getApplicantDetail(jobId, applicationId)
      .then(data => { if (!cancelled) setApplicant(data); })
      .catch(err => { if (!cancelled) setError(err.response?.data?.detail || 'Failed to load applicant profile.'); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [jobId, applicationId]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-zinc-950/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl shadow-2xl transform transition-all animate-in fade-in zoom-in duration-300">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-full text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-50 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors z-10"
        >
          <X size={18} />
        </button>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24">
            <Loader2 size={24} className="animate-spin text-zinc-400" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-24 px-8 text-center text-sm text-red-500">
            {error}
          </div>
        ) : applicant ? (
          <div className="p-8">
            {/* Header */}
            <div className="flex items-start gap-4 mb-6">
              {applicant.profile_picture ? (
                <img
                  src={applicant.profile_picture}
                  alt={applicant.full_name || applicant.username}
                  className="w-16 h-16 rounded-full object-cover border-2 border-zinc-200 dark:border-zinc-700 shrink-0"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-xl font-bold text-zinc-500 dark:text-zinc-400 shrink-0">
                  {(applicant.full_name || applicant.username).charAt(0).toUpperCase()}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 truncate">
                  {applicant.full_name || applicant.username}
                </h2>
                <p className="text-sm text-zinc-400 truncate">@{applicant.username}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${STATUS_BADGE[applicant.status] || 'bg-zinc-100 text-zinc-500'}`}>
                    {applicant.status}
                  </span>
                  {applicant.conversation_id && (
                    <button
                      onClick={handleMessage}
                      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 text-xs font-semibold rounded-full hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors cursor-pointer"
                    >
                      <MessageSquare size={12} />
                      Message
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Contact info */}
            <div className="space-y-2.5 mb-6 pb-6 border-b border-zinc-100 dark:border-zinc-800">
              <div className="flex items-center gap-2.5 text-sm text-zinc-600 dark:text-zinc-300">
                <Mail size={15} className="text-zinc-400 shrink-0" />
                <a href={`mailto:${applicant.email}`} className="hover:underline truncate">{applicant.email}</a>
              </div>
              {applicant.mobile_number && (
                <div className="flex items-center gap-2.5 text-sm text-zinc-600 dark:text-zinc-300">
                  <Phone size={15} className="text-zinc-400 shrink-0" />
                  <span>{applicant.mobile_number}</span>
                </div>
              )}
              <div className="flex items-center gap-2.5 text-sm text-zinc-600 dark:text-zinc-300">
                <Calendar size={15} className="text-zinc-400 shrink-0" />
                <span>Applied on {new Date(applicant.applied_at).toLocaleDateString()}</span>
              </div>
            </div>

            {/* Links */}
            <div className="flex flex-wrap gap-2.5 mb-6">
              {applicant.resume && (
                <a
                  href={applicant.resume}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-3.5 py-2 bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 text-sm font-medium rounded-xl hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors"
                >
                  <FileText size={15} />
                  View Resume
                </a>
              )}
              {applicant.linkedin_url && (
                <a
                  href={applicant.linkedin_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-3.5 py-2 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 text-sm font-medium rounded-xl hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                >
                  <LinkedinIcon />
                  LinkedIn
                </a>
              )}
              {applicant.github_url && (
                <a
                  href={applicant.github_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-3.5 py-2 border border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 text-sm font-medium rounded-xl hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                >
                  <GithubIcon />
                  GitHub
                </a>
              )}
              {!applicant.resume && !applicant.linkedin_url && !applicant.github_url && (
                <p className="text-sm text-zinc-400 italic">No resume or profile links provided.</p>
              )}
            </div>

            {/* Skills */}
            {applicant.skills.length > 0 && (
              <div className="mb-6">
                <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-2.5">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {applicant.skills.map((skill, idx) => (
                    <span
                      key={`${skill.name}-${idx}`}
                      title={SKILL_CATEGORY_LABEL[skill.category] || skill.category}
                      className="px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-lg text-xs font-medium"
                    >
                      {skill.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Message */}
            <div>
              <h3 className="flex items-center gap-2 text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mb-2.5">
                <MessageSquare size={13} />
                Message from Applicant
              </h3>
              {applicant.message ? (
                <p className="text-sm text-zinc-700 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800 rounded-xl p-4 whitespace-pre-wrap">
                  {applicant.message}
                </p>
              ) : (
                <p className="text-sm text-zinc-400 italic">No message included with this application.</p>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default ApplicantProfileModal;
