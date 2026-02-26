"use client"

import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, Loader2, Lightbulb, MessageSquare, History, Trash2, Zap, Sparkles, ShieldCheck, Activity, Globe } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  toolsUsed?: string[]
  latencyMs?: number
}

interface AgentResponse {
  session_id: string
  query: string
  response: string
  reasoning_trace: Array<{ step: number; action: string; result: string }>
  tools_used: string[]
  latency_ms: number
  model: string
  agent_type: string
}

const sampleQueries = [
  "What is the current air quality?",
  "Is it safe for a morning run?",
  "Check WHO compliance for PM2.5",
  "Explain the recent AQI spike",
  "AQI forecast for the next 48h",
]

export default function AgentPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [agentStatus, setAgentStatus] = useState<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchAgentStatus()
    setMessages([{
      id: '0',
      role: 'assistant',
      content: `**System Online.** I am GreenPulse AI, your environmental cognitive assistant. 🌿

I have direct access to real-time sensor telemetry, predictive ML models, and regulatory frameworks. How can I assist your analysis today?`,
      timestamp: new Date(),
    }])
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const fetchAgentStatus = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/agents/status`
      )
      if (response.ok) {
        const data = await response.json()
        setAgentStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch agent status:', err)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const sendMessage = async (query: string) => {
    if (!query.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/agents/query`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            session_id: sessionId,
          }),
        }
      )

      if (!response.ok) throw new Error('Failed to get response')

      const data: AgentResponse = await response.json()
      setSessionId(data.session_id)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        toolsUsed: data.tools_used,
        latencyMs: data.latency_ms,
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I encountered a disruption in the neural pipeline. Please re-initiate your query.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const formatMessage = (content: string) => {
    return content.split('\n').map((line, i) => {
      line = line.replace(/\*\*(.*?)\*\*/g, '<b class="text-white font-black">$1</b>')
      if (line.startsWith('•') || line.startsWith('-')) {
        return `<li class="ml-4 mb-1 list-none flex items-start gap-2"><span class="text-green-500 mt-1.5 w-1.5 h-1.5 rounded-full bg-green-500/40 flex-shrink-0" /> ${line.substring(2)}</li>`
      }
      return `<p class="mb-3 last:mb-0">${line}</p>`
    }).join('')
  }

  return (
    <div className="max-w-[1000px] mx-auto h-[calc(100vh-140px)] flex flex-col gap-6 animate-fade-slide">

      {/* Agent Identity Overlay */}
      <div className="flex items-center justify-between px-6 py-4 glass-card border-white/5 relative overflow-hidden shrink-0">
        <div className="absolute top-0 right-0 p-8 transform translate-x-1/2 -translate-y-1/2 bg-green-500/5 blur-3xl rounded-full w-48 h-48 pointer-events-none" />

        <div className="flex items-center gap-5 relative z-10">
          <div className="relative">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-xl shadow-green-500/20">
              <Bot className="w-7 h-7 text-white" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-[#020617] p-0.5">
              <div className="w-full h-full rounded-full bg-green-500 animate-pulse" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-black text-white tracking-tight">GreenPulse <span className="text-green-500">Cognitive</span></h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Status: Operational</span>
              <div className="w-px h-2.5 bg-white/10" />
              <span className="text-[10px] font-black text-green-500 uppercase tracking-widest leading-none">
                {agentStatus?.llm_model || 'GPT-4O Enterprise'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 relative z-10">
          <div className="hidden sm:flex flex-col items-end mr-4">
            <span className="text-[9px] font-black text-gray-600 uppercase">Context Window</span>
            <span className="text-[10px] font-bold text-gray-400">128k Tokens</span>
          </div>
          <button
            onClick={() => setMessages(messages.slice(0, 1))}
            className="p-3 bg-white/5 hover:bg-white/10 rounded-2xl border border-white/5 text-gray-500 hover:text-white transition-all"
            title="Reset Context"
          >
            <Trash2 className="w-4.5 h-4.5" />
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto px-2 space-y-8 custom-scrollbar scroll-smooth">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-slide`}>
            <div className={`flex gap-4 max-w-[85%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center border ${m.role === 'user'
                  ? 'bg-white/5 border-white/10'
                  : 'bg-green-500/10 border-green-500/20 shadow-lg shadow-green-500/5'
                }`}>
                {m.role === 'user' ? <User className="w-5 h-5 text-gray-400" /> : <Sparkles className="w-5 h-5 text-green-400" />}
              </div>

              <div className="space-y-2">
                <div className={`px-6 py-4 rounded-3xl text-sm leading-relaxed ${m.role === 'user'
                    ? 'bg-white text-black font-semibold rounded-tr-none'
                    : 'glass-card border-white/5 text-gray-200 rounded-tl-none'
                  }`}>
                  <div
                    className="prose-custom"
                    dangerouslySetInnerHTML={{ __html: formatMessage(m.content) }}
                  />

                  {m.toolsUsed && m.toolsUsed.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-3">
                      <Zap className="w-3.5 h-3.5 text-yellow-500" />
                      <div className="flex gap-1.5">
                        {m.toolsUsed.map(t => (
                          <span key={t} className="text-[9px] font-black bg-white/5 px-2 py-0.5 rounded text-gray-500 border border-white/5">
                            {t.toUpperCase()}
                          </span>
                        ))}
                      </div>
                      {m.latencyMs && <span className="ml-auto text-[9px] font-black text-gray-600 uppercase tracking-widest">{m.latencyMs}ms</span>}
                    </div>
                  )}
                </div>
                <p className={`text-[9px] font-black text-gray-600 uppercase tracking-widest px-2 ${m.role === 'user' ? 'text-right' : ''}`}>
                  {m.role === 'user' ? 'Analytical Request' : 'Cognitive Response'} • {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start animate-fade-slide">
            <div className="flex gap-4 max-w-[85%]">
              <div className="shrink-0 w-10 h-10 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-green-400" />
              </div>
              <div className="glass-card px-8 py-4 rounded-3xl rounded-tl-none flex items-center gap-4">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-green-500/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-green-500/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-green-500/40 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs font-black text-gray-500 uppercase tracking-widest">Synthesizing Insight</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="shrink-0 space-y-4 pb-4">
        {/* Sample Queries */}
        {messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 justify-center">
            {sampleQueries.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-2xl text-[10px] font-black text-gray-400 hover:text-white transition-all uppercase tracking-widest active:scale-95"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input Bar */}
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-green-500/20 to-emerald-500/20 rounded-[32px] blur opacity-0 group-focus-within:opacity-100 transition-opacity" />
          <div className="relative glass-card bg-[#020617]/40 border-white/10 p-2 pl-6 flex items-center gap-4">
            <MessageSquare className="w-5 h-5 text-gray-600" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
              placeholder="Consult the platform intelligence layer..."
              className="flex-1 bg-transparent text-white text-sm focus:outline-none placeholder:text-gray-600 font-medium"
              disabled={isLoading}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="w-12 h-12 rounded-2xl bg-white text-black flex items-center justify-center hover:scale-105 active:scale-95 transition-all disabled:opacity-20 disabled:grayscale"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex items-center justify-center gap-6 mt-2 opacity-30">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3 h-3 text-green-500" />
            <span className="text-[8px] font-black text-gray-500 uppercase tracking-widest">Secure Interaction</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-green-500" />
            <span className="text-[8px] font-black text-gray-500 uppercase tracking-widest">Real-time Telemetry Ingestion</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Globe className="w-3 h-3 text-green-500" />
            <span className="text-[8px] font-black text-gray-500 uppercase tracking-widest">Multi-Source Auditing</span>
          </div>
        </div>
      </div>

      <style jsx global>{`
        .prose-custom p { margin-bottom: 0.75rem; }
        .prose-custom p:last-child { margin-bottom: 0; }
        @keyframes fade-slide-up {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
