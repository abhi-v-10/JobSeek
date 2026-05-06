import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import LiquidEther from "../components/LiquidEther";
import TextType from "../components/TextType";
import { PulsatingButton } from "../components/ui/pulsating-button";
import CountUp from "../components/ui/CountUp";

// ─── Scroll-reveal hook ───────────────────────────────────────────────────────
// Fires once when the element enters the viewport; never resets.

function useInView(threshold = 0.2) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setInView(true);
      },
      { threshold, rootMargin: "0px 0px -80px 0px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, inView };
}

// ─── Animation helpers ────────────────────────────────────────────────────────

// Use specific properties so these don't bleed into card hover transitions
const fadeUp = (inView: boolean, delay = 0) => ({
  className: `transition-[opacity,transform] duration-900 ease-out ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`,
  style: { transitionDelay: `${delay}ms` },
});

const fadeLeft = (inView: boolean, delay = 0) => ({
  className: `transition-[opacity,transform] duration-900 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-8"}`,
  style: { transitionDelay: `${delay}ms` },
});

const fadeRight = (inView: boolean, delay = 0) => ({
  className: `transition-[opacity,transform] duration-900 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"}`,
  style: { transitionDelay: `${delay}ms` },
});

// ─── SVG Icons ────────────────────────────────────────────────────────────────

const SparklesIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
    />
  </svg>
);
const DocumentTextIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
    />
  </svg>
);
const TrendingUpIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941"
    />
  </svg>
);
const MagnifyingGlassIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
    />
  </svg>
);
const TargetIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
    />
  </svg>
);
const LightBulbIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
    />
  </svg>
);
const MapIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z"
    />
  </svg>
);
const CodeBracketIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
    />
  </svg>
);
const UsersIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
    />
  </svg>
);
const BriefcaseIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0M12 12.75h.008v.008H12v-.008Z"
    />
  </svg>
);
const ChatBubbleIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
    />
  </svg>
);
const BuildingIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21"
    />
  </svg>
);
const CheckIcon = ({ className = "w-5 h-5" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={2.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m4.5 12.75 6 6 9-13.5"
    />
  </svg>
);
const XMarkIcon = ({ className = "w-5 h-5" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={2.5}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M6 18 18 6M6 6l12 12"
    />
  </svg>
);
const ArrowRightIcon = ({ className = "w-5 h-5" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
    />
  </svg>
);
const ChevronDownIcon = ({ className = "w-6 h-6" }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m19.5 8.25-7.5 7.5-7.5-7.5"
    />
  </svg>
);

// ─── Shared UI Helpers ────────────────────────────────────────────────────────

const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <span className="inline-block text-indigo-400 text-xs font-bold uppercase tracking-[0.2em] mb-3">
    {children}
  </span>
);

const SectionTitle = ({
  label,
  title,
  subtitle,
  align = "center",
}: {
  label?: string;
  title: React.ReactNode;
  subtitle?: string;
  align?: "center" | "left";
}) => (
  <div className={`mb-14 ${align === "center" ? "text-center" : ""}`}>
    {label && <SectionLabel>{label}</SectionLabel>}
    <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 leading-tight">
      {title}
    </h2>
    {subtitle && (
      <p
        className={`text-zinc-400 text-lg leading-relaxed ${align === "center" ? "max-w-2xl mx-auto" : "max-w-xl"}`}
      >
        {subtitle}
      </p>
    )}
  </div>
);

// ─── Section 1: Hero ──────────────────────────────────────────────────────────

const HeroSection = ({ onGetStarted }: { onGetStarted: () => void }) => (
  <section className="relative min-h-screen flex flex-col items-center justify-center px-6 text-center overflow-hidden">
    <div className="relative z-10 max-w-4xl mx-auto space-y-6 animate-fade-in-up pointer-events-none">
      <TextType
        as="h1"
        text="JobSeek"
        className="text-6xl md:text-8xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-zinc-100 dark:to-zinc-500 pb-2"
        typingSpeed={90}
        pauseDuration={5000}
        showCursor={true}
        cursorCharacter="|"
      />
      <h2 className="text-2xl md:text-4xl font-bold text-white/90 leading-snug">
        Find Jobs. Build Careers. Grow Smarter.
      </h2>
      <p className="text-lg md:text-xl text-zinc-300 max-w-2xl mx-auto leading-relaxed">
        Not just a job portal — an AI-powered career platform. Upload your
        resume, get personalized job matches, detect skill gaps, and grow with
        SeekBot AI as your dedicated career agent.
      </p>
      <div className="pt-6 flex flex-col sm:flex-row gap-4 justify-center items-center pointer-events-auto">
        <div className="w-full sm:w-auto sm:min-w-[200px]">
          <PulsatingButton
            variant="ripple"
            pulseColor="#ffffff"
            onClick={onGetStarted}
            className="py-4 text-lg font-bold shadow-xl shadow-zinc-100/10 hover:scale-105 transition-transform bg-white text-zinc-900 w-full"
          >
            Get Started
          </PulsatingButton>
        </div>
        <a
          href="#seekbot"
          className="text-zinc-300 hover:text-white flex items-center gap-2 text-base font-medium transition-colors group"
        >
          Meet SeekBot
          <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </a>
      </div>
    </div>
    <a
      href="#what-is-jobseek"
      className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 text-zinc-500 hover:text-zinc-300 transition-colors animate-bounce"
    >
      <ChevronDownIcon className="w-7 h-7" />
    </a>
  </section>
);

// ─── Section 2: What Is JobSeek ───────────────────────────────────────────────

const comparisonPoints = [
  {
    label: "Job Search",
    traditional: "Keyword filters only",
    jobseek: "Natural language AI search",
  },
  {
    label: "Resume",
    traditional: "Upload & forget",
    jobseek: "AI analysis & auto skill extraction",
  },
  {
    label: "Match Insight",
    traditional: "None",
    jobseek: "AI-computed job match score",
  },
  {
    label: "Career Guidance",
    traditional: "None",
    jobseek: "Skill gaps, roadmaps & mentoring",
  },
  {
    label: "Projects",
    traditional: "Not covered",
    jobseek: "Tailored project recommendations",
  },
];

const whatCards = [
  {
    icon: <SparklesIcon />,
    title: "AI Job Matching",
    description:
      "SeekBot analyzes your skills, projects, and resume to surface best-fit jobs with a computed match score — so you apply with confidence.",
  },
  {
    icon: <DocumentTextIcon />,
    title: "Resume Intelligence",
    description:
      "Upload your resume once. SeekBot auto-extracts your tech stack, projects, certifications, and experience level to build your smart profile.",
  },
  {
    icon: <TrendingUpIcon />,
    title: "Career Growth Guidance",
    description:
      "From skill gap detection to learning roadmaps and project suggestions — JobSeek helps you become job-ready, not just job-searching.",
  },
];

const WhatIsJobSeekSection = () => {
  const { ref, inView } = useInView(0.1);
  return (
    <section id="what-is-jobseek" className="relative py-24 px-6">
      <div ref={ref} className="max-w-7xl mx-auto">
        <div {...fadeUp(inView)}>
          <SectionTitle
            label="What is JobSeek?"
            title="Not Just Another Job Portal"
            subtitle="Traditional job portals let you search and apply. JobSeek understands you — your skills, goals, and gaps — and builds your entire career path around them."
          />
        </div>

        {/* Comparison strip */}
        <div className="grid md:grid-cols-2 rounded-2xl overflow-hidden mb-16 border border-zinc-800/60">
          {/* Traditional column */}
          <div className="bg-zinc-950/60 p-8 border-r border-zinc-800/60">
            <h3 className="text-zinc-500 font-semibold text-xs uppercase tracking-widest mb-7">
              Traditional Portals
            </h3>
            <div className="space-y-5">
              {comparisonPoints.map((p, i) => (
                <div
                  key={p.label}
                  className={`flex items-start gap-3 transition-all duration-500 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-6"}`}
                  style={{ transitionDelay: `${i * 90}ms` }}
                >
                  <span className="mt-0.5 text-zinc-700 shrink-0">
                    <XMarkIcon className="w-4 h-4" />
                  </span>
                  <div>
                    <span className="text-zinc-500 text-sm font-medium">
                      {p.label}:{" "}
                    </span>
                    <span className="text-zinc-600 text-sm">
                      {p.traditional}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {/* JobSeek column */}
          <div className="bg-indigo-950/20 p-8">
            <h3 className="text-indigo-400 font-semibold text-xs uppercase tracking-widest mb-7">
              JobSeek
            </h3>
            <div className="space-y-5">
              {comparisonPoints.map((p, i) => (
                <div
                  key={p.label}
                  className={`flex items-start gap-3 transition-all duration-500 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 translate-x-6"}`}
                  style={{ transitionDelay: `${i * 90 + 200}ms` }}
                >
                  <span className="mt-0.5 text-indigo-400 shrink-0">
                    <CheckIcon className="w-4 h-4" />
                  </span>
                  <div>
                    <span className="text-zinc-200 text-sm font-medium">
                      {p.label}:{" "}
                    </span>
                    <span className="text-zinc-300 text-sm">{p.jobseek}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Feature cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {whatCards.map((card, i) => (
            <div
              key={card.title}
              className={fadeUp(inView, i * 100 + 500).className}
              style={fadeUp(inView, i * 100 + 500).style}
            >
              <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-6 h-full hover:border-indigo-500/40 hover:shadow-lg hover:shadow-indigo-900/20 transition-[border-color,box-shadow] duration-150">
                <div className="w-12 h-12 bg-indigo-500/10 rounded-lg flex items-center justify-center text-indigo-400 mb-5">
                  {card.icon}
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">
                  {card.title}
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  {card.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Section 3: SeekBot ───────────────────────────────────────────────────────

const seekbotCapabilities = [
  {
    icon: <DocumentTextIcon className="w-5 h-5" />,
    label: "Resume Analysis",
    desc: "Extracts skills, projects, and experience from your uploaded resume automatically.",
  },
  {
    icon: <SparklesIcon className="w-5 h-5" />,
    label: "Job Recommendations",
    desc: "Personalized job matches based on your profile, history, and career interests.",
  },
  {
    icon: <LightBulbIcon className="w-5 h-5" />,
    label: "Skill Gap Detection",
    desc: "Identifies missing skills for your target role and prioritizes what to learn first.",
  },
  {
    icon: <MapIcon className="w-5 h-5" />,
    label: "Career Roadmaps",
    desc: "Step-by-step growth paths to reach your dream role with timelines and milestones.",
  },
];

const exampleQueries = [
  {
    user: "I want a remote frontend internship",
    bot: "Found 12 remote frontend internships matching your profile. Top match: 88% — React Developer Intern at TechNova.",
  },
  {
    user: "Find Python jobs under 8 LPA",
    bot: "Here are 8 Python developer roles under 8 LPA. Your profile matches 5 of them with 70%+ score.",
  },
  {
    user: "How do I become a full stack developer?",
    bot: "Here's your 6-month Full Stack roadmap: HTML → React → Node.js → Databases → APIs → Deployment.",
  },
  {
    user: "What skills do I need for a Data Analyst?",
    bot: "You're missing SQL, Excel, and Power BI. I've added a learning path to your dashboard.",
  },
];

const SeekBotSection = () => {
  const { ref, inView } = useInView(0.1);
  return (
    <section id="seekbot" className="relative py-24 px-6">
      <div ref={ref} className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: content */}
          <div {...fadeLeft(inView)}>
            <SectionLabel>Powered by AI</SectionLabel>
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-5 leading-tight">
              Meet SeekBot —{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-400">
                Your AI Career Agent
              </span>
            </h2>
            <p className="text-zinc-400 text-lg mb-10 leading-relaxed">
              SeekBot is not just a chatbot. It's a smart, action-oriented
              career agent that understands your profile, analyzes your resume,
              recommends jobs, and guides your growth — all through natural
              conversation.
            </p>
            <div className="space-y-5">
              {seekbotCapabilities.map((cap, i) => (
                <div
                  key={cap.label}
                  className={`flex items-start gap-4 transition-all duration-500 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4"}`}
                  style={{ transitionDelay: `${i * 80 + 200}ms` }}
                >
                  <div className="w-10 h-10 bg-indigo-500/10 rounded-lg flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                    {cap.icon}
                  </div>
                  <div>
                    <h4 className="text-white font-semibold text-sm mb-1">
                      {cap.label}
                    </h4>
                    <p className="text-zinc-400 text-sm leading-relaxed">
                      {cap.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: chat demo — hover zoom + neon glow + macOS window buttons */}
          <div
            className={`transition-[opacity,transform] duration-900 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 translate-x-8"}`}
            style={{ transitionDelay: "150ms" }}
          >
            <div className="group bg-zinc-950/90 border border-zinc-800/70 rounded-2xl overflow-hidden shadow-2xl shadow-black/50 transition-[transform,border-color,box-shadow] duration-300 ease-out cursor-default hover:scale-[1.025] hover:border-indigo-400/60 hover:shadow-[0_0_0_1px_rgba(129,140,248,0.2),0_0_40px_rgba(99,102,241,0.2),0_0_80px_rgba(99,102,241,0.08)]">
              {/* Header */}
              <div className="flex items-center gap-3 px-5 py-4 border-b border-zinc-800/60 bg-zinc-900/60">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0">
                  <SparklesIcon className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">SeekBot AI</p>
                  <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                    Online
                  </span>
                </div>
                {/* macOS-style window dots: grey → red/yellow/green on card hover */}
                <div className="ml-auto flex gap-2">
                  <span className="w-3 h-3 rounded-full bg-zinc-700 group-hover:bg-red-500 transition-colors duration-200" />
                  <span className="w-3 h-3 rounded-full bg-zinc-700 group-hover:bg-yellow-400 transition-colors duration-200" />
                  <span className="w-3 h-3 rounded-full bg-zinc-700 group-hover:bg-green-500 transition-colors duration-200" />
                </div>
              </div>

              {/* Messages — show only 3 to keep card clean */}
              <div className="px-5 pt-5 pb-3 space-y-4">
                {exampleQueries.slice(0, 3).map((q, i) => (
                  <div key={i} className="space-y-2">
                    <div className="flex justify-end">
                      <div className="bg-indigo-600/20 border border-indigo-500/25 text-zinc-200 text-xs rounded-2xl rounded-tr-sm px-3.5 py-2 max-w-[85%]">
                        {q.user}
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="bg-zinc-800/70 text-zinc-300 text-xs rounded-2xl rounded-tl-sm px-3.5 py-2 max-w-[85%]">
                        <span className="text-indigo-400 font-semibold">
                          SeekBot:{" "}
                        </span>
                        {q.bot}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Input bar — flush styling, no excess padding */}
              <div className="px-4 py-4">
                <div className="flex items-center gap-3 bg-zinc-800/60 border border-zinc-700/40 rounded-xl px-4 py-2.5">
                  <span className="text-zinc-500 text-xs flex-1">
                    Ask SeekBot anything...
                  </span>
                  <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
                    <ArrowRightIcon className="w-3 h-3 text-white" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ─── Section 4: Features Grid ─────────────────────────────────────────────────

const features = [
  {
    icon: <DocumentTextIcon />,
    title: "Resume Analysis",
    description:
      "Upload your resume and SeekBot auto-extracts skills, frameworks, projects, certifications, and experience level to build your intelligent profile.",
  },
  {
    icon: <MagnifyingGlassIcon />,
    title: "AI Job Search",
    description:
      'Search jobs using plain language — "remote React internship" or "Django backend under 8 LPA" — no manual filters required.',
  },
  {
    icon: <TargetIcon />,
    title: "Job Match Score",
    description:
      "For every job you view, see your eligibility score, matching skills, missing skills, and how strong your profile is for the role.",
  },
  {
    icon: <LightBulbIcon />,
    title: "Skill Gap Detection",
    description:
      "SeekBot identifies exactly which skills you're missing for your target role and gives you a prioritized learning path.",
  },
  {
    icon: <CodeBracketIcon />,
    title: "Project Recommendations",
    description:
      "Get tailored project ideas (e-commerce site, auth API, admin dashboard) to build a portfolio aligned to your target roles.",
  },
  {
    icon: <MapIcon />,
    title: "Career Roadmaps",
    description:
      'Ask "how do I become a full stack developer in 6 months?" and get a structured milestone plan with timelines.',
  },
];

const FeaturesSection = () => {
  const { ref, inView } = useInView(0.1);
  return (
    <section className="relative py-24 px-6">
      <div ref={ref} className="max-w-7xl mx-auto">
        <div {...fadeUp(inView)}>
          <SectionTitle
            label="Features"
            title="Everything You Need to Grow"
            subtitle="Six core capabilities that make JobSeek a complete career ecosystem, not just a listing board."
          />
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div
              key={f.title}
              className={fadeUp(inView, i * 80 + 100).className}
              style={fadeUp(inView, i * 80 + 100).style}
            >
              <div className="group bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-6 h-full hover:border-indigo-500/40 hover:shadow-lg hover:shadow-indigo-900/20 transition-[border-color,box-shadow] duration-150">
                <div className="w-12 h-12 bg-indigo-500/10 rounded-xl flex items-center justify-center text-indigo-400 mb-5 group-hover:bg-indigo-500/20 transition-colors duration-150">
                  {f.icon}
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">
                  {f.title}
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  {f.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Section 5: How It Works ──────────────────────────────────────────────────

const steps = [
  {
    icon: <DocumentTextIcon className="w-7 h-7" />,
    title: "Upload Resume / Create Profile",
    description:
      "Sign up and upload your resume (PDF/DOCX). SeekBot scans it instantly and fills in your skills, projects, and experience level automatically.",
  },
  {
    icon: <SparklesIcon className="w-7 h-7" />,
    title: "SeekBot Analyzes Your Profile",
    description:
      "SeekBot maps your tech stack, detects your experience level, identifies your strongest areas, and computes job match scores across all listings.",
  },
  {
    icon: <TrendingUpIcon className="w-7 h-7" />,
    title: "Get Personalized Jobs & Career Insights",
    description:
      "Receive tailored job recommendations, know exactly where your gaps are, follow a career roadmap, and grow into your dream role strategically.",
  },
];

const HowItWorksSection = () => {
  const { ref, inView } = useInView(0.1);
  return (
    <section className="relative py-24 px-6">
      <div ref={ref} className="max-w-7xl mx-auto">
        <div {...fadeUp(inView)}>
          <SectionTitle
            label="How It Works"
            title="Three Steps to Your Next Career Move"
            subtitle="JobSeek turns a complex job search into a clear, personalized, and AI-guided journey."
          />
        </div>
        <div className="grid md:grid-cols-3 gap-8 relative">
          <div className="hidden md:block absolute top-12 left-[calc(16.66%-12px)] right-[calc(16.66%-12px)] h-px bg-gradient-to-r from-transparent via-indigo-500/25 to-transparent z-0" />
          {steps.map((step, i) => (
            <div
              key={i}
              className={`relative z-10 flex flex-col items-center text-center transition-all duration-700 ease-out ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"}`}
              style={{ transitionDelay: `${i * 150}ms` }}
            >
              <div className="relative mb-6">
                <div className="w-20 h-20 rounded-2xl bg-zinc-900/90 border border-zinc-800/60 flex items-center justify-center text-indigo-400 shadow-lg shadow-black/30">
                  {step.icon}
                </div>
                <span className="absolute -top-3 -right-3 w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </span>
              </div>
              <h3 className="text-white font-semibold text-lg mb-3">
                {step.title}
              </h3>
              <p className="text-zinc-400 text-sm leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Section 6: Career Growth ─────────────────────────────────────────────────

const growthPoints = [
  {
    icon: <MapIcon />,
    title: "Personalized Learning Paths",
    description:
      "SeekBot creates a custom learning roadmap — beginner to advanced — for any role you aspire to, with estimated timelines.",
  },
  {
    icon: <CodeBracketIcon />,
    title: "Build the Right Projects",
    description:
      "Stop building random projects. Get targeted suggestions (auth APIs, dashboards, e-commerce apps) that directly strengthen your target role portfolio.",
  },
  {
    icon: <DocumentTextIcon />,
    title: "Resume Improvement",
    description:
      "For any specific job, SeekBot suggests exactly how to improve your resume — keywords, project highlights, ATS optimization — to boost interview chances.",
  },
  {
    icon: <SparklesIcon />,
    title: "Career Strategy Guidance",
    description:
      'Ask any career question — "Is Java worth learning?", "React vs Angular in 2026?", "How to switch to backend?" — and get expert-level AI guidance.',
  },
];

const CareerGrowthSection = () => {
  const { ref, inView } = useInView(0.1);
  return (
    <section className="relative py-24 px-6">
      <div ref={ref} className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left */}
          <div {...fadeLeft(inView)}>
            <SectionLabel>Career Growth</SectionLabel>
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-5 leading-tight">
              Don't Just Find a Job.{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-400">
                Build a Career.
              </span>
            </h2>
            <p className="text-zinc-400 text-lg mb-10 leading-relaxed">
              JobSeek is designed to help you grow beyond your current level —
              with AI-powered guidance on what to learn, what to build, and how
              to position yourself for the role you want.
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              {growthPoints.map((g, i) => (
                <div
                  key={g.title}
                  className={fadeUp(inView, i * 80 + 300).className}
                  style={fadeUp(inView, i * 80 + 300).style}
                >
                  <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-5 h-full hover:border-indigo-500/30 hover:shadow-md hover:shadow-indigo-900/15 transition-[border-color,box-shadow] duration-150">
                    <div className="text-indigo-400 mb-3">{g.icon}</div>
                    <h4 className="text-white font-semibold text-sm mb-1.5">
                      {g.title}
                    </h4>
                    <p className="text-zinc-400 text-xs leading-relaxed">
                      {g.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: snapshot card */}
          <div {...fadeRight(inView, 150)}>
            <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-2xl p-8">
              <h3 className="text-white font-semibold text-lg mb-7 flex items-center gap-2">
                <SparklesIcon className="w-5 h-5 text-indigo-400" />
                SeekBot Career Snapshot
              </h3>
              {[
                {
                  label: "Current Level",
                  value: "Frontend Developer (Intermediate)",
                  dot: "bg-blue-500",
                },
                {
                  label: "Target Role",
                  value: "Full Stack Engineer",
                  dot: "bg-violet-500",
                },
                {
                  label: "Skills to Learn",
                  value: "Node.js, PostgreSQL, Docker",
                  dot: "bg-amber-500",
                },
                {
                  label: "Suggested Projects",
                  value: "REST API + Blog Platform + Auth System",
                  dot: "bg-emerald-500",
                },
                {
                  label: "Estimated Timeline",
                  value: "3–4 months with consistent effort",
                  dot: "bg-rose-500",
                },
              ].map((item, i) => (
                <div
                  key={item.label}
                  className={`flex items-start gap-3 mb-4 transition-all duration-500 ease-out ${inView ? "opacity-100 translate-x-0" : "opacity-0 translate-x-4"}`}
                  style={{ transitionDelay: `${i * 80 + 300}ms` }}
                >
                  <span
                    className={`w-2 h-2 rounded-full mt-2 shrink-0 ${item.dot}`}
                  />
                  <div>
                    <span className="text-zinc-500 text-xs font-medium block mb-0.5">
                      {item.label}
                    </span>
                    <span className="text-zinc-200 text-sm">{item.value}</span>
                  </div>
                </div>
              ))}
              <div className="mt-4 pt-5 border-t border-zinc-800/60">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-zinc-400 text-xs">
                    Profile Completion
                  </span>
                  <span className="text-indigo-400 text-xs font-semibold">
                    72%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-1000 ease-out ${inView ? "w-[72%]" : "w-0"}`}
                    style={{ transitionDelay: "800ms" }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ─── Section 7: Testimonials Carousel ────────────────────────────────────────

const allTestimonials = [
  {
    name: "Priya Sharma",
    role: "Data Analyst Intern · Bangalore",
    avatar: "PS",
    quote:
      "SeekBot identified that I was missing SQL and Power BI for data analyst roles and gave me a clear 3-month roadmap. Within 2 months, I landed my first internship. This platform actually understands what you need.",
  },
  {
    name: "Rahul Mehta",
    role: "React Developer · Pune",
    avatar: "RM",
    quote:
      "The job match score changed how I apply. Instead of blind applications, I now know exactly where I stand for each role. Found a React position at 84% match and got an interview in the first week.",
  },
  {
    name: "Anika Reddy",
    role: "Full Stack Aspirant · Hyderabad",
    avatar: "AR",
    quote:
      'I asked SeekBot "how do I become a full stack developer?" and got a step-by-step plan with projects, resources, and timelines. It feels like having a senior mentor available 24/7.',
  },
  {
    name: "Kiran Patel",
    role: "Backend Developer · Mumbai",
    avatar: "KP",
    quote:
      "JobSeek helped me understand exactly which projects to build to land a backend role. The project recommendations were spot-on — my resume improved drastically within a month.",
  },
  {
    name: "Sneha Nair",
    role: "UI/UX Designer · Kochi",
    avatar: "SN",
    quote:
      "I switched careers from graphic design to UI/UX and SeekBot mapped out my entire transition path — what tools to learn, what portfolio projects to do, and which companies to target.",
  },
  {
    name: "Arjun Kumar",
    role: "DevOps Engineer · Bangalore",
    avatar: "AK",
    quote:
      "The skill gap feature is a game-changer. SeekBot told me I needed Docker and Kubernetes before I could apply for senior roles. I focused on those and doubled my interview calls.",
  },
];

// ─── Testimonials: pure-CSS infinite marquee ─────────────────────────────────
// CARD_STEP = card-width + gap-right  →  moving by N*CARD_STEP loops seamlessly
const T_CARD_W = 380;
const T_CARD_GAP = 24;
const T_CARD_STEP = T_CARD_W + T_CARD_GAP; // 404 px per slot
const T_TOTAL_W = allTestimonials.length * T_CARD_STEP; // 2424 px = one full loop

const TestimonialsSection = () => {
  const { ref: titleRef, inView: titleInView } = useInView(0.1);
  const [isPaused, setIsPaused] = useState(false);
  const doubled = [...allTestimonials, ...allTestimonials];

  return (
    <section className="relative py-24 overflow-hidden">
      {/* Inject the keyframe — value is static so this is safe */}
      <style>{`
        @keyframes t-marquee {
          from { transform: translateX(0); }
          to   { transform: translateX(-${T_TOTAL_W}px); }
        }
      `}</style>

      {/* Title stays within page max-width */}
      <div ref={titleRef} className="px-6 max-w-7xl mx-auto mb-12">
        <div {...fadeUp(titleInView)}>
          <SectionTitle
            label="Testimonials"
            title="What Our Users Say"
            subtitle="Real stories from job seekers who grew their careers with JobSeek and SeekBot."
          />
        </div>
      </div>

      {/* Edge-to-edge scrolling track */}
      <div className="overflow-hidden">
        <div
          style={{
            display: "flex",
            width: `${doubled.length * T_CARD_STEP}px`,
            animation: `t-marquee 38s linear infinite`,
            animationPlayState: isPaused ? "paused" : "running",
          }}
        >
          {doubled.map((t, i) => (
            <div
              key={i}
              style={{
                width: T_CARD_W,
                marginRight: T_CARD_GAP,
                flexShrink: 0,
              }}
              onMouseEnter={() => setIsPaused(true)}
              onMouseLeave={() => setIsPaused(false)}
            >
              <div className="bg-zinc-900/80 border border-zinc-800/60 rounded-xl p-6 flex flex-col h-full cursor-default hover:border-indigo-500/40 hover:shadow-lg hover:shadow-indigo-900/20 transition-[border-color,box-shadow] duration-150">
                <div className="text-indigo-400/30 text-4xl font-serif leading-none mb-4 select-none">
                  "
                </div>
                <p className="text-zinc-300 text-sm leading-relaxed flex-1 mb-6">
                  {t.quote}
                </p>
                <div className="flex items-center gap-3 pt-4 border-t border-zinc-800/60">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
                    {t.avatar}
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm">{t.name}</p>
                    <p className="text-zinc-500 text-xs">{t.role}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Section 8: Stats ─────────────────────────────────────────────────────────

const stats = [
  {
    icon: <BriefcaseIcon className="w-7 h-7" />,
    countTo: 99,
    separator: ",",
    suffix: "+",
    label: "Jobs Listed",
    sub: "Corporate & domestic roles",
  },
  {
    icon: <UsersIcon className="w-7 h-7" />,
    countTo: 500,
    separator: ",",
    suffix: "+",
    label: "Active Users",
    sub: "Job seekers & recruiters",
  },
  {
    icon: <TargetIcon className="w-7 h-7" />,
    countTo: 90,
    separator: "",
    prefix: "~",
    suffix: "%+",
    label: "Match Accuracy",
    sub: "AI-powered relevance",
  },
  {
    icon: <BuildingIcon className="w-7 h-7" />,
    countTo: 200,
    separator: "",
    suffix: "+",
    label: "Partner Companies",
    sub: "Hiring via JobSeek",
  },
];

const StatsSection = () => {
  const { ref, inView } = useInView(0.2);
  return (
    <section className="relative py-20 px-6">
      <div ref={ref} className="relative z-10 max-w-7xl mx-auto">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((s, i) => (
            <div
              key={s.label}
              className={`flex flex-col items-center text-center group ${fadeUp(inView, i * 100).className}`}
              style={fadeUp(inView, i * 100).style}
            >
              <div className="w-14 h-14 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 mb-4 group-hover:bg-indigo-500/20 transition-colors">
                {s.icon}
              </div>
              {/* Animated number + suffix */}
              <div className="text-3xl md:text-4xl font-black text-white mb-1 tabular-nums">
                <CountUp
                  from={0}
                  to={s.countTo}
                  separator={s.separator}
                  direction="up"
                  duration={2.2}
                  delay={i * 0.15}
                  startWhen={inView}
                  className=""
                />
                <span>{s.suffix}</span>
              </div>
              <div className="text-zinc-300 font-semibold text-sm mb-1">
                {s.label}
              </div>
              <div className="text-zinc-600 text-xs">{s.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Section 9: Why Choose JobSeek ───────────────────────────────────────────

const comparisonRows = [
  // Features both platforms offer
  { feature: "Job Listings & Search", jobseek: true, traditional: true },
  { feature: "Apply to Jobs", jobseek: true, traditional: true },
  { feature: "User Profiles", jobseek: true, traditional: true },
  // JobSeek-exclusive AI capabilities
  { feature: "AI-Powered Job Matching", jobseek: true, traditional: false },
  { feature: "Resume Intelligence", jobseek: true, traditional: false },
  { feature: "Job Match Score", jobseek: true, traditional: false },
  { feature: "Skill Gap Detection", jobseek: true, traditional: false },
  { feature: "Career Roadmaps & Guidance", jobseek: true, traditional: false },
];

const WhyChooseSection = () => {
  const { ref, inView } = useInView(0.1);
  return (
    <section className="relative py-24 px-6">
      <div ref={ref} className="max-w-4xl mx-auto">
        <div {...fadeUp(inView)}>
          <SectionTitle
            label="Why Choose JobSeek?"
            title={
              <>
                JobSeek vs{" "}
                <span className="text-zinc-500">Traditional Job Portals</span>
              </>
            }
            subtitle="See exactly what you gain by choosing an AI-driven career platform over a basic listing board."
          />
        </div>
        <div
          className={`rounded-2xl overflow-hidden border border-zinc-800/60 transition-all duration-700 ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}
          style={{ transitionDelay: "200ms" }}
        >
          <div className="grid grid-cols-3 bg-zinc-900/70 border-b border-zinc-800/60">
            <div className="col-span-1 px-6 py-4 text-zinc-500 text-sm font-semibold">
              Feature
            </div>
            <div className="col-span-1 px-6 py-4 text-indigo-400 text-sm font-bold text-center bg-indigo-500/5">
              JobSeek
            </div>
            <div className="col-span-1 px-6 py-4 text-zinc-500 text-sm font-semibold text-center">
              Traditional
            </div>
          </div>
          {comparisonRows.map((row, i) => (
            <div
              key={row.feature}
              className={`grid grid-cols-3 border-b border-zinc-800/40 bg-zinc-950/50 transition-all duration-400 ease-out ${inView ? "opacity-100" : "opacity-0"}`}
              style={{ transitionDelay: `${i * 40 + 300}ms` }}
            >
              <div className="col-span-1 px-6 py-3.5 text-zinc-300 text-sm">
                {row.feature}
              </div>
              <div className="col-span-1 px-6 py-3.5 flex justify-center items-center bg-indigo-500/5">
                {row.jobseek ? (
                  <CheckIcon className="w-5 h-5 text-indigo-400" />
                ) : (
                  <XMarkIcon className="w-5 h-5 text-zinc-700" />
                )}
              </div>
              <div className="col-span-1 px-6 py-3.5 flex justify-center items-center">
                {row.traditional ? (
                  <CheckIcon className="w-5 h-5 text-zinc-500" />
                ) : (
                  <XMarkIcon className="w-5 h-5 text-zinc-700" />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Section 10: CTA ──────────────────────────────────────────────────────────

const CTASection = ({ onGetStarted }: { onGetStarted: () => void }) => {
  const { ref, inView } = useInView(0.2);
  return (
    <section className="relative py-24 px-6">
      <div ref={ref} className="max-w-4xl mx-auto text-center">
        <div
          className={`inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-4 py-1.5 mb-8 transition-all duration-700 ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
        >
          <SparklesIcon className="w-4 h-4 text-indigo-400" />
          <span className="text-indigo-300 text-sm font-medium">
            Powered by SeekBot AI
          </span>
        </div>
        <h2
          className={`text-3xl md:text-5xl font-black text-white mb-6 leading-tight transition-all duration-700 ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}
          style={{ transitionDelay: "100ms" }}
        >
          Stop applying blindly.{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-violet-400">
            Start applying intelligently.
          </span>
        </h2>
        <p
          className={`text-zinc-400 text-lg mb-10 max-w-xl mx-auto leading-relaxed transition-all duration-700 ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}
          style={{ transitionDelay: "200ms" }}
        >
          Join thousands of job seekers who let SeekBot guide their job search,
          close skill gaps, and build careers — not just resumes.
        </p>
        <div
          className={`flex flex-col sm:flex-row justify-center gap-4 transition-all duration-700 ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}
          style={{ transitionDelay: "300ms" }}
        >
          <PulsatingButton
            variant="ripple"
            pulseColor="#ffffff"
            onClick={onGetStarted}
            className="py-4 px-8 text-lg font-bold shadow-xl shadow-zinc-100/10 hover:scale-105 transition-transform bg-white text-zinc-900"
          >
            Get Started — It's Free
          </PulsatingButton>
          <a
            href="/seekbot"
            className="inline-flex items-center justify-center gap-2 px-8 py-4 text-base font-semibold text-white border border-zinc-700/60 rounded-lg hover:border-indigo-500/50 hover:bg-zinc-900/40 transition-all"
          >
            <ChatBubbleIcon className="w-5 h-5" />
            Try SeekBot
          </a>
        </div>
      </div>
    </section>
  );
};

// ─── Section 11: Contact ──────────────────────────────────────────────────────

const ContactSection = () => {
  const { ref, inView } = useInView(0.1);
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const subject = encodeURIComponent(`JobSeek Contact — ${form.name}`);
    const body = encodeURIComponent(
      `Name: ${form.name}\nEmail: ${form.email}\n\nMessage:\n${form.message}`,
    );
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=jobseek.applications@gmail.com&su=${subject}&body=${body}`;
    window.open(gmailUrl, "_blank", "noopener,noreferrer");
    setSent(true);
    setForm({ name: "", email: "", message: "" });
  };

  return (
    <section id="contact" className="relative py-24 px-6">
      <div ref={ref} className="max-w-2xl mx-auto">
        <div {...fadeUp(inView)}>
          <SectionTitle
            label="Get In Touch"
            title="Have Questions? Let's Talk."
            subtitle="Reach out with any questions about JobSeek, partnership opportunities, or feedback."
          />
        </div>

        {sent ? (
          <div
            className={`bg-zinc-900/80 border border-emerald-500/30 rounded-xl p-8 text-center ${fadeUp(inView).className}`}
            style={fadeUp(inView).style}
          >
            <div className="w-14 h-14 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckIcon className="w-7 h-7 text-emerald-400" />
            </div>
            <h3 className="text-white font-semibold text-lg mb-2">
              Message Sent!
            </h3>
            <p className="text-zinc-400 text-sm">
              We'll get back to you as soon as possible.
            </p>
            <button
              onClick={() => setSent(false)}
              className="mt-6 text-indigo-400 hover:text-indigo-300 text-sm font-medium transition-colors"
            >
              Send another message
            </button>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className={`space-y-5 ${fadeUp(inView, 150).className}`}
            style={fadeUp(inView, 150).style}
          >
            {[
              {
                label: "Name",
                key: "name",
                type: "text",
                placeholder: "Your full name",
              },
              {
                label: "Email",
                key: "email",
                type: "email",
                placeholder: "you@example.com",
              },
            ].map((field) => (
              <div key={field.key}>
                <label className="block text-zinc-400 text-sm font-medium mb-1.5">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  required
                  value={form[field.key as keyof typeof form]}
                  onChange={(e) =>
                    setForm({ ...form, [field.key]: e.target.value })
                  }
                  placeholder={field.placeholder}
                  className="w-full bg-zinc-900/70 border border-zinc-800/60 rounded-xl px-4 py-3 text-white placeholder-zinc-600 text-sm focus:outline-none focus:border-indigo-500/50 transition-colors"
                />
              </div>
            ))}
            <div>
              <label className="block text-zinc-400 text-sm font-medium mb-1.5">
                Message
              </label>
              <textarea
                required
                rows={5}
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                placeholder="How can we help you?"
                className="w-full bg-zinc-900/70 border border-zinc-800/60 rounded-xl px-4 py-3 text-white placeholder-zinc-600 text-sm focus:outline-none focus:border-indigo-500/50 transition-colors resize-none"
              />
            </div>
            <button
              type="submit"
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3.5 rounded-xl transition-colors text-sm flex items-center justify-center gap-2 group"
            >
              Send Message
              <ArrowRightIcon className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>
        )}
      </div>
    </section>
  );
};

// ─── Section 12: Footer ───────────────────────────────────────────────────────

const FooterSection = () => (
  <footer className="relative py-12 px-6 bg-zinc-950/60">
    <div className="max-w-7xl mx-auto">
      <div className="grid md:grid-cols-4 gap-10 mb-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <SparklesIcon className="w-4 h-4 text-white" />
            </div>
            <span className="text-white font-black text-xl tracking-tight">
              JobSeek
            </span>
          </div>
          <p className="text-zinc-500 text-sm leading-relaxed max-w-xs">
            An AI-powered career platform. Find jobs, build skills, and grow
            smarter — with SeekBot as your personal career agent.
          </p>
          <div className="flex gap-3 mt-5">
            {[
              {
                label: "LinkedIn",
                href: "https://www.linkedin.com/in/abhishyanth-v/",
              },
              { label: "GitHub", href: "https://github.com/abhi-v-10" },
            ].map((s) => (
              <a
                key={s.label}
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-600 hover:text-zinc-300 text-xs border border-zinc-800/60 hover:border-zinc-600 rounded-lg px-3 py-1.5 transition-all"
              >
                {s.label}
              </a>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-zinc-400 text-xs font-semibold uppercase tracking-widest mb-4">
            Product
          </h4>
          <ul className="space-y-2.5">
            {[
              { label: "Browse Jobs", href: "/jobs" },
              { label: "SeekBot AI", href: "/seekbot" },
              { label: "Post a Job", href: "/post-job" },
              { label: "My Profile", href: "/profile" },
            ].map((l) => (
              <li key={l.label}>
                <a
                  href={l.href}
                  className="text-zinc-500 hover:text-zinc-200 text-sm transition-colors"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="text-zinc-400 text-xs font-semibold uppercase tracking-widest mb-4">
            Company
          </h4>
          <ul className="space-y-2.5">
            {[
              { label: "About", href: "#" },
              { label: "Contact", href: "#contact" },
              { label: "Terms of Service", href: "#" },
              { label: "Privacy Policy", href: "#" },
            ].map((l) => (
              <li key={l.label}>
                <a
                  href={l.href}
                  className="text-zinc-500 hover:text-zinc-200 text-sm transition-colors"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="pt-8 border-t border-zinc-800/40 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <p className="text-zinc-600 text-xs">
            © {new Date().getFullYear()} JobSeek. All rights reserved.
          </p>
          <span className="hidden sm:inline text-zinc-700 text-xs">·</span>
          <p className="text-zinc-600 text-xs">
            Developed by{" "}
            <a
              href="https://github.com/abhi-v-10"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
            >
              abhi-v-10
            </a>
          </p>
        </div>
        <p className="text-zinc-600 text-xs flex items-center gap-1.5">
          Powered by
          <span className="text-indigo-500 font-medium">SeekBot AI</span>
          <SparklesIcon className="w-3.5 h-3.5 text-indigo-500" />
        </p>
      </div>
    </div>
  </footer>
);

// ─── Main Landing Component ───────────────────────────────────────────────────

const Landing = () => {
  const navigate = useNavigate();

  const handleGetStarted = () => {
    const isLoggedIn = !!localStorage.getItem("access_token");
    navigate(isLoggedIn ? "/jobs" : "/login");
  };

  return (
    <div className="dark flex flex-col text-white">
      {/* Single global LiquidEther canvas — fixed behind all sections */}
      <div className="fixed inset-0 z-0 pointer-events-auto">
        <LiquidEther
          colors={["#5227FF", "#1c0ab8", "#5b69b9"]}
          mouseForce={15}
          cursorSize={100}
          isViscous={false}
          viscous={30}
          iterationsViscous={32}
          iterationsPoisson={32}
          resolution={0.5}
          isBounce={true}
          autoDemo={true}
          autoSpeed={0.4}
          autoIntensity={3.5}
          takeoverDuration={0.25}
          autoResumeDelay={1000}
          autoRampDuration={0.6}
        />
      </div>

      <HeroSection onGetStarted={handleGetStarted} />
      <WhatIsJobSeekSection />
      <SeekBotSection />
      <FeaturesSection />
      <HowItWorksSection />
      <CareerGrowthSection />
      <TestimonialsSection />
      <StatsSection />
      <WhyChooseSection />
      <CTASection onGetStarted={handleGetStarted} />
      <ContactSection />
      <FooterSection />
    </div>
  );
};

export default Landing;
