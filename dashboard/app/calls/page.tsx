import React from 'react'
import { api, CallLog } from '@/lib/api'
import { Phone, Calendar, ArrowRightLeft, MessageSquare, AlertCircle } from 'lucide-react'
import Link from 'next/link'

const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'bg-green-100 text-green-700',
  neutral:  'bg-gray-100 text-gray-600',
  negative: 'bg-orange-100 text-orange-700',
  urgent:   'bg-red-100 text-red-700',
}
const OUTCOME_ICON: Record<string, React.ReactNode> = {
  appointment_booked: <Calendar size={14} />,
  transferred:        <ArrowRightLeft size={14} />,
  message_taken:      <MessageSquare size={14} />,
  resolved:           <Phone size={14} />,
}
const INTENT_FR: Record<string, string> = {
  appointment: 'RDV', support: 'Support', order: 'Commande',
  info: 'Info', complaint: 'Réclamation', other: 'Autre',
}

export default async function CallsPage() {
  let calls: CallLog[] = []
  try { calls = await api.getCalls({ limit: '100' }) } catch {}

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Historique des appels</h1>
        <span className="text-sm text-gray-500">{calls.length} appels</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Numéro', 'Date', 'Durée', 'Intention', 'Sentiment', 'Résultat', 'Résumé', ''].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {calls.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-10 text-center text-gray-400">Aucun appel enregistré</td></tr>
            )}
            {calls.map(c => (
              <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-mono font-medium">
                  {c.caller_number || 'Inconnu'}
                  {c.is_vip && <span className="ml-1 text-yellow-500">⭐</span>}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {c.started_at ? new Date(c.started_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                </td>
                <td className="px-4 py-3 text-gray-500">{formatDuration(c.duration_seconds)}</td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 rounded-full bg-brand-50 text-brand-600 text-xs font-medium">
                    {INTENT_FR[c.intent || ''] || c.intent || '—'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {c.sentiment && (
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${SENTIMENT_COLOR[c.sentiment] || 'bg-gray-100'}`}>
                      {c.sentiment}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-1 text-gray-600">
                    {OUTCOME_ICON[c.outcome || ''] || <AlertCircle size={14} />}
                    {c.outcome || '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{c.summary || '—'}</td>
                <td className="px-4 py-3">
                  <Link href={`/calls/${c.id}`} className="text-brand-600 hover:underline text-xs">Détail</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function formatDuration(s: number) {
  if (!s) return '—'
  const m = Math.floor(s / 60), sec = s % 60
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`
}
