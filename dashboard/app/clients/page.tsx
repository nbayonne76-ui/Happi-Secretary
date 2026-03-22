import { api, Client } from '@/lib/api'
import Link from 'next/link'
import { Plus, Phone, Settings } from 'lucide-react'

export default async function ClientsPage() {
  let clients: Client[] = []
  try { clients = await api.getClients() } catch {}

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
        <Link href="/clients/new" className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600">
          <Plus size={16} /> Nouveau client
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {clients.length === 0 && (
          <div className="col-span-3 bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-400">
            Aucun client. Créez votre premier client.
          </div>
        )}
        {clients.map(c => (
          <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="font-semibold text-gray-900">{c.name}</h2>
                <p className="text-xs text-gray-500 capitalize">{c.business_type}</p>
              </div>
              <span className={`w-2.5 h-2.5 rounded-full mt-1.5 ${c.is_active ? 'bg-green-400' : 'bg-gray-300'}`} />
            </div>

            <div className="text-sm space-y-1 text-gray-600">
              <div className="flex items-center gap-2">
                <Phone size={14} className="text-gray-400" />
                {c.phone_number || <span className="text-gray-400 italic">Pas de numéro</span>}
              </div>
              <div>🤖 {c.assistant_name} · {c.language}</div>
              {c.calendar_enabled && <div>📅 Calendrier activé</div>}
            </div>

            <div className="flex gap-2 pt-1">
              <Link href={`/clients/${c.id}`} className="flex-1 text-center text-sm text-brand-600 border border-brand-200 rounded-lg py-1.5 hover:bg-brand-50">
                Configurer
              </Link>
              <Link href={`/knowledge?client=${c.id}`} className="flex-1 text-center text-sm text-gray-600 border border-gray-200 rounded-lg py-1.5 hover:bg-gray-50">
                Base de connaissances
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
