'use client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Stats } from '@/lib/api'

const COLORS = ['#6C63FF', '#34D399', '#FBBF24', '#F87171', '#60A5FA']
const INTENT_FR: Record<string, string> = {
  appointment: 'RDV', support: 'Support', order: 'Commande',
  info: 'Info', complaint: 'Réclamation', other: 'Autre',
}

interface Props {
  stats: Stats
  byDay: { day: string; count: number }[]
  intents: { intent: string; count: number }[]
}

export default function AnalyticsCharts({ stats, byDay, intents }: Props) {
  const sentimentData = [
    { name: 'Positif', value: stats.sentiment.positive },
    { name: 'Neutre',  value: stats.sentiment.neutral },
    { name: 'Négatif', value: stats.sentiment.negative },
    { name: 'Urgent',  value: stats.sentiment.urgent },
  ].filter(d => d.value > 0)

  const intentData = intents.map(i => ({
    name: INTENT_FR[i.intent] || i.intent,
    count: i.count,
  }))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Analytiques — 30 derniers jours</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Big label="Total appels"       value={stats.total_calls} />
        <Big label="Taux de résolution" value={`${stats.resolution_rate}%`} />
        <Big label="Durée moyenne"      value={`${Math.floor(stats.avg_duration_seconds / 60)}m ${stats.avg_duration_seconds % 60}s`} />
        <Big label="RDV réservés"       value={stats.appointments_booked} />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-700 mb-4">Volume d'appels par jour</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={byDay}>
            <XAxis dataKey="day" tick={{ fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#6C63FF" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Sentiment</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={sentimentData}
                dataKey="value"
                nameKey="name"
                cx="50%" cy="50%"
                outerRadius={80}
                label={({ name, percent }: { name: string; percent: number }) =>
                  `${name} ${(percent * 100).toFixed(0)}%`
                }
              >
                {sentimentData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Intentions</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={intentData} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={80} />
              <Tooltip />
              <Bar dataKey="count" fill="#34D399" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function Big({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 text-center">
      <div className="text-3xl font-bold text-brand-600">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}
