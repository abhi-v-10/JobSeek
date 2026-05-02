import React from 'react';
import { useNavigate } from 'react-router-dom';
import LiquidEther from '../components/LiquidEther';
import TextType from '../components/TextType';
import { PulsatingButton } from '../components/ui/pulsating-button';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="dark flex-1 flex flex-col items-center justify-center p-6 text-center relative overflow-hidden bg-zinc-950">
      <div className="absolute inset-0 z-0 pointer-events-auto">
        <LiquidEther
          colors={['#5227FF', '#1c0ab8', '#5b69b9']}
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

      <div className="relative z-10 max-w-3xl mx-auto space-y-8 animate-fade-in-up pointer-events-none">

        <TextType
          as="h1"
          text="JobSeek"
          className="text-6xl md:text-8xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-zinc-100 dark:to-zinc-500 pb-2"
          typingSpeed={90}
          pauseDuration={5000}
          showCursor={true}
          cursorCharacter="|"
        />
        <p className="text-xl md:text-2xl text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto leading-relaxed">
          Discover your next career opportunity or find the perfect candidate for your team with our intelligent matching platform.
        </p>
        <div className="pt-8 flex justify-center pointer-events-auto">
          <div className="w-full max-w-xs">
            <PulsatingButton
              variant="ripple"
              pulseColor="#ffffff"
              onClick={() => {
                const isLoggedIn = !!localStorage.getItem('access_token');
                navigate(isLoggedIn ? '/jobs' : '/login');
              }}
              className="py-4 text-lg font-bold shadow-xl shadow-zinc-100/10 hover:scale-105 transition-transform bg-white text-zinc-900 w-full"
            >
              Start now !!
            </PulsatingButton>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Landing;
