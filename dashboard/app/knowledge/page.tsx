'use client'
import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { api, KnowledgeEntry, Client } from '@/lib/api'
import { Plus, Trash2, Globe, FileText, MessageSquare, Upload } from 'lucide-react'

function KnowledgePage() {
  const searchParams = useSearchParams()
  const defaultClient = searchParams.get('client') || ''

  const [clients, setClients] = useState<Client[]>([])
  const [selectedClient, setSelectedClient] = useState(defaultClient)
  const [entries, setEntries] = useState<KnowledgeEntry[]>([])
  const [tab, setTab] = useState<'faq' | 'manual' | 'url'>('faq')
  const [loading, setLoading] = useState(false)

  // FAQ form
  const [faqQ, setFaqQ] = useState('')
  const [faqA, setFaqA] = useState('')
  // Manual form
  const [manTitle, setManTitle] = useState('')
  const [manContent, setManContent] = useState('')
  // URL form
  const [url, setUrl] = useState('')

  useEffect(() => { api.getClients().then(setClients).catch(() => {}) }, [])
  useEffect(() => {
    if (selectedClient) api.getKnowledge(selectedClient).then(setEntries).catch(() => {})
  }, [selectedClient])

  async function addFaq() {
    if (!selectedClient || !faqQ || !faqA) return
    setLoading(true)
    try {
      await api.addFaq(selectedClient, faqQ, faqA)
      setFaqQ(''); setFaqA('')
      setEntries(await api.getKnowledge(selectedClient))
    } finally { setLoading(false) }
  }

  async function addManual() {
    if (!selectedClient || !manTitle || !manContent) return
    setLoading(true)
    try {
      await api.addManual(selectedClient, manTitle, manContent)
      setManTitle(''); setManContent('')
      setEntries(await api.getKnowledge(selectedClient))
    } finally { setLoading(false) }
  }

  async function addUrl() {
    if (!selectedClient || !url) return
    setLoading(true)
    try {
      await api.ingestUrl(selectedClient, url)
      setUrl('')
      setEntries(await api.getKnowledge(selectedClient))
    } finally { setLoading(false) }
  }

  async function remove(id: string) {
    await api.deleteKnowledge(id)
    setEntries(e => e.filter(x => x.id !== id))
  }

  const SOURCE_ICON: Record<string, React.ReactNode> = {
    faq: <MessageSquare size={14} />, manual: <FileText size={14} />,
    url: <Globe size={14} />, pdf: <Upload size={14} />,
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900">Base de connaissances</h1>

      <div>
        <label className="text-sm font-medium text-gray-600 block mb-1">Client</label>
        <select className={SELECT_CLS} value={selectedClient} onChange={e => setSelectedClient(e.target.value)}>
          <option value="">-- Sélectionner un client --</option>
          {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      {selectedClient && (
        <>
          {/* Add form */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <div className="flex gap-2">
              {(['faq', 'manual', 'url'] as const).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${tab === t ? 'bg-brand-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  {t === 'faq' ? 'FAQ' : t === 'manual' ? 'Texte libre' : 'Importer une URL'}
                </button>
              ))}
            </div>

            {tab === 'faq' && (
              <div className="space-y-3">
                <input className={INPUT_CLS} placeholder="Question fréquente..." value={faqQ} onChange={e => setFaqQ(e.target.value)} />
                <textarea className={`${INPUT_CLS} resize-none`} rows={2} placeholder="Réponse..." value={faqA} onChange={e => setFaqA(e.target.value)} />
                <button onClick={addFaq} disabled={loading || !faqQ || !faqA} className={BTN_CLS}><Plus size={16} /> Ajouter</button>
              </div>
            )}
            {tab === 'manual' && (
              <div className="space-y-3">
                <input className={INPUT_CLS} placeholder="Titre..." value={manTitle} onChange={e => setManTitle(e.target.value)} />
                <textarea className={`${INPUT_CLS} resize-none`} rows={4} placeholder="Contenu..." value={manContent} onChange={e => setManContent(e.target.value)} />
                <button onClick={addManual} disabled={loading || !manTitle || !manContent} className={BTN_CLS}><Plus size={16} /> Ajouter</button>
              </div>
            )}
            {tab === 'url' && (
              <div className="space-y-3">
                <input className={INPUT_CLS} placeholder="https://..." value={url} onChange={e => setUrl(e.target.value)} />
                <p className="text-xs text-gray-400">L'IA extraira automatiquement le contenu textuel de la page.</p>
                <button onClick={addUrl} disabled={loading || !url} className={BTN_CLS}><Globe size={16} /> Importer</button>
              </div>
            )}
          </div>

          {/* Entry list */}
          <div className="space-y-2">
            {entries.length === 0 && <p className="text-gray-400 text-sm text-center py-6">Aucune entrée dans la base de connaissances.</p>}
            {entries.map(e => (
              <div key={e.id} className="bg-white rounded-lg border border-gray-200 p-4 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-gray-400">{SOURCE_ICON[e.source_type]}</span>
                    <span className="text-sm font-medium text-gray-800 truncate">{e.title}</span>
                    <span className="text-xs text-gray-400 bg-gray-100 px-2 rounded-full">{e.source_type}</span>
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-2">{e.content}</p>
                </div>
                <button onClick={() => remove(e.id)} className="text-gray-400 hover:text-red-500 shrink-0 mt-0.5">
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

const INPUT_CLS = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300'
const SELECT_CLS = 'border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-300 w-full max-w-xs'
const BTN_CLS = 'flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-50'

export default function KnowledgePageWrapper() {
  return <Suspense><KnowledgePage /></Suspense>
}
