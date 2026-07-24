import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Check,
  ChevronDown,
  Eye,
  EyeOff,
  Feather,
  Menu,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Send,
  Settings2,
  Square,
  Volume2,
  VolumeX,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react'

type Sender = 'user' | 'assistant'
type ConnectionState = 'checking' | 'online' | 'offline'

interface Message {
  id: string
  text: string
  sender: Sender
  audioUrl?: string
  createdAt: Date
}

interface HealthResponse {
  status: string
  provider: string
  model: string
  voice_enabled: boolean
}

interface ChatResponse {
  response: string
  audio_url?: string
  provider: string
  model: string
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

const starterPrompts = [
  ['Plan my task', 'Break my goal into a small, practical plan.'],
  ['Explain code', 'Explain this code simply and point out possible bugs.'],
  ['Draft locally', 'Help me draft a clear document without sending data online.'],
]

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [connection, setConnection] = useState<ConnectionState>('checking')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [privacyMode, setPrivacyMode] = useState(false)
  const [quietMode, setQuietMode] = useState(
    () => localStorage.getItem('agentic-quiet-mode') !== 'false',
  )
  const [sidebarOpen, setSidebarOpen] = useState(
    () => window.innerWidth >= 900,
  )
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  const statusText = useMemo(() => {
    if (connection === 'checking') return 'Checking local runtime'
    if (connection === 'offline') return 'Runtime offline'
    return `${health?.provider ?? 'local'} · ${health?.model ?? 'ready'}`
  }, [connection, health])

  const checkHealth = useCallback(async () => {
    setConnection('checking')
    try {
      const response = await fetch(`${API_URL}/health`, {
        signal: AbortSignal.timeout(3500),
      })
      if (!response.ok) throw new Error('Runtime unavailable')
      const data = (await response.json()) as HealthResponse
      setHealth(data)
      setConnection(data.status === 'ready' ? 'online' : 'offline')
    } catch {
      setConnection('offline')
    }
  }, [])

  useEffect(() => {
    void checkHealth()
  }, [checkHealth])

