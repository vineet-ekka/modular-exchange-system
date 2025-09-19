import React, { useState, useEffect } from 'react';
import Header from '../components/Layout/Header';
import StatCard from '../components/Cards/StatCard';
import LiveFundingTicker from '../components/Ticker/LiveFundingTicker';
import FundingCountdown from '../components/Ticker/FundingCountdown';
import clsx from 'clsx';

const UIKitPage: React.FC = () => {
  const [activeSection, setActiveSection] = useState('glassmorphism');
  const [copiedText, setCopiedText] = useState<string | null>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [animationKey, setAnimationKey] = useState(0);

  // Trigger animations on section change
  useEffect(() => {
    setAnimationKey(prev => prev + 1);
  }, [activeSection]);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(label);
    setTimeout(() => setCopiedText(null), 2000);
  };

  // Add glassmorphism section
  const renderGlassmorphismSection = () => (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        Glassmorphism Components
      </h2>

      {/* Glassmorphic Cards */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Glass Cards</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Basic Glass Card */}
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl blur-xl opacity-30"></div>
            <div className="relative backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <h4 className="text-lg font-semibold text-gray-900 mb-2">Glass Card</h4>
              <p className="text-gray-700 text-sm">This card uses backdrop blur and transparency for a frosted glass effect.</p>
              <div className="mt-4 flex gap-2">
                <span className="px-2 py-1 text-xs rounded-full bg-white/20 backdrop-blur">Modern</span>
                <span className="px-2 py-1 text-xs rounded-full bg-white/20 backdrop-blur">Glass</span>
              </div>
            </div>
          </div>

          {/* Gradient Glass Card */}
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-br from-pink-500 via-purple-500 to-indigo-500 rounded-2xl blur-xl opacity-40"></div>
            <div className="relative backdrop-blur-xl bg-gradient-to-br from-white/20 to-white/5 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <div className="text-2xl mb-2">💎</div>
              <h4 className="text-lg font-semibold text-gray-900">Premium Glass</h4>
              <p className="text-gray-700 text-sm mt-2">Gradient background with glass morphism overlay effect.</p>
            </div>
          </div>

          {/* Data Glass Card */}
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-green-500 to-blue-500 rounded-2xl blur-xl opacity-30"></div>
            <div className="relative backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl p-6 shadow-2xl">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <p className="text-sm text-gray-600">Total Volume</p>
                  <p className="text-2xl font-bold text-gray-900">$2.4M</p>
                </div>
                <span className="text-green-500 text-sm">+12.5%</span>
              </div>
              <div className="h-12 flex items-end gap-1">
                {[40, 65, 45, 70, 55, 80, 60].map((h, i) => (
                  <div key={i} className="flex-1 bg-gradient-to-t from-blue-500/50 to-green-500/50 rounded-t backdrop-blur" style={{ height: `${h}%` }}></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Glass Buttons */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Glass Buttons</h3>
        <div className="flex flex-wrap gap-4">
          <button className="px-6 py-3 backdrop-blur-xl bg-white/20 border border-white/30 rounded-xl hover:bg-white/30 transition-all duration-300 shadow-xl">
            Glass Button
          </button>
          <button className="px-6 py-3 backdrop-blur-xl bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-white/30 rounded-xl hover:from-blue-500/30 hover:to-purple-500/30 transition-all duration-300 shadow-xl">
            Gradient Glass
          </button>
          <button className="px-6 py-3 backdrop-blur-xl bg-black/20 border border-white/10 text-white rounded-xl hover:bg-black/30 transition-all duration-300 shadow-xl">
            Dark Glass
          </button>
        </div>
      </div>

      {/* Glass Panels */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Floating Glass Panels</h3>
        <div className="relative h-64 bg-gradient-to-br from-purple-600 to-blue-600 rounded-2xl p-8">
          <div className="absolute top-4 left-4 right-4 bottom-4 backdrop-blur-2xl bg-white/10 rounded-xl border border-white/20 p-6 shadow-2xl">
            <h4 className="text-white text-xl font-bold mb-2">Floating Panel</h4>
            <p className="text-white/80">This panel appears to float above the gradient background with glass morphism effects.</p>
            <div className="mt-4 grid grid-cols-3 gap-2">
              <div className="backdrop-blur bg-white/10 rounded-lg p-2 text-center">
                <p className="text-white/60 text-xs">Users</p>
                <p className="text-white font-bold">1.2K</p>
              </div>
              <div className="backdrop-blur bg-white/10 rounded-lg p-2 text-center">
                <p className="text-white/60 text-xs">Revenue</p>
                <p className="text-white font-bold">$24K</p>
              </div>
              <div className="backdrop-blur bg-white/10 rounded-lg p-2 text-center">
                <p className="text-white/60 text-xs">Growth</p>
                <p className="text-white font-bold">+18%</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // Add neumorphism section
  const renderNeumorphismSection = () => (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold mb-6">Neumorphism Components</h2>

      {/* Neumorphic Cards */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Soft UI Cards</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-8 bg-gray-100 rounded-2xl">
          {/* Raised Card */}
          <div className="bg-gray-100 rounded-2xl p-6 shadow-[20px_20px_60px_#bebebe,-20px_-20px_60px_#ffffff]">
            <h4 className="text-lg font-semibold mb-2">Raised Card</h4>
            <p className="text-gray-600 text-sm">Soft shadows create an extruded appearance.</p>
            <button className="mt-4 px-4 py-2 bg-gray-100 rounded-lg shadow-[5px_5px_10px_#bebebe,-5px_-5px_10px_#ffffff] hover:shadow-[inset_5px_5px_10px_#bebebe,inset_-5px_-5px_10px_#ffffff] transition-all duration-300">
              Soft Button
            </button>
          </div>

          {/* Inset Card */}
          <div className="bg-gray-100 rounded-2xl p-6 shadow-[inset_20px_20px_60px_#bebebe,inset_-20px_-20px_60px_#ffffff]">
            <h4 className="text-lg font-semibold mb-2">Inset Card</h4>
            <p className="text-gray-600 text-sm">This card appears pressed into the surface.</p>
            <div className="mt-4 w-full h-2 bg-gray-100 rounded-full shadow-[inset_2px_2px_5px_#bebebe,inset_-2px_-2px_5px_#ffffff]">
              <div className="h-full w-3/4 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full"></div>
            </div>
          </div>

          {/* Flat Card */}
          <div className="bg-gray-100 rounded-2xl p-6 shadow-[10px_10px_30px_#bebebe,-10px_-10px_30px_#ffffff]">
            <h4 className="text-lg font-semibold mb-2">Balanced Card</h4>
            <p className="text-gray-600 text-sm">Balanced shadows for a subtle 3D effect.</p>
            <div className="mt-4 flex gap-2">
              <div className="w-8 h-8 bg-gray-100 rounded-full shadow-[3px_3px_6px_#bebebe,-3px_-3px_6px_#ffffff] flex items-center justify-center text-xs">1</div>
              <div className="w-8 h-8 bg-gray-100 rounded-full shadow-[3px_3px_6px_#bebebe,-3px_-3px_6px_#ffffff] flex items-center justify-center text-xs">2</div>
              <div className="w-8 h-8 bg-gray-100 rounded-full shadow-[3px_3px_6px_#bebebe,-3px_-3px_6px_#ffffff] flex items-center justify-center text-xs">3</div>
            </div>
          </div>
        </div>
      </div>

      {/* Neumorphic Controls */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Soft UI Controls</h3>
        <div className="p-8 bg-gray-100 rounded-2xl space-y-6">
          {/* Toggle Switches */}
          <div className="flex gap-8">
            <div className="flex items-center gap-4">
              <span className="text-sm">Toggle:</span>
              <div className="relative w-16 h-8 bg-gray-100 rounded-full shadow-[inset_8px_8px_16px_#bebebe,inset_-8px_-8px_16px_#ffffff]">
                <div className="absolute top-1 left-1 w-6 h-6 bg-gray-100 rounded-full shadow-[3px_3px_6px_#bebebe,-3px_-3px_6px_#ffffff] transition-transform"></div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm">Active:</span>
              <div className="relative w-16 h-8 bg-gradient-to-r from-blue-400 to-blue-500 rounded-full shadow-[inset_2px_2px_4px_rgba(0,0,0,0.2)]">
                <div className="absolute top-1 right-1 w-6 h-6 bg-white rounded-full shadow-lg"></div>
              </div>
            </div>
          </div>

          {/* Input Fields */}
          <div className="flex gap-4">
            <input
              type="text"
              placeholder="Neumorphic input"
              className="px-4 py-3 bg-gray-100 rounded-xl shadow-[inset_8px_8px_16px_#bebebe,inset_-8px_-8px_16px_#ffffff] outline-none focus:shadow-[inset_12px_12px_20px_#bebebe,inset_-12px_-12px_20px_#ffffff] transition-all"
            />
            <button className="px-6 py-3 bg-gray-100 rounded-xl shadow-[8px_8px_16px_#bebebe,-8px_-8px_16px_#ffffff] hover:shadow-[12px_12px_20px_#bebebe,-12px_-12px_20px_#ffffff] active:shadow-[inset_8px_8px_16px_#bebebe,inset_-8px_-8px_16px_#ffffff] transition-all duration-200">
              Submit
            </button>
          </div>

          {/* Radio Buttons */}
          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <div className="w-6 h-6 bg-gray-100 rounded-full shadow-[3px_3px_6px_#bebebe,-3px_-3px_6px_#ffffff] flex items-center justify-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full opacity-0"></div>
              </div>
              <span className="text-sm">Option 1</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <div className="w-6 h-6 bg-gray-100 rounded-full shadow-[inset_2px_2px_4px_#bebebe,inset_-2px_-2px_4px_#ffffff] flex items-center justify-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              </div>
              <span className="text-sm">Option 2</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );

  // Add modern gradients section
  const renderGradientsSection = () => (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold mb-6 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
        Modern Gradient System
      </h2>

      {/* Vibrant Gradients */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Vibrant Gradients</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: 'Sunset', gradient: 'from-orange-500 via-pink-500 to-purple-500' },
            { name: 'Ocean', gradient: 'from-blue-600 via-cyan-500 to-teal-400' },
            { name: 'Forest', gradient: 'from-green-600 via-emerald-500 to-teal-500' },
            { name: 'Berry', gradient: 'from-purple-600 via-pink-600 to-red-500' },
            { name: 'Aurora', gradient: 'from-green-400 via-blue-500 to-purple-600' },
            { name: 'Flame', gradient: 'from-red-600 via-orange-500 to-yellow-400' },
            { name: 'Galaxy', gradient: 'from-indigo-900 via-purple-800 to-pink-700' },
            { name: 'Mint', gradient: 'from-teal-400 via-cyan-400 to-blue-400' },
          ].map((item) => (
            <div key={item.name} className="group cursor-pointer" onClick={() => copyToClipboard(item.gradient, item.name)}>
              <div className={`h-32 rounded-xl bg-gradient-to-br ${item.gradient} group-hover:scale-105 transition-transform shadow-lg`}></div>
              <p className="text-sm font-medium mt-2">{item.name}</p>
              {copiedText === item.name && <p className="text-xs text-green-500">Copied!</p>}
            </div>
          ))}
        </div>
      </div>

      {/* Mesh Gradients */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Mesh Gradients</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-48 rounded-2xl relative overflow-hidden shadow-xl">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400 to-blue-600"></div>
            <div className="absolute inset-0 bg-gradient-to-tr from-purple-400/50 to-transparent"></div>
            <div className="absolute inset-0 bg-gradient-to-bl from-pink-400/30 to-transparent"></div>
            <div className="absolute inset-0 backdrop-blur-[1px]"></div>
            <div className="relative p-6 text-white">
              <h4 className="font-bold">Mesh Gradient 1</h4>
              <p className="text-sm opacity-90">Multiple layers</p>
            </div>
          </div>

          <div className="h-48 rounded-2xl relative overflow-hidden shadow-xl">
            <div className="absolute inset-0 bg-gradient-conic from-yellow-400 via-red-500 to-yellow-400"></div>
            <div className="absolute inset-0 bg-gradient-radial from-transparent to-black/20"></div>
            <div className="relative p-6 text-white">
              <h4 className="font-bold">Conic Gradient</h4>
              <p className="text-sm opacity-90">Radial blend</p>
            </div>
          </div>

          <div className="h-48 rounded-2xl relative overflow-hidden shadow-xl">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-400 via-cyan-500 to-blue-600"></div>
            <div className="absolute inset-0" style={{
              backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(255,255,255,0.3) 0%, transparent 50%)'
            }}></div>
            <div className="relative p-6 text-white">
              <h4 className="font-bold">Radial Accent</h4>
              <p className="text-sm opacity-90">Light burst effect</p>
            </div>
          </div>
        </div>
      </div>

      {/* Animated Gradients */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Animated Gradients</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-32 rounded-xl bg-gradient-to-r from-purple-500 via-pink-500 to-red-500 animate-gradient-x shadow-lg"></div>
          <div className="h-32 rounded-xl bg-gradient-to-r from-blue-500 via-teal-500 to-green-500 animate-gradient-y shadow-lg"></div>
        </div>
      </div>
    </div>
  );

  // Add micro animations section
  const renderMicroAnimationsSection = () => (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold mb-6">Micro Animations</h2>

      {/* Hover Effects */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Hover Animations</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:scale-105 transition-transform duration-200">
            Scale
          </button>
          <button className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:rotate-3 transition-transform duration-200">
            Rotate
          </button>
          <button className="px-6 py-3 bg-gradient-to-r from-pink-500 to-orange-500 text-white rounded-lg hover:shadow-2xl transition-shadow duration-200">
            Shadow
          </button>
          <button className="px-6 py-3 border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-600 hover:text-white transition-all duration-200">
            Fill
          </button>
        </div>
      </div>

      {/* Loading Animations */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Loading States</h3>
        <div className="flex gap-8 items-center">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-3 h-3 bg-blue-600 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 0.1}s` }}
              ></div>
            ))}
          </div>

          <div className="relative w-12 h-12">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full animate-spin"></div>
            <div className="absolute inset-1 bg-white rounded-full"></div>
          </div>

          <div className="flex gap-1">
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="w-1 bg-green-500 animate-pulse"
                style={{
                  height: `${20 + i * 5}px`,
                  animationDelay: `${i * 0.1}s`
                }}
              ></div>
            ))}
          </div>
        </div>
      </div>

      {/* Pulse Effects */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Pulse & Glow Effects</h3>
        <div className="flex gap-6">
          <div className="relative">
            <div className="absolute inset-0 bg-green-500 rounded-full animate-ping"></div>
            <div className="relative w-4 h-4 bg-green-500 rounded-full"></div>
          </div>

          <button className="px-6 py-3 bg-blue-600 text-white rounded-lg animate-pulse-slow">
            Gentle Pulse
          </button>

          <div className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg shadow-lg animate-shimmer">
            Shimmer Effect
          </div>
        </div>
      </div>
    </div>
  );

  // Add bento grid section
  const renderBentoSection = () => (
    <div className="space-y-8">
      <h2 className="text-3xl font-bold mb-6">Bento Grid Layout</h2>

      <div className="grid grid-cols-4 gap-4 auto-rows-[120px]">
        {/* Large feature card */}
        <div className="col-span-2 row-span-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl p-6 text-white shadow-xl">
          <h3 className="text-2xl font-bold mb-2">Featured Metric</h3>
          <p className="text-4xl font-bold">$2.4M</p>
          <p className="text-sm opacity-80 mt-2">Total Volume Today</p>
        </div>

        {/* Medium cards */}
        <div className="col-span-1 row-span-1 bg-white rounded-xl p-4 shadow-lg border border-gray-200">
          <p className="text-xs text-gray-500">Active Users</p>
          <p className="text-2xl font-bold">1,234</p>
        </div>

        <div className="col-span-1 row-span-1 bg-gradient-to-br from-green-400 to-blue-500 rounded-xl p-4 text-white shadow-lg">
          <p className="text-xs opacity-80">Growth Rate</p>
          <p className="text-2xl font-bold">+24%</p>
        </div>

        {/* Wide card */}
        <div className="col-span-2 row-span-1 bg-white rounded-xl p-4 shadow-lg border border-gray-200">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-sm text-gray-500">Performance Score</p>
              <p className="text-xl font-bold">98.5</p>
            </div>
            <div className="h-12 w-32 flex items-end gap-1">
              {[60, 45, 70, 85, 65, 90, 75].map((h, i) => (
                <div key={i} className="flex-1 bg-gradient-to-t from-blue-500 to-cyan-400 rounded-t" style={{ height: `${h}%` }}></div>
              ))}
            </div>
          </div>
        </div>

        {/* Small cards */}
        <div className="col-span-1 row-span-1 bg-gradient-to-br from-orange-400 to-red-500 rounded-xl p-4 text-white shadow-lg">
          <p className="text-3xl mb-1">🔥</p>
          <p className="text-sm font-semibold">Hot Trades</p>
        </div>

        <div className="col-span-1 row-span-1 bg-black text-white rounded-xl p-4 shadow-lg">
          <p className="text-xs opacity-60">APR</p>
          <p className="text-xl font-bold">12.5%</p>
        </div>
      </div>
    </div>
  );

  const sections = [
    { id: 'glassmorphism', label: 'Glassmorphism', icon: '🔮' },
    { id: 'neumorphism', label: 'Neumorphism', icon: '💠' },
    { id: 'gradients', label: 'Modern Gradients', icon: '🌈' },
    { id: 'colors', label: 'Color System', icon: '🎨' },
    { id: 'microanimations', label: 'Micro Animations', icon: '✨' },
    { id: 'bento', label: 'Bento Grid', icon: '🍱' },
    { id: 'buttons', label: 'Modern Buttons', icon: '🔘' },
    { id: 'cards', label: 'Advanced Cards', icon: '🃏' },
    { id: 'forms', label: 'Form Elements', icon: '📋' },
    { id: 'datavis', label: 'Data Visualization', icon: '📊' },
    { id: 'loading', label: 'Loading States', icon: '⏳' },
    { id: 'trading', label: 'Trading Components', icon: '💹' },
  ];

  const renderColorSection = () => (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-6">Color System</h2>

        {/* Primary Colors */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4">Primary Palette</h3>
          <div className="grid grid-cols-4 gap-4">
            {[
              { name: 'Primary Blue', color: 'bg-blue-600', hex: '#2563EB' },
              { name: 'Success Green', color: 'bg-green-500', hex: '#10B981' },
              { name: 'Danger Red', color: 'bg-red-500', hex: '#EF4444' },
              { name: 'Warning Amber', color: 'bg-amber-500', hex: '#F59E0B' },
              { name: 'Purple Accent', color: 'bg-purple-600', hex: '#9333EA' },
              { name: 'Indigo', color: 'bg-indigo-600', hex: '#4F46E5' },
              { name: 'Gray', color: 'bg-gray-600', hex: '#4B5563' },
              { name: 'Dark', color: 'bg-gray-900', hex: '#111827' },
            ].map((item) => (
              <div
                key={item.name}
                className="cursor-pointer group"
                onClick={() => copyToClipboard(item.hex, item.name)}
              >
                <div className={`${item.color} h-24 rounded-lg mb-2 group-hover:scale-105 transition-transform`} />
                <p className="text-sm font-medium">{item.name}</p>
                <p className="text-xs text-gray-500">{item.hex}</p>
                {copiedText === item.name && (
                  <p className="text-xs text-green-500">Copied!</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Funding Rate Colors */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4">Funding Rate Colors</h3>
          <div className="grid grid-cols-3 gap-4">
            {[
              { name: 'Positive', color: 'bg-green-500', hex: '#10B981' },
              { name: 'Negative', color: 'bg-red-500', hex: '#EF4444' },
              { name: 'Neutral', color: 'bg-gray-500', hex: '#6B7280' },
            ].map((item) => (
              <div
                key={item.name}
                className="cursor-pointer"
                onClick={() => copyToClipboard(item.hex, item.name)}
              >
                <div className={`${item.color} h-20 rounded-lg mb-2`} />
                <p className="text-sm font-medium">{item.name}</p>
                <p className="text-xs text-gray-500">{item.hex}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Z-Score Gradient */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4">Z-Score Gradient</h3>
          <div className="h-20 rounded-lg bg-gradient-to-r from-blue-500 via-gray-400 to-orange-500" />
          <div className="flex justify-between mt-2 text-xs text-gray-600">
            <span>-3 (Extreme Negative)</span>
            <span>0 (Neutral)</span>
            <span>+3 (Extreme Positive)</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTypographySection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Typography</h2>

      <div className="space-y-6">
        {[
          { tag: 'h1', class: 'text-5xl font-bold', text: 'Heading 1' },
          { tag: 'h2', class: 'text-4xl font-bold', text: 'Heading 2' },
          { tag: 'h3', class: 'text-3xl font-bold', text: 'Heading 3' },
          { tag: 'h4', class: 'text-2xl font-semibold', text: 'Heading 4' },
          { tag: 'h5', class: 'text-xl font-semibold', text: 'Heading 5' },
          { tag: 'h6', class: 'text-lg font-semibold', text: 'Heading 6' },
          { tag: 'p', class: 'text-base', text: 'Body text - Lorem ipsum dolor sit amet, consectetur adipiscing elit.' },
          { tag: 'small', class: 'text-sm', text: 'Small text - Used for secondary information' },
          { tag: 'tiny', class: 'text-xs', text: 'Tiny text - Used for labels and captions' },
        ].map((item) => (
          <div key={item.tag} className="border-b border-gray-200 pb-4">
            <div className="flex items-baseline justify-between">
              <p className={item.class}>{item.text}</p>
              <code className="text-xs bg-gray-100 px-2 py-1 rounded">{item.class}</code>
            </div>
          </div>
        ))}
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Text Colors</h3>
        <div className="space-y-2">
          <p className="text-gray-900">Primary Text (text-gray-900)</p>
          <p className="text-gray-600">Secondary Text (text-gray-600)</p>
          <p className="text-gray-400">Muted Text (text-gray-400)</p>
          <p className="text-green-600">Success Text (text-green-600)</p>
          <p className="text-red-600">Danger Text (text-red-600)</p>
          <p className="text-blue-600">Link Text (text-blue-600)</p>
        </div>
      </div>
    </div>
  );

  const renderSpacingSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Spacing System</h2>

      <div>
        <h3 className="text-lg font-semibold mb-4">Spacing Scale</h3>
        <div className="space-y-4">
          {[
            { size: '0', value: '0px', class: 'p-0' },
            { size: '1', value: '4px', class: 'p-1' },
            { size: '2', value: '8px', class: 'p-2' },
            { size: '3', value: '12px', class: 'p-3' },
            { size: '4', value: '16px', class: 'p-4' },
            { size: '5', value: '20px', class: 'p-5' },
            { size: '6', value: '24px', class: 'p-6' },
            { size: '8', value: '32px', class: 'p-8' },
            { size: '10', value: '40px', class: 'p-10' },
            { size: '12', value: '48px', class: 'p-12' },
          ].map((item) => (
            <div key={item.size} className="flex items-center gap-4">
              <code className="text-sm w-16">{item.class}</code>
              <span className="text-sm text-gray-600 w-16">{item.value}</span>
              <div className="flex-1">
                <div className={`${item.class} bg-blue-500 inline-block`}>
                  <div className="bg-white h-4 w-4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-4">Container Widths</h3>
        <div className="space-y-4">
          {[
            { size: 'sm', value: '640px' },
            { size: 'md', value: '768px' },
            { size: 'lg', value: '1024px' },
            { size: 'xl', value: '1280px' },
            { size: '2xl', value: '1536px' },
          ].map((item) => (
            <div key={item.size} className="flex items-center gap-4">
              <code className="text-sm w-16">max-w-{item.size}</code>
              <span className="text-sm text-gray-600">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderButtonsSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Buttons</h2>

      {/* Button Variants */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Button Variants</h3>
        <div className="flex flex-wrap gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            Primary
          </button>
          <button className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors">
            Secondary
          </button>
          <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors">
            Success
          </button>
          <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
            Danger
          </button>
          <button className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors">
            Warning
          </button>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Outline
          </button>
          <button className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
            Ghost
          </button>
        </div>
      </div>

      {/* Button Sizes */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Button Sizes</h3>
        <div className="flex items-center gap-4">
          <button className="px-2 py-1 text-xs bg-blue-600 text-white rounded">
            Extra Small
          </button>
          <button className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg">
            Small
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg">
            Medium
          </button>
          <button className="px-6 py-3 text-lg bg-blue-600 text-white rounded-lg">
            Large
          </button>
        </div>
      </div>

      {/* Button States */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Button States</h3>
        <div className="flex gap-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg">
            Normal
          </button>
          <button className="px-4 py-2 bg-blue-700 text-white rounded-lg">
            Hover/Active
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg opacity-50 cursor-not-allowed" disabled>
            Disabled
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg flex items-center gap-2">
            <span className="animate-spin">⟳</span>
            Loading
          </button>
        </div>
      </div>

      {/* Icon Buttons */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Icon Buttons</h3>
        <div className="flex gap-4">
          <button className="p-2 bg-blue-600 text-white rounded-lg">
            ⚙️
          </button>
          <button className="p-2 bg-green-600 text-white rounded-lg">
            ✓
          </button>
          <button className="p-2 bg-red-600 text-white rounded-lg">
            ✕
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg flex items-center gap-2">
            <span>📊</span>
            With Icon
          </button>
        </div>
      </div>
    </div>
  );

  const renderFormsSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Form Elements</h2>

      {/* Text Inputs */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Text Inputs</h3>
        <div className="space-y-4 max-w-md">
          <div>
            <label className="block text-sm font-medium mb-1">Default Input</label>
            <input
              type="text"
              placeholder="Enter text..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Search Input</label>
            <div className="relative">
              <span className="absolute left-3 top-2.5">🔍</span>
              <input
                type="text"
                placeholder="Search..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Number Input</label>
            <input
              type="number"
              placeholder="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Disabled Input</label>
            <input
              type="text"
              placeholder="Disabled"
              disabled
              className="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Input with Error</label>
            <input
              type="text"
              placeholder="Invalid input"
              className="w-full px-3 py-2 border border-red-500 rounded-lg focus:ring-2 focus:ring-red-500"
            />
            <p className="text-xs text-red-500 mt-1">This field is required</p>
          </div>
        </div>
      </div>

      {/* Select Dropdown */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Select Dropdown</h3>
        <div className="max-w-md">
          <label className="block text-sm font-medium mb-1">Exchange</label>
          <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
            <option>Binance</option>
            <option>KuCoin</option>
            <option>Backpack</option>
            <option>Hyperliquid</option>
          </select>
        </div>
      </div>

      {/* Checkboxes and Radios */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Checkboxes & Radio Buttons</h3>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded text-blue-600" defaultChecked />
              <span>Checkbox Option 1</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="rounded text-blue-600" />
              <span>Checkbox Option 2</span>
            </label>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2">
              <input type="radio" name="radio-group" className="text-blue-600" defaultChecked />
              <span>Radio Option 1</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="radio" name="radio-group" className="text-blue-600" />
              <span>Radio Option 2</span>
            </label>
          </div>
        </div>
      </div>

      {/* Toggle Switch */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Toggle Switch</h3>
        <label className="flex items-center gap-3">
          <span>Enable Feature</span>
          <div className="relative">
            <input type="checkbox" className="sr-only peer" />
            <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-checked:bg-blue-600 transition-colors"></div>
            <div className="absolute top-0.5 left-0.5 bg-white w-5 h-5 rounded-full transition-transform peer-checked:translate-x-5"></div>
          </div>
        </label>
      </div>

      {/* Textarea */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Textarea</h3>
        <div className="max-w-md">
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            placeholder="Enter description..."
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  );

  const renderCardsSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Cards</h2>

      {/* Basic Card */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Basic Card</h3>
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 max-w-md">
          <h4 className="text-lg font-semibold mb-2">Card Title</h4>
          <p className="text-gray-600">This is a basic card component with a title and content.</p>
        </div>
      </div>

      {/* Stat Card */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Stat Card</h3>
        <div className="grid grid-cols-3 gap-4 max-w-3xl">
          <StatCard
            title="Total Contracts"
            value="1,240"
            icon="📊"
            color="blue"
          />
          <StatCard
            title="Average APR"
            value="12.5%"
            change={2.3}
            icon="📈"
            color="green"
          />
          <StatCard
            title="Highest APR"
            value="89.2%"
            subtitle="Binance - ENAUSDT"
            icon="🚀"
            color="purple"
          />
        </div>
      </div>

      {/* Card with Header */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Card with Header</h3>
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 max-w-md">
          <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 rounded-t-xl">
            <h4 className="font-semibold">Card Header</h4>
          </div>
          <div className="p-6">
            <p className="text-gray-600">Card content goes here.</p>
          </div>
        </div>
      </div>

      {/* Interactive Card */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Interactive Card</h3>
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 max-w-md hover:shadow-xl transition-shadow cursor-pointer">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-lg font-semibold">Clickable Card</h4>
              <p className="text-gray-600 text-sm">Hover and click me!</p>
            </div>
            <span className="text-2xl">→</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTablesSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Tables</h2>

      <div>
        <h3 className="text-lg font-semibold mb-4">Basic Table</h3>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 font-semibold">Asset</th>
                <th className="text-left py-3 px-4 font-semibold">Exchange</th>
                <th className="text-right py-3 px-4 font-semibold">Funding Rate</th>
                <th className="text-right py-3 px-4 font-semibold">APR</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 px-4">BTC</td>
                <td className="py-3 px-4">Binance</td>
                <td className="py-3 px-4 text-right text-green-600">0.0100%</td>
                <td className="py-3 px-4 text-right">10.95%</td>
              </tr>
              <tr className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 px-4">ETH</td>
                <td className="py-3 px-4">KuCoin</td>
                <td className="py-3 px-4 text-right text-red-600">-0.0050%</td>
                <td className="py-3 px-4 text-right">-5.48%</td>
              </tr>
              <tr className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 px-4">SOL</td>
                <td className="py-3 px-4">Backpack</td>
                <td className="py-3 px-4 text-right text-green-600">0.0200%</td>
                <td className="py-3 px-4 text-right">21.90%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderBadgesSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Badges & Tags</h2>

      {/* Status Badges */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Status Badges</h3>
        <div className="flex flex-wrap gap-2">
          <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>
          <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">Pending</span>
          <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">Inactive</span>
          <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">New</span>
          <span className="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-800">Premium</span>
        </div>
      </div>

      {/* Exchange Tags */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Exchange Tags</h3>
        <div className="flex flex-wrap gap-2">
          <span className="px-3 py-1 text-sm rounded bg-yellow-500 text-white">Binance</span>
          <span className="px-3 py-1 text-sm rounded bg-green-500 text-white">KuCoin</span>
          <span className="px-3 py-1 text-sm rounded bg-blue-500 text-white">Backpack</span>
          <span className="px-3 py-1 text-sm rounded bg-purple-500 text-white">Hyperliquid</span>
        </div>
      </div>

      {/* Z-Score Indicators */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Z-Score Indicators</h3>
        <div className="flex flex-wrap gap-2">
          <span className="px-3 py-1 text-sm rounded bg-blue-500 text-white">Z: -2.5</span>
          <span className="px-3 py-1 text-sm rounded bg-gray-500 text-white">Z: 0.2</span>
          <span className="px-3 py-1 text-sm rounded bg-orange-500 text-white">Z: +3.1</span>
        </div>
      </div>

      {/* Funding Rate Indicators */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Funding Rate Indicators</h3>
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-1">
            <span className="text-green-500">↑</span>
            <span className="text-green-500 font-semibold">0.0100%</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-red-500">↓</span>
            <span className="text-red-500 font-semibold">-0.0050%</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-gray-500">→</span>
            <span className="text-gray-500 font-semibold">0.0000%</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderAlertsSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Alerts</h2>

      <div className="space-y-4 max-w-2xl">
        {/* Success Alert */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-green-500">✓</span>
          <div>
            <h4 className="font-semibold text-green-900">Success!</h4>
            <p className="text-green-700 text-sm">Data has been successfully updated.</p>
          </div>
        </div>

        {/* Warning Alert */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-yellow-500">⚠</span>
          <div>
            <h4 className="font-semibold text-yellow-900">Warning</h4>
            <p className="text-yellow-700 text-sm">Some data points are missing from the last update.</p>
          </div>
        </div>

        {/* Error Alert */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-red-500">✕</span>
          <div>
            <h4 className="font-semibold text-red-900">Error</h4>
            <p className="text-red-700 text-sm">Failed to connect to the exchange API.</p>
          </div>
        </div>

        {/* Info Alert */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-blue-500">ⓘ</span>
          <div>
            <h4 className="font-semibold text-blue-900">Information</h4>
            <p className="text-blue-700 text-sm">New features have been added to the dashboard.</p>
          </div>
        </div>

        {/* Dismissible Alert */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 flex items-start justify-between">
          <div className="flex items-start gap-3">
            <span className="text-purple-500">💡</span>
            <div>
              <h4 className="font-semibold text-purple-900">Tip</h4>
              <p className="text-purple-700 text-sm">Click on any asset to view historical data.</p>
            </div>
          </div>
          <button className="text-purple-500 hover:text-purple-700">✕</button>
        </div>
      </div>
    </div>
  );

  const renderLoadingSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Loading States</h2>

      {/* Spinners */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Spinners</h3>
        <div className="flex items-center gap-8">
          <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          <div className="animate-spin h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          <div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          <div className="animate-spin h-10 w-10 border-2 border-blue-600 border-t-transparent rounded-full"></div>
        </div>
      </div>

      {/* Progress Bars */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Progress Bars</h3>
        <div className="space-y-4 max-w-md">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full" style={{ width: '25%' }}></div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-green-600 h-2 rounded-full" style={{ width: '50%' }}></div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-purple-600 h-2 rounded-full" style={{ width: '75%' }}></div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
          </div>
        </div>
      </div>

      {/* Skeleton Screens */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Skeleton Screens</h3>
        <div className="space-y-4 max-w-md">
          {/* Card Skeleton */}
          <div className="bg-white rounded-lg p-6 shadow-lg">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
              <div className="h-3 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>

          {/* Table Row Skeleton */}
          <div className="bg-white rounded-lg p-4 shadow">
            <div className="animate-pulse flex items-center gap-4">
              <div className="h-10 w-10 bg-gray-200 rounded-full"></div>
              <div className="flex-1">
                <div className="h-3 bg-gray-200 rounded w-1/3 mb-2"></div>
                <div className="h-2 bg-gray-200 rounded w-1/2"></div>
              </div>
              <div className="h-6 bg-gray-200 rounded w-16"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Loading Overlay */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Loading Overlay</h3>
        <div className="relative bg-white rounded-lg p-8 shadow-lg max-w-md">
          <div className="opacity-50">
            <h4 className="text-lg font-semibold mb-2">Content being loaded...</h4>
            <p className="text-gray-600">This content is behind a loading overlay.</p>
          </div>
          <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
            <div className="text-center">
              <div className="animate-spin h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2"></div>
              <p className="text-sm text-gray-600">Loading...</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderChartsSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Charts & Data Visualization</h2>

      {/* Sparklines */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Sparklines</h3>
        <div className="grid grid-cols-3 gap-4 max-w-3xl">
          <div className="bg-white rounded-lg p-4 shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">BTC Funding</span>
              <span className="text-sm font-semibold text-green-600">+0.01%</span>
            </div>
            <div className="h-12 flex items-end gap-1">
              {[40, 45, 42, 48, 52, 45, 58, 55, 60].map((h, i) => (
                <div key={i} className="flex-1 bg-blue-400 rounded-t" style={{ height: `${h}%` }}></div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg p-4 shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">ETH Funding</span>
              <span className="text-sm font-semibold text-red-600">-0.005%</span>
            </div>
            <div className="h-12 flex items-end gap-1">
              {[60, 55, 52, 48, 45, 42, 40, 38, 35].map((h, i) => (
                <div key={i} className="flex-1 bg-red-400 rounded-t" style={{ height: `${h}%` }}></div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-lg p-4 shadow">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">SOL Funding</span>
              <span className="text-sm font-semibold text-green-600">+0.02%</span>
            </div>
            <div className="h-12 flex items-end gap-1">
              {[30, 35, 40, 45, 50, 55, 60, 65, 70].map((h, i) => (
                <div key={i} className="flex-1 bg-green-400 rounded-t" style={{ height: `${h}%` }}></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Progress Circles */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Progress Circles</h3>
        <div className="flex gap-8">
          <div className="relative h-20 w-20">
            <svg className="transform -rotate-90 h-20 w-20">
              <circle cx="40" cy="40" r="36" stroke="#E5E7EB" strokeWidth="8" fill="none" />
              <circle cx="40" cy="40" r="36" stroke="#3B82F6" strokeWidth="8" fill="none"
                strokeDasharray={`${2 * Math.PI * 36 * 0.75} ${2 * Math.PI * 36}`} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-semibold">75%</span>
            </div>
          </div>

          <div className="relative h-20 w-20">
            <svg className="transform -rotate-90 h-20 w-20">
              <circle cx="40" cy="40" r="36" stroke="#E5E7EB" strokeWidth="8" fill="none" />
              <circle cx="40" cy="40" r="36" stroke="#10B981" strokeWidth="8" fill="none"
                strokeDasharray={`${2 * Math.PI * 36 * 0.45} ${2 * Math.PI * 36}`} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-semibold">45%</span>
            </div>
          </div>

          <div className="relative h-20 w-20">
            <svg className="transform -rotate-90 h-20 w-20">
              <circle cx="40" cy="40" r="36" stroke="#E5E7EB" strokeWidth="8" fill="none" />
              <circle cx="40" cy="40" r="36" stroke="#8B5CF6" strokeWidth="8" fill="none"
                strokeDasharray={`${2 * Math.PI * 36 * 0.90} ${2 * Math.PI * 36}`} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-semibold">90%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTradingSection = () => (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold mb-6">Trading Components</h2>

      {/* Live Funding Ticker */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Live Funding Ticker</h3>
        <div className="max-w-2xl">
          <LiveFundingTicker
            asset="BTC"
            selectedContract="BTCUSDT"
          />
        </div>
      </div>

      {/* Funding Countdown */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Funding Countdown</h3>
        <div className="max-w-md">
          <FundingCountdown
            asset="BTC"
            selectedContract="BTCUSDT"
          />
        </div>
      </div>

      {/* APR Display */}
      <div>
        <h3 className="text-lg font-semibold mb-4">APR Display</h3>
        <div className="flex gap-4">
          <div className="bg-white rounded-lg p-4 shadow">
            <p className="text-sm text-gray-600 mb-1">Current APR</p>
            <p className="text-2xl font-bold text-green-600">12.5%</p>
          </div>
          <div className="bg-white rounded-lg p-4 shadow">
            <p className="text-sm text-gray-600 mb-1">30D Average</p>
            <p className="text-2xl font-bold text-blue-600">8.2%</p>
          </div>
          <div className="bg-white rounded-lg p-4 shadow">
            <p className="text-sm text-gray-600 mb-1">Max APR</p>
            <p className="text-2xl font-bold text-purple-600">45.3%</p>
          </div>
        </div>
      </div>

      {/* Exchange Logos */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Exchange Indicators</h3>
        <div className="flex gap-4">
          <div className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg font-semibold">
            Binance
          </div>
          <div className="px-4 py-2 bg-green-100 text-green-800 rounded-lg font-semibold">
            KuCoin
          </div>
          <div className="px-4 py-2 bg-blue-100 text-blue-800 rounded-lg font-semibold">
            Backpack
          </div>
          <div className="px-4 py-2 bg-purple-100 text-purple-800 rounded-lg font-semibold">
            Hyperliquid
          </div>
        </div>
      </div>

      {/* Z-Score Display */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Z-Score Indicators</h3>
        <div className="grid grid-cols-5 gap-4 max-w-3xl">
          <div className="text-center">
            <div className="h-16 w-full rounded-lg bg-blue-500 flex items-center justify-center text-white font-bold">
              -3.2
            </div>
            <p className="text-xs mt-1">Extreme Low</p>
          </div>
          <div className="text-center">
            <div className="h-16 w-full rounded-lg bg-blue-300 flex items-center justify-center text-white font-bold">
              -1.5
            </div>
            <p className="text-xs mt-1">Low</p>
          </div>
          <div className="text-center">
            <div className="h-16 w-full rounded-lg bg-gray-400 flex items-center justify-center text-white font-bold">
              0.2
            </div>
            <p className="text-xs mt-1">Neutral</p>
          </div>
          <div className="text-center">
            <div className="h-16 w-full rounded-lg bg-orange-300 flex items-center justify-center text-white font-bold">
              1.8
            </div>
            <p className="text-xs mt-1">High</p>
          </div>
          <div className="text-center">
            <div className="h-16 w-full rounded-lg bg-orange-500 flex items-center justify-center text-white font-bold">
              3.5
            </div>
            <p className="text-xs mt-1">Extreme High</p>
          </div>
        </div>
      </div>

      {/* Funding Interval Display */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Funding Intervals</h3>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-gray-100 rounded text-sm">1h</span>
          <span className="px-3 py-1 bg-gray-100 rounded text-sm">2h</span>
          <span className="px-3 py-1 bg-gray-100 rounded text-sm">4h</span>
          <span className="px-3 py-1 bg-gray-100 rounded text-sm font-semibold bg-blue-100 text-blue-800">8h</span>
        </div>
      </div>
    </div>
  );

  const renderSection = () => {
    switch (activeSection) {
      case 'glassmorphism': return renderGlassmorphismSection();
      case 'neumorphism': return renderNeumorphismSection();
      case 'gradients': return renderGradientsSection();
      case 'colors': return renderColorSection();
      case 'microanimations': return renderMicroAnimationsSection();
      case 'bento': return renderBentoSection();
      case 'buttons': return renderButtonsSection();
      case 'cards': return renderCardsSection();
      case 'forms': return renderFormsSection();
      case 'datavis': return renderChartsSection();
      case 'loading': return renderLoadingSection();
      case 'trading': return renderTradingSection();
      default: return renderGlassmorphismSection();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <Header />

      <div className="flex">
        {/* Modern Glassmorphic Sidebar */}
        <nav className="w-72 min-h-screen sticky top-0">
          <div className="m-4 backdrop-blur-xl bg-white/80 rounded-2xl border border-white/50 shadow-2xl h-[calc(100vh-100px)]">
            <div className="p-6">
              <div className="mb-8">
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  UI Kit 2025
                </h1>
                <p className="text-xs text-gray-500 mt-1">Modern Design System</p>
              </div>

              {/* Dark Mode Toggle */}
              <div className="mb-6 p-3 bg-gray-100 rounded-xl flex items-center justify-between">
                <span className="text-sm text-gray-700">Dark Mode</span>
                <button
                  onClick={() => setIsDarkMode(!isDarkMode)}
                  className="relative w-12 h-6 bg-gray-300 rounded-full transition-colors"
                >
                  <div className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${isDarkMode ? 'translate-x-6' : ''}`}></div>
                </button>
              </div>

              <ul className="space-y-1">
                {sections.map((section) => (
                  <li key={section.id}>
                    <button
                      onClick={() => setActiveSection(section.id)}
                      className={clsx(
                        'w-full text-left px-4 py-3 rounded-xl transition-all duration-200 flex items-center gap-3 group',
                        activeSection === section.id
                          ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg scale-105'
                          : 'hover:bg-white/50 hover:backdrop-blur text-gray-700 hover:shadow-md'
                      )}
                    >
                      <span className={clsx(
                        'text-xl transition-transform group-hover:scale-110',
                        activeSection === section.id && 'animate-pulse'
                      )}>
                        {section.icon}
                      </span>
                      <span className="font-medium">{section.label}</span>
                      {activeSection === section.id && (
                        <span className="ml-auto">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                          </svg>
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </nav>

        {/* Main Content with Animation */}
        <main className="flex-1 p-8">
          <div className="max-w-7xl mx-auto" key={animationKey}>
            <div className="animate-fade-in">
              {renderSection()}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default UIKitPage;