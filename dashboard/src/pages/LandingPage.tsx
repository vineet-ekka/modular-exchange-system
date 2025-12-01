import React from 'react';
import { Boxes } from '../components/ui/background-boxes';
import { cn } from '../lib/utils';

const LandingPage: React.FC = () => {
  return (
    <div className="h-screen max-h-screen w-full overflow-hidden bg-slate-900 flex items-center justify-center relative">
      <div className="absolute inset-0 w-full h-full bg-slate-900 z-20 [mask-image:radial-gradient(transparent,white)] pointer-events-none" />
      <Boxes />
      <div className="relative z-20 text-center px-4 sm:px-6 md:px-8 max-w-xs sm:max-w-xl md:max-w-3xl lg:max-w-4xl mx-auto">
        <img
          src="/basispoint-logo.png"
          alt="BasisPoint"
          className={cn(
            'w-full max-w-xs sm:max-w-md md:max-w-lg lg:max-w-xl xl:max-w-2xl',
            'mx-auto mb-6 sm:mb-8 md:mb-10'
          )}
          style={{ mixBlendMode: 'screen' }}
        />
        <p
          className={cn(
            'text-sm sm:text-base md:text-lg lg:text-xl',
            'text-slate-300 leading-relaxed font-normal'
          )}
          style={{ fontFamily: "'Helvetica Neue', Helvetica, Arial, sans-serif" }}
        >
          We are building the next generation protocol for liquidity provision, on-chain asset and treasury management and data
        </p>
      </div>
    </div>
  );
};

export default LandingPage;
