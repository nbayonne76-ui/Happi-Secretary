'use client'
import { useState, useEffect, useRef } from 'react'
import { Phone, PhoneOff, Send, Mic, Calendar, ArrowRightLeft, MessageSquare, Loader2, RefreshCw } from 'lucide-react'
import { api, Client } from '@/lib/api'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  action?: string
  action_data?: any
}

interface CallState {
  call_id: string
  assistant_name: string
  greeting: string
  mode: string
  client: { id: string; name: string }
}

export default function SimulatorPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClient, setSelectedClient] = useState('')
  const [callerNumber, setCallerNumber] = useState('+33600000000')
  const [callState, setCallState] = useState<CallState | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [callEnded, setCallEnded] = useState(false)
  const [summary, setSummary] = useState<any>(null)
  const [seeding, setSeeding] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { api.getClients().then(setClients).catch(() => {}) }, [])
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function seedDemo() {
    setSeeding(true)
    try {
      const res = await fetch(`${BASE}/api/demo/seed`, { method: 'POST' })
      const data = await res.json()
      const freshClients = await api.getClients()
      setClients(freshClients)
      if (freshClients.length > 0) setSelectedClient(freshClients[0].id)
      alert(`✅ ${data.message}`)
    } finally { setSeeding(false) }
  }

  async function startCall() {
    if (!selectedClient) return
    setLoading(true)
    setCallEnded(false)
    setSummary(null)
    setMessages([])
    try {
      const res = await fetch(`${BASE}/api/simulator/call/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: selectedClient, caller_number: callerNumber }),
      })
      const data = await res.json()
      setCallState(data)
      setMessages([{
        role: 'assistant',
        content: data.greeting,
        timestamp: new Date().toISOString(),
      }])
    } finally { setLoading(false) }
  }

  async function sendMessage() {
    if (!input.trim() || !callState || loading) return
    const text = input.trim()
    setInput('')
    setLoading(true)

    // Add user message immediately
    const userMsg: Message = { role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])

    try {
      const res = await fetch(`${BASE}/api/simulator/call/${callState.call_id}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      const data = await res.json()

      const assistantMsg: Message = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        action: data.action,
        action_data: data.action_data,
      }
      setMessages(prev => [...prev, assistantMsg])

      if (data.should_end) {
        await endCall()
      }
    } finally { setLoading(false) }
  }

  async function endCall() {
    if (!callState) return
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/api/simulator/call/${callState.call_id}/end`, { method: 'POST' })
      const data = await res.json()
      setSummary(data)
      setCallEnded(true)

      setMessages(prev => [...prev, {
        role: 'system',
        content: `📋 Appel terminé — ${data.duration_seconds}s | Intent: ${data.intent} | Sentiment: ${data.sentiment}`,
        timestamp: new Date().toISOString(),
      }])
    } finally {
      setLoading(false)
      setCallState(null)
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const ACTION_BADGE: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    book_appointment: { label: 'RDV réservé',    color: 'bg-green-100 text-green-700',  icon: <Calendar size={12} /> },
    transfer:         { label: 'Transfert',      color: 'bg-blue-100 text-blue-700',    icon: <ArrowRightLeft size={12} /> },
    take_message:     { label: 'Message pris',   color: 'bg-orange-100 text-orange-700', icon: <MessageSquare size={12} /> },
    show_slots:       { label: 'Créneaux dispo', color: 'bg-purple-100 text-purple-700', icon: <Calendar size={12} /> },
    end_call:         { label: 'Fin d\'appel',   color: 'bg-gray-100 text-gray-600',    icon: <PhoneOff size={12} /> },
  }

  return (
    <div className="h-full flex flex-col max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Simulateur d'appel</h1>
          <p className="text-sm text-gray-500 mt-0.5">Testez les workflows sans aucun service externe</p>
        </div>
        <button
          onClick={seedDemo}
          disabled={seeding}
          className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
        >
          {seeding ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Charger démo
        </button>
      </div>

      {/* Config */}
      {!callState && !callEnded && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600 block mb-1">Client</label>
              <select
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white"
                value={selectedClient}
                onChange={e => setSelectedClient(e.target.value)}
              >
                <option value="">-- Choisir un client --</option>
                {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600 block mb-1">Numéro appelant</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
                value={callerNumber}
                onChange={e => setCallerNumber(e.target.value)}
              />
            </div>
          </div>
          <button
            onClick={startCall}
            disabled={!selectedClient || loading}
            className="w-full flex items-center justify-center gap-2 py-3 bg-green-500 text-white rounded-xl font-semibold hover:bg-green-600 disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <Phone size={18} />}
            Lancer l'appel simulé
          </button>
        </div>
      )}

      {/* Phone UI */}
      {(callState || callEnded) && (
        <div className="flex-1 flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden min-h-0">
          {/* Call header */}
          <div className={`px-5 py-3 flex items-center justify-between ${callEnded ? 'bg-gray-100' : 'bg-green-50 border-b border-green-100'}`}>
            <div className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full ${callEnded ? 'bg-gray-400' : 'bg-green-500 animate-pulse'}`} />
              <span className="font-semibold text-gray-800">
                {callEnded ? 'Appel terminé' : `En ligne — ${callState?.client.name}`}
              </span>
              <span className="text-sm text-gray-500">{callerNumber}</span>
            </div>
            {callState && !callEnded && (
              <button
                onClick={endCall}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500 text-white rounded-full text-sm font-medium hover:bg-red-600"
              >
                <PhoneOff size={14} /> Raccrocher
              </button>
            )}
            {callEnded && (
              <button
                onClick={() => { setCallEnded(false); setSummary(null); setMessages([]) }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-500 text-white rounded-full text-sm font-medium hover:bg-brand-600"
              >
                <Phone size={14} /> Nouvel appel
              </button>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : msg.role === 'system' ? 'justify-center' : 'justify-start'}`}>
                {msg.role === 'system' ? (
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">{msg.content}</span>
                ) : (
                  <div className={`max-w-xs lg:max-w-md ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                    <div className={`px-4 py-2.5 rounded-2xl text-sm ${
                      msg.role === 'user'
                        ? 'bg-brand-500 text-white rounded-br-sm'
                        : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                    }`}>
                      {msg.content}
                    </div>
                    {msg.action && ACTION_BADGE[msg.action] && (
                      <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${ACTION_BADGE[msg.action].color}`}>
                        {ACTION_BADGE[msg.action].icon}
                        {ACTION_BADGE[msg.action].label}
                        {msg.action === 'show_slots' && msg.action_data?.slots && (
                          <span className="ml-1 opacity-70">{msg.action_data.slots.join(', ')}</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3">
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          {callState && !callEnded && (
            <div className="p-4 border-t border-gray-100">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Mic size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
                    placeholder="Tapez ce que dit l'appelant..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    disabled={loading}
                    autoFocus
                  />
                </div>
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || loading}
                  className="px-4 py-2.5 bg-brand-500 text-white rounded-xl hover:bg-brand-600 disabled:opacity-50"
                >
                  <Send size={16} />
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-2 text-center">
                Simulez la voix de l'appelant en tapant du texte • Entrée pour envoyer
              </p>
            </div>
          )}
        </div>
      )}

      {/* Summary card */}
      {summary && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Rapport d'appel généré</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500 mb-1">Durée</p><p className="font-semibold">{summary.duration_seconds}s</p></div>
            <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500 mb-1">Intention</p><p className="font-semibold capitalize">{summary.intent}</p></div>
            <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500 mb-1">Sentiment</p><p className="font-semibold capitalize">{summary.sentiment}</p></div>
            <div className="bg-gray-50 rounded-lg p-3"><p className="text-xs text-gray-500 mb-1">Résultat</p><p className="font-semibold capitalize">{summary.outcome}</p></div>
          </div>
          <div className="bg-brand-50 border border-brand-100 rounded-lg p-3 text-sm text-gray-700">
            <span className="font-semibold text-brand-700">Résumé IA : </span>{summary.summary}
          </div>
          {summary.appointment_booked && (
            <div className="bg-green-50 border border-green-100 rounded-lg p-3 text-sm text-green-700 font-medium">
              ✅ Rendez-vous réservé avec succès
            </div>
          )}
        </div>
      )}
    </div>
  )
}
