import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, User, Bot, Volume2, Loader2, Sparkles, Zap } from 'lucide-react';
import Antigravity from './components/Antigravity';
import { NoiseBackground } from './components/ui/noise-background';
import { cn } from './lib/utils';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  audioUrl?: string;
  timestamp: Date;
}

const Card = ({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) => {
  return (
    <div
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 text-center shadow-2xl",
        className,
      )}
    >
      {children}
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      text: input,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        message: input,
      });

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.response,
        sender: 'ai',
        audioUrl: response.data.audio_url,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMsg]);

      // Play audio automatically
      if (aiMsg.audioUrl) {
        if (audioRef.current) {
          audioRef.current.src = aiMsg.audioUrl;
          audioRef.current.play();
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: 'error',
          text: '⚠️ Connection error. Please ensure the backend is running on port 8000.',
          sender: 'ai',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-gradient-to-br from-black via-purple-950/20 to-black text-white selection:bg-purple-500/30">
      {/* Animated Background Layer */}
      <div className="absolute inset-0 z-0">
        <Antigravity
          count={500}
          magnetRadius={6}
          ringRadius={9}
          waveSpeed={0.6}
          waveAmplitude={2}
          particleSize={1.3}
          color="#A855F7"
          autoAnimate
          particleVariance={2.5}
          rotationSpeed={0.015}
          pulseSpeed={2.5}
          particleShape="capsule"
          fieldStrength={12}
        />
      </div>

      {/* Gradient Overlays for Depth */}
      <div className="absolute inset-0 z-[1] bg-gradient-to-t from-black/60 via-transparent to-black/40 pointer-events-none" />
      <div className="absolute inset-0 z-[1] bg-[radial-gradient(ellipse_at_center,_transparent_0%,_rgba(0,0,0,0.4)_100%)] pointer-events-none" />

      {/* Main Chat Interface */}
      <div className="relative z-10 flex h-full flex-col items-center justify-center p-4 md:p-6 lg:p-8">
        <div className="w-full max-w-5xl flex flex-col h-[92vh] gap-4">

          {/* Premium Header */}
          <div className="flex items-center justify-between px-6 py-4 rounded-2xl bg-black/40 backdrop-blur-xl border border-white/10 shadow-2xl">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-purple-500 blur-xl opacity-50 animate-pulse" />
                <div className="relative w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold tracking-tight bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 bg-clip-text text-transparent animate-gradient">
                  ANTIGRAVITY AI
                </h1>
                <p className="text-xs text-neutral-400 font-medium">Powered by Neural Intelligence</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10">
                <Zap className="w-4 h-4 text-yellow-400" />
                <span className="text-xs font-semibold text-neutral-300">ULTRA FAST</span>
              </div>
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50" />
                <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Online</span>
              </div>
            </div>
          </div>

          {/* Messages Area with Premium Styling */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto space-y-6 px-2 scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent hover:scrollbar-thumb-purple-500/40 transition-all"
          >
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center space-y-8 animate-in fade-in duration-1000">
                <div className="relative">
                  <div className="absolute inset-0 bg-purple-500 blur-3xl opacity-30 animate-pulse" />
                  <Bot size={80} className="text-purple-400 relative animate-float" />
                </div>
                <div className="text-center space-y-3 max-w-md">
                  <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-300 to-pink-300 bg-clip-text text-transparent">
                    Welcome to Antigravity
                  </h2>
                  <p className="text-lg text-neutral-400 font-light leading-relaxed">
                    Experience the future of AI conversation with voice synthesis
                  </p>
                </div>
                <div className="flex flex-wrap gap-3 justify-center max-w-2xl">
                  {['Tell me a story', 'Explain quantum physics', 'Write a poem'].map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(suggestion)}
                      className="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/50 text-sm text-neutral-300 hover:text-white transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, index) => (
              <div
                key={msg.id}
                className={cn(
                  "flex w-full group animate-in fade-in slide-in-from-bottom-4 duration-500",
                  msg.sender === 'user' ? "justify-end" : "justify-start"
                )}
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className={cn(
                  "flex gap-4 max-w-[85%] md:max-w-[75%]",
                  msg.sender === 'user' ? "flex-row-reverse" : "flex-row"
                )}>
                  {/* Avatar */}
                  <div className={cn(
                    "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-xl relative",
                    msg.sender === 'user'
                      ? "bg-gradient-to-br from-purple-600 to-pink-600"
                      : "bg-gradient-to-br from-neutral-800 to-neutral-900 border border-white/10"
                  )}>
                    {msg.sender === 'user' ? (
                      <User size={18} className="text-white" />
                    ) : (
                      <>
                        <div className="absolute inset-0 bg-purple-500 blur-md opacity-20 animate-pulse" />
                        <Bot size={18} className="text-purple-400 relative" />
                      </>
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div className="flex flex-col gap-2">
                    <div className={cn(
                      "relative px-5 py-3.5 rounded-2xl text-sm leading-relaxed transition-all duration-300 group-hover:scale-[1.02]",
                      msg.sender === 'user'
                        ? "bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-tr-sm shadow-xl shadow-purple-500/20"
                        : "bg-gradient-to-br from-neutral-900/90 to-neutral-800/90 backdrop-blur-xl border border-white/10 text-neutral-100 rounded-tl-sm shadow-2xl hover:border-purple-500/30"
                    )}>
                      <p className="whitespace-pre-wrap">{msg.text}</p>

                      {/* Voice Button for AI messages */}
                      {msg.sender === 'ai' && msg.audioUrl && (
                        <button
                          onClick={() => {
                            if (audioRef.current) {
                              audioRef.current.src = msg.audioUrl!;
                              audioRef.current.play();
                            }
                          }}
                          className="absolute -right-12 top-3 opacity-0 group-hover:opacity-100 transition-all duration-300 p-2.5 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 hover:border-purple-500/50 backdrop-blur-sm hover:scale-110"
                          title="Play voice"
                        >
                          <Volume2 size={16} className="text-purple-400" />
                        </button>
                      )}
                    </div>
                    <span className={cn(
                      "text-[10px] text-neutral-500 font-medium px-2",
                      msg.sender === 'user' ? "text-right" : "text-left"
                    )}>
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex gap-4 max-w-[75%]">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neutral-800 to-neutral-900 border border-white/10 flex items-center justify-center relative shadow-xl">
                    <div className="absolute inset-0 bg-purple-500 blur-md opacity-20 animate-pulse" />
                    <Loader2 size={18} className="animate-spin text-purple-400 relative" />
                  </div>
                  <div className="px-5 py-3.5 rounded-2xl rounded-tl-sm bg-gradient-to-br from-neutral-900/50 to-neutral-800/50 backdrop-blur-xl border border-white/10 text-neutral-400 text-sm shadow-2xl">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="italic">Antigravity is thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Premium Input Area */}
          <div className="px-2 pb-2">
            <NoiseBackground
              className="rounded-2xl"
              gradientColors={[
                "rgb(168, 85, 247)", // Purple
                "rgb(236, 72, 153)", // Pink
                "rgb(147, 51, 234)", // Deep Purple
              ]}
              noiseIntensity={0.15}
              speed={0.2}
            >
              <Card className="min-h-[auto] p-1.5 bg-black/60 backdrop-blur-2xl border-white/20 shadow-2xl">
                <div className="flex items-end gap-3 p-2">
                  <div className="flex-1 relative">
                    <textarea
                      ref={inputRef as any}
                      value={input}
                      onChange={(e) => {
                        setInput(e.target.value);
                        e.target.style.height = 'auto';
                        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      placeholder="Message Antigravity AI..."
                      rows={1}
                      className="w-full bg-transparent border-none outline-none px-4 py-3 text-sm placeholder:text-neutral-500 resize-none max-h-[120px] scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent"
                      style={{ minHeight: '44px' }}
                    />
                  </div>
                  <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    className={cn(
                      "p-3.5 rounded-xl transition-all duration-300 flex items-center justify-center relative group shrink-0",
                      input.trim()
                        ? "bg-gradient-to-br from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white shadow-xl shadow-purple-500/30 hover:shadow-2xl hover:shadow-purple-500/40 hover:scale-105 active:scale-95"
                        : "bg-white/5 text-neutral-600 cursor-not-allowed"
                    )}
                  >
                    {input.trim() && !isLoading && (
                      <div className="absolute inset-0 bg-white/20 rounded-xl blur-md group-hover:blur-lg transition-all" />
                    )}
                    {isLoading ? (
                      <Loader2 size={20} className="animate-spin relative" />
                    ) : (
                      <Send size={20} className="relative" />
                    )}
                  </button>
                </div>
                <div className="px-4 pb-2 pt-1">
                  <p className="text-[10px] text-neutral-500 text-center font-medium">
                    Press <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 font-mono">Enter</kbd> to send • <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 font-mono">Shift + Enter</kbd> for new line
                  </p>
                </div>
              </Card>
            </NoiseBackground>
          </div>
        </div>
      </div>

      <audio ref={audioRef} className="hidden" />

      {/* Subtle Vignette Effect */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,_transparent_0%,_rgba(0,0,0,0.3)_100%)] z-[2]" />
    </div>
  );
}

export default App;
