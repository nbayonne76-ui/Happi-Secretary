import { api } from '@/lib/api'
import { ArrowLeft, Calendar, Mic } from 'lucide-react'
import Link from 'next/link'

export default async function CallDetailPage({ params }: { params: { id: string } }) {
  let call
  try { call = await api.getCall(params.id) } catch { return <p className="text-red-500">Appel introuvable.</p> }

  return (
    <div className="max-w-3xl space-y-6">
      <Link href="/calls" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
        <ArrowLeft size={14} /> Retour aux appels
      </Link>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{call.caller_number || 'Numéro inconnu'} {call.is_vip && '⭐'}</h1>
            <p className="text-gray-500 text-sm">
              {call.started_at ? new Date(call.started_at).toLocaleString('fr-FR') : '—'}
              {call.duration_seconds ? ` · ${Math.floor(call.duration_seconds / 60)}m ${call.duration_seconds % 60}s` : ''}
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            call.sentiment === 'urgent' ? 'bg-red-100 text-red-700' :
            call.sentiment === 'negative' ? 'bg-orange-100 text-orange-700' :
            call.sentiment === 'positive' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
          }`}>{call.sentiment || 'neutral'}</span>
        </div>

        {/* Summary */}
        {call.summary && (
          <div className="bg-brand-50 border border-brand-100 rounded-lg p-4">
            <p className="text-sm font-semibold text-brand-700 mb-1">Résumé IA</p>
            <p className="text-sm text-gray-700">{call.summary}</p>
          </div>
        )}

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Meta label="Intention" value={call.intent || '—'} />
          <Meta label="Résultat" value={call.outcome || '—'} />
          <Meta label="Transféré à" value={call.transferred_to || '—'} />
          <Meta label="RDV réservé" value={call.appointment_booked ? `Oui (${call.appointment_id || ''})` : 'Non'} />
        </div>

        {/* Recording */}
        {call.recording_url && (
          <div className="flex items-center gap-2 text-sm">
            <Mic size={16} className="text-brand-500" />
            <a href={call.recording_url} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline">
              Écouter l'enregistrement
            </a>
          </div>
        )}
      </div>

      {/* Transcript */}
      {call.transcript && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-700 mb-3">Transcription complète</h2>
          <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">{call.transcript}</pre>
        </div>
      )}
    </div>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="font-medium capitalize">{value}</p>
    </div>
  )
}
