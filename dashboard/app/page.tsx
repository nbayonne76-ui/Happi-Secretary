import React from 'react'
import { api, Stats } from '@/lib/api'
import { Phone, Calendar, MessageSquare, TrendingUp, Clock, AlertTriangle } from 'lucide-react'

export default async function DashboardPage() {
  let stats: Stats | null = null
  let byDay: { day: string; count: number }[] = []
  let intents: { intent: string; count: number }[] = []
  try {
    ;[stats, byDay, intents] = await Promise.all([
      api.getStats(undefined, 30),
      api.getCallsByDay(undefined, 30),
      api.getIntents(undefined, 30),
    ])
  } catch {
    stats = null; byDay = []; intents = []
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
        <p className="text-gray-500 text-sm mt-1">30 derniers jours</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard icon={<Phone size={20} />}  label="Appels total"          value={stats?.total_calls ?? '—'}     color="blue" />
        <StatCard icon={<TrendingUp size={20} />} label="Taux résolution"   value={stats ? `${stats.resolution_rate}%` : '—'} color="green" />
        <StatCard icon={<Calendar size={20} />}  label="RDV réservés"       value={stats?.appointments_booked ?? '—'} color="purple" />
        <StatCard icon={<MessageSquare size={20} />} label="Messages pris"  value={stats?.messages_taken ?? '—'}  color="orange" />
        <StatCard icon={<Clock size={20} />}     label="Durée moy. (s)"     value={stats?.avg_duration_seconds ?? '—'} color="gray" />
        <StatCard icon={<AlertTriangle size={20} />} label="Appels manqués" value={stats?.missed_calls ?? '—'}    color="red" />
      </div>

      {/* Sentiment + Intents */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Sentiment des appelants</h2>
          {stats ? (
            <div className="space-y-3">
              <SentimentBar label="Positif"  value={stats.sentiment.positive} total={stats.total_calls} color="bg-green-400" />
              <SentimentBar label="Neutre"   value={stats.sentiment.neutral}  total={stats.total_calls} color="bg-gray-300" />
              <SentimentBar label="Négatif"  value={stats.sentiment.negative} total={stats.total_calls} color="bg-orange-400" />
              <SentimentBar label="Urgent"   value={stats.sentiment.urgent}   total={stats.total_calls} color="bg-red-500" />
            </div>
          ) : <p className="text-gray-400 text-sm">Aucune donnée</p>}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Intentions d'appel</h2>
          {intents.length > 0 ? (
            <div className="space-y-2">
              {intents.map((i: any) => (
                <div key={i.intent} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 capitalize">{INTENT_FR[i.intent] || i.intent}</span>
                  <span className="text-sm font-semibold text-brand-600">{i.count}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-400 text-sm">Aucune donnée</p>}
        </div>
      </div>
    </div>
  )
}

const INTENT_FR: Record<string, string> = {
  appointment: 'Prise de rendez-vous',
  support: 'Support client',
  order: 'Commande',
  info: "Demande d'information",
  complaint: 'Réclamation',
  other: 'Autre',
}

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: any; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600', green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600', orange: 'bg-orange-50 text-orange-600',
    gray: 'bg-gray-100 text-gray-600', red: 'bg-red-50 text-red-600',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${colors[color]}`}>{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function SentimentBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{value} ({pct}%)</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
