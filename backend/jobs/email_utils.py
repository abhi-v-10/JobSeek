import os
from django.core.mail import EmailMessage
from django.conf import settings

def send_application_email(job, applicant, conversation_id, optional_message=""):
    """
    Sends an email to the job poster when someone applies.
    """
    candidate_name = applicant.profile.full_name or applicant.username
    job_title = job.position or job.work
    poster_name = job.posted_by.profile.full_name or job.posted_by.username
    
    subject = f"New Application for {job_title} – {candidate_name}"
    
    skills_list = ", ".join([s.name for s in applicant.profile.skills.all()]) or "None listed"
    
    # Experience summary - Can be extracted from parsed_resume or just a placeholder
    experience_summary = "Please refer to the attached resume for detailed professional experience."
    if applicant.profile.parsed_resume and isinstance(applicant.profile.parsed_resume, dict):
        experience_summary = applicant.profile.parsed_resume.get('summary', experience_summary)

    body = f"""Hello {poster_name},

A new candidate has applied for your job posting:

Job Title: {job_title}
Company: {job.company or 'N/A'}

Candidate Details:
-------------------------
Name: {candidate_name}
Email: {applicant.email}
Phone: {applicant.profile.mobile_number or 'Not provided'}

Professional Profiles:
LinkedIn: {applicant.profile.linkedin_url or 'Not provided'}
GitHub: {applicant.profile.github_url or 'Not provided'}

Skills:
{skills_list}

Experience Summary:
{experience_summary}

Resume:
Attached with this email.

Message from Candidate:
{optional_message or 'No message provided.'}

Please review the application and connect with the candidate if interested.

Best regards,
JobSeek Platform
"""
    
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [job.posted_by.email],
    )
    
    # Attach resume if it exists
    if applicant.profile.resume:
        try:
            resume_path = applicant.profile.resume.path
            if os.path.exists(resume_path):
                email.attach_file(resume_path)
        except Exception as e:
            print(f"Error attaching resume: {e}")
            
    try:
        email.send()
        print(f"Application email sent to {job.posted_by.email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