  useEffect(() => {
    localStorage.setItem('agentic-quiet-mode', String(quietMode))
  }, [quietMode])

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, isLoading])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'p') {
        event.preventDefault()
        setPrivacyMode((current) => !current)
      }
      if (event.ctrlKey && event.key.toLowerCase() === 'n') {
        event.preventDefault()
        abortRef.current?.abort()
        setMessages([])
        setInput('')
        setError(null)
        inputRef.current?.focus()
      }
      if (event.key === 'Escape') setSettingsOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const sendMessage = async (preset?: string) => {
    const text = (preset ?? input).trim()
    if (!text || isLoading) return

    const userMessage: Message = {
      id: makeId(),
      text,
      sender: 'user',
      createdAt: new Date(),
    }
    setMessages((current) => [...current, userMessage])
    setInput('')
    setError(null)
    setIsLoading(true)
    abortRef.current = new AbortController()

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: messages.slice(-8).map((message) => ({
            role: message.sender === 'assistant' ? 'assistant' : 'user',
            content: message.text,
          })),
          voice: !quietMode,
        }),
        signal: abortRef.current.signal,
      })
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(detail?.detail ?? 'The local runtime returned an error.')
      }

      const data = (await response.json()) as ChatResponse
      const assistantMessage: Message = {
        id: makeId(),
        text: data.response,
        sender: 'assistant',
        audioUrl: data.audio_url
          ? new URL(data.audio_url, API_URL).toString()
          : undefined,
        createdAt: new Date(),
      }
      setMessages((current) => [...current, assistantMessage])
      setConnection('online')

      if (!quietMode && data.audio_url && audioRef.current) {
        audioRef.current.src = data.audio_url
        await audioRef.current.play().catch(() => undefined)
      }
    } catch (requestError) {
      if ((requestError as Error).name !== 'AbortError') {
        setError((requestError as Error).message)
        setConnection('offline')
      }
    } finally {
      setIsLoading(false)
      abortRef.current = null
      inputRef.current?.focus()
    }
  }

  const stopGeneration = () => {
    abortRef.current?.abort()
    setIsLoading(false)
  }

  const startNewChat = () => {
    abortRef.current?.abort()
    setMessages([])
    setInput('')
    setError(null)
    inputRef.current?.focus()
  }

  return (
    <main className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark" aria-hidden="true">
            <Feather size={18} />
          </div>
          <div>
            <strong>Agentic</strong>
            <span>Local companion</span>
          </div>
          <button
            className="icon-button sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        <button className="new-chat-button" onClick={startNewChat}>
          <MessageSquarePlus size={17} />
          New chat
          <kbd>Ctrl N</kbd>
        </button>

        <nav className="sidebar-nav" aria-label="Chat history">
          <p>Today</p>
          {messages.length > 0 ? (
            <button className="history-item active">
              <span>{messages[0]?.text.slice(0, 34)}</span>
              <small>{messages.length} messages</small>
            </button>
          ) : (
            <div className="history-empty">Your local chats appear here.</div>
          )}
        </nav>

        <div className="sidebar-footer">
          <button onClick={() => setSettingsOpen(true)}>
            <Settings2 size={17} />
            Settings
          </button>
          <div className="device-note">
            <Feather size={15} />
            <span>
              <strong>Lite mode</strong>
              No WebGL. Minimal GPU use.
            </span>
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button"
              onClick={() => setSidebarOpen((current) => !current)}
              aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose size={19} /> : <PanelLeftOpen size={19} />}
            </button>
            <div className="conversation-title">
              <strong>New conversation</strong>
              <span className={`runtime-state ${connection}`}>
                {connection === 'online' ? <Wifi size={12} /> : <WifiOff size={12} />}
                {statusText}
              </span>
            </div>
          </div>

          <div className="topbar-actions">
            <button
              className={`text-button ${privacyMode ? 'active' : ''}`}
              onClick={() => setPrivacyMode((current) => !current)}
              title="Toggle Privacy Mode (Ctrl + Shift + P)"
            >
              {privacyMode ? <EyeOff size={16} /> : <Eye size={16} />}
              <span>{privacyMode ? 'Content hidden' : 'Privacy'}</span>
            </button>
            <button
              className="icon-button mobile-settings"
              onClick={() => setSettingsOpen(true)}
              aria-label="Open settings"
            >
              <Settings2 size={18} />
            </button>
          </div>
        </header>

        <div
          className={`conversation ${privacyMode ? 'privacy-active' : ''}`}
          ref={scrollRef}
          aria-live="polite"
        >
          {privacyMode ? (
            <div className="privacy-screen">
              <div className="privacy-icon"><EyeOff size={22} /></div>
              <h1>Conversation hidden</h1>
              <p>Your content is masked while Privacy Mode is active.</p>
              <button onClick={() => setPrivacyMode(false)}>
                <Eye size={16} />
                Show conversation
              </button>
              <kbd>Ctrl + Shift + P</kbd>
            </div>
          ) : messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-mark"><Feather size={24} /></div>
              <h1>What are we building?</h1>
              <p>
                A private assistant that stays useful on everyday hardware.
                Start with a task, question, or idea.
              </p>
              <div className="starter-list">
                {starterPrompts.map(([title, prompt]) => (
                  <button key={title} onClick={() => void sendMessage(prompt)}>
                    <span>
                      <strong>{title}</strong>
                      <small>{prompt}</small>
                    </span>
                    <Send size={15} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message) => (
                <article className={`message ${message.sender}`} key={message.id}>
                  <div className="message-avatar">
                    {message.sender === 'assistant' ? <Feather size={16} /> : 'You'}
                  </div>
                  <div className="message-body">
                    <div className="message-meta">
                      <strong>{message.sender === 'assistant' ? 'Agentic' : 'You'}</strong>
                      <time>
                        {message.createdAt.toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </time>
                    </div>
                    <p>{message.text}</p>
                    {message.audioUrl && (
                      <button
                        className="play-button"
                        onClick={() => {
                          if (!audioRef.current) return
                          audioRef.current.src = message.audioUrl ?? ''
                          void audioRef.current.play()
                        }}
                      >
                        <Volume2 size={14} />
                        Play response
                      </button>
                    )}
                  </div>
                </article>
              ))}
              {isLoading && (
                <article className="message assistant loading-message">
                  <div className="message-avatar"><Feather size={16} /></div>
                  <div className="message-body">
                    <div className="message-meta"><strong>Agentic</strong></div>
                    <div className="thinking-lines" aria-label="Agentic is thinking">
                      <span />
                      <span />
                      <span />
                    </div>
                  </div>
                </article>
              )}
            </div>
          )}
        </div>

        <div className="composer-wrap">
          {error && (
            <div className="error-banner" role="alert">
              <WifiOff size={16} />
              <span>{error}</span>
              <button onClick={() => setError(null)} aria-label="Dismiss error">
                <X size={15} />
              </button>
            </div>
          )}
          <div className="composer">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void sendMessage()
                }
              }}
              placeholder={connection === 'offline' ? 'Start the local runtime to chat...' : 'Message Agentic...'}
              rows={1}
              disabled={privacyMode}
              aria-label="Message Agentic"
            />
            <div className="composer-tools">
              <button
                className={`quiet-toggle ${quietMode ? 'active' : ''}`}
                onClick={() => setQuietMode((current) => !current)}
                title={quietMode ? 'Voice output is off' : 'Voice output is on'}
              >
                {quietMode ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>
              {isLoading ? (
                <button className="send-button stop" onClick={stopGeneration} aria-label="Stop">
                  <Square size={15} fill="currentColor" />
                </button>
              ) : (
                <button
                  className="send-button"
                  onClick={() => void sendMessage()}
                  disabled={!input.trim() || privacyMode}
                  aria-label="Send message"
                >
                  <Send size={17} />
                </button>
              )}
            </div>
          </div>
          <p className="composer-note">
            Local models can make mistakes. Review actions before they run.
          </p>
        </div>
      </section>

      {settingsOpen && (
        <div className="modal-backdrop" onMouseDown={() => setSettingsOpen(false)}>
          <section
            className="settings-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="settings-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header>
              <div>
                <h2 id="settings-title">Runtime settings</h2>
                <p>Simple defaults for private, low-resource use.</p>
              </div>
              <button
                className="icon-button"
                onClick={() => setSettingsOpen(false)}
                aria-label="Close settings"
              >
                <X size={18} />
              </button>
            </header>
            <div className="settings-group">
              <label>Provider</label>
              <button className="select-row" onClick={checkHealth}>
                <span>
                  <strong>{health?.provider ?? 'Auto detect'}</strong>
                  <small>{health?.model ?? 'Connect to inspect the runtime'}</small>
                </span>
                <ChevronDown size={16} />
              </button>
            </div>
            <div className="settings-group">
              <label>Performance</label>
              <div className="option-row selected">
                <span>
                  <strong>Lite interface</strong>
                  <small>Static surfaces, low memory, no continuous GPU work.</small>
                </span>
                <Check size={17} />
              </div>
            </div>
            <button className="connection-button" onClick={checkHealth}>
              {connection === 'online' ? <Wifi size={16} /> : <WifiOff size={16} />}
              Check connection
            </button>
          </section>
        </div>
      )}

      {!sidebarOpen && (
        <button className="mobile-menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
          <Menu size={19} />
        </button>
      )}
      <audio ref={audioRef} hidden />
    </main>
  )
}

export default App
