import { api } from '@/lib/api'
import AnalyticsCharts from './AnalyticsCharts'

export default async function AnalyticsPage() {
  let stats, byDay, intents
  try {
    ;[stats, byDay, intents] = await Promise.all([
      api.getStats(undefined, 30),
      api.getCallsByDay(undefined, 30),
      api.getIntents(undefined, 30),
    ])
  } catch {
    return <p className="text-red-500">Erreur de chargement des données.</p>
  }

  return <AnalyticsCharts stats={stats} byDay={byDay} intents={intents} />
}
