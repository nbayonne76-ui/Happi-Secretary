'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api, Client } from '@/lib/api'
import { ArrowLeft, Save, Loader2 } from 'lucide-react'
import Link from 'next/link'

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
const DAYS_FR: Record<string, string> = {
  monday: 'Lundi', tuesday: 'Mardi', wednesday: 'Mercredi',
  thursday: 'Jeudi', friday: 'Vendredi', saturday: 'Samedi', sunday: 'Dimanche',
}

export default function ClientConfigPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [client, setClient] = useState<Client | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (id) api.getClient(id).then(setClient).catch(() => router.push('/clients'))
  }, [id])

  if (!client) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="animate-spin text-brand-500" size={28} />
    </div>
  )

  async function save() {
    if (!client) return
    setSaving(true)
    try {
      await api.updateClient(client.id, client)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  function set(field: keyof Client, val: any) {
    setClient(prev => prev ? { ...prev, [field]: val } : prev)
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/clients" className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft size={14} /> Clients
        </Link>
        <button
          onClick={save}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-60"
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {saved ? 'Sauvegardé ✓' : 'Sauvegarder'}
        </button>
      </div>

      <Section title="Informations générales">
        <Field label="Nom du client"><Input value={client.name} onChange={v => set('name', v)} /></Field>
        <Field label="Type de business"><Input value={client.business_type} onChange={v => set('business_type', v)} /></Field>
        <Field label="Nom de l'assistant IA"><Input value={client.assistant_name} onChange={v => set('assistant_name', v)} /></Field>
        <Field label="Langue">
          <select className={SELECT_CLS} value={client.language} onChange={e => set('language', e.target.value)}>
            <option value="fr-FR">Français</option>
            <option value="en-US">English</option>
            <option value="es-ES">Español</option>
          </select>
        </Field>
      </Section>

      <Section title="Messages">
        <Field label="Message d'accueil">
          <textarea className={TEXTAREA_CLS} value={client.greeting_message} onChange={e => set('greeting_message', e.target.value)} rows={2} />
        </Field>
        <Field label="Message hors horaires">
          <textarea className={TEXTAREA_CLS} value={client.after_hours_message} onChange={e => set('after_hours_message', e.target.value)} rows={2} />
        </Field>
        <Field label="Prompt système (comportement avancé)">
          <textarea className={TEXTAREA_CLS} value={client.system_prompt || ''} onChange={e => set('system_prompt', e.target.value)} rows={4} placeholder="Décrivez le comportement de votre assistant..." />
        </Field>
      </Section>

      <Section title="Horaires d'ouverture">
        <div className="space-y-2">
          {DAYS.map(day => {
            const h = client.business_hours?.[day] || { open: '09:00', close: '18:00', enabled: false }
            return (
              <div key={day} className="flex items-center gap-3 text-sm">
                <input type="checkbox" checked={h.enabled} onChange={e => set('business_hours', { ...client.business_hours, [day]: { ...h, enabled: e.target.checked } })} className="accent-brand-500" />
                <span className="w-24 text-gray-700">{DAYS_FR[day]}</span>
                <input type="time" value={h.open} disabled={!h.enabled} onChange={e => set('business_hours', { ...client.business_hours, [day]: { ...h, open: e.target.value } })} className="border border-gray-200 rounded px-2 py-1 disabled:opacity-40" />
                <span className="text-gray-400">—</span>
                <input type="time" value={h.close} disabled={!h.enabled} onChange={e => set('business_hours', { ...client.business_hours, [day]: { ...h, close: e.target.value } })} className="border border-gray-200 rounded px-2 py-1 disabled:opacity-40" />
              </div>
            )
          })}
        </div>
      </Section>

      <Section title="Notifications">
        <Field label="Email de notification"><Input value={client.notification_email || ''} onChange={v => set('notification_email', v)} type="email" /></Field>
        <Field label="SMS de notification"><Input value={client.notification_sms || ''} onChange={v => set('notification_sms', v)} /></Field>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={client.send_transcript_email} onChange={e => set('send_transcript_email', e.target.checked)} className="accent-brand-500" /> Transcription par email</label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={client.send_transcript_sms} onChange={e => set('send_transcript_sms', e.target.checked)} className="accent-brand-500" /> Résumé par SMS</label>
        </div>
      </Section>

      <Section title="Calendrier (Cal.com)">
        <label className="flex items-center gap-2 text-sm mb-3"><input type="checkbox" checked={client.calendar_enabled} onChange={e => set('calendar_enabled', e.target.checked)} className="accent-brand-500" /> Activer la prise de rendez-vous</label>
        {client.calendar_enabled && (
          <>
            <Field label="Cal.com API Key"><Input value={(client as any).calcom_api_key || ''} onChange={v => set('calcom_api_key' as any, v)} type="password" /></Field>
            <Field label="Event Type ID"><Input value={String(client.calcom_event_type_id || '')} onChange={v => set('calcom_event_type_id', Number(v))} /></Field>
          </>
        )}
      </Section>

      <Section title="Intégration CRM">
        <Field label="Webhook URL"><Input value={client.crm_webhook_url || ''} onChange={v => set('crm_webhook_url', v)} placeholder="https://hooks.zapier.com/..." /></Field>
      </Section>

      <Section title="Fonctionnalités">
        {Object.entries(client.features || {}).map(([key, val]) => (
          <label key={key} className="flex items-center gap-2 text-sm capitalize">
            <input type="checkbox" checked={!!val} onChange={e => set('features', { ...client.features, [key]: e.target.checked })} className="accent-brand-500" />
            {key.replace(/_/g, ' ')}
          </label>
        ))}
      </Section>
    </div>
  )
}

const INPUT_CLS = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300'
const TEXTAREA_CLS = `${INPUT_CLS} resize-none`
const SELECT_CLS = `${INPUT_CLS} bg-white`

function Input({ value, onChange, type = 'text', placeholder = '' }: { value: string; onChange: (v: string) => void; type?: string; placeholder?: string }) {
  return <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} className={INPUT_CLS} />
}
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
      <h2 className="font-semibold text-gray-800 text-base">{title}</h2>
      {children}
    </div>
  )
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-gray-600">{label}</label>
      {children}
    </div>
  )
}
