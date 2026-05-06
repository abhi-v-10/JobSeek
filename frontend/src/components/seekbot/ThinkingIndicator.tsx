import React, { useState, useEffect } from "react";

// ── Dynamic phrases that cycle while the AI is processing ─────────────────────
const THINKING_PHRASES = [
  "Strategizing",
  "Scanning market fit",
  "Evaluating stack",
  "Extracting impact",
  "Finalizing verdict",
];

const ThinkingIndicator: React.FC = () => {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [dotCount, setDotCount] = useState(1);

  // Cycle through phrases every 2.5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % THINKING_PHRASES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  // Animate dots: 1 → 2 → 3 → 1
  useEffect(() => {
    const interval = setInterval(() => {
      setDotCount((prev) => (prev % 3) + 1);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  const phrase = THINKING_PHRASES[phraseIndex];
  const dots = ".".repeat(dotCount);
  // Invisible dots to prevent layout shift
  const padDots = ".".repeat(3 - dotCount);

  return (
    <div className="inline-flex items-center gap-3 py-1">
      {/* Pulsing orb */}
      <div className="relative flex items-center justify-center w-5 h-5">
        <span className="absolute w-5 h-5 rounded-full bg-indigo-500/20 animate-ping" />
        <span className="relative w-2.5 h-2.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
      </div>

      {/* Cycling text */}
      <span className="text-sm text-zinc-400 font-medium transition-all duration-300">
        <span
          key={phrase}
          className="inline-block animate-fade-in"
        >
          {phrase}
        </span>
        <span className="text-zinc-500">{dots}</span>
        <span className="invisible">{padDots}</span>
      </span>
    </div>
  );
};

export default ThinkingIndicator;
