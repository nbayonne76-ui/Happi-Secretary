'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart2, Phone, Users, BookOpen, Mic, PhoneCall } from 'lucide-react'
import clsx from 'clsx'
import { useState, useEffect } from 'react'

const NAV = {
  fr: [
    { href: '/',           label: 'Tableau de bord',       icon: BarChart2 },
    { href: '/calls',      label: 'Appels',                icon: Phone },
    { href: '/clients',    label: 'Clients',               icon: Users },
    { href: '/knowledge',  label: 'Base de connaissances', icon: BookOpen },
    { href: '/analytics',  label: 'Analytiques',           icon: BarChart2 },
    { href: '/simulator',  label: 'Simulateur',            icon: PhoneCall },
  ],
  en: [
    { href: '/',           label: 'Dashboard',             icon: BarChart2 },
    { href: '/calls',      label: 'Calls',                 icon: Phone },
    { href: '/clients',    label: 'Clients',               icon: Users },
    { href: '/knowledge',  label: 'Knowledge Base',        icon: BookOpen },
    { href: '/analytics',  label: 'Analytics',             icon: BarChart2 },
    { href: '/simulator',  label: 'Simulator',             icon: PhoneCall },
  ],
}

export type Lang = 'fr' | 'en'

export default function Sidebar() {
  const path = usePathname()
  const [lang, setLang] = useState<Lang>('fr')

  useEffect(() => {
    const saved = localStorage.getItem('happi_lang') as Lang | null
    if (saved) setLang(saved)
  }, [])

  function toggleLang() {
    const next: Lang = lang === 'fr' ? 'en' : 'fr'
    setLang(next)
    localStorage.setItem('happi_lang', next)
  }

  const nav = NAV[lang]

  return (
    <aside className="w-60 bg-white border-r border-gray-200 flex flex-col shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-gray-100">
        <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
          <Mic size={16} className="text-white" />
        </div>
        <span className="font-bold text-gray-900 text-lg">Happi</span>
        <span className="text-brand-500 font-bold text-lg">Secretary</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              path === href
                ? 'bg-brand-50 text-brand-600'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-gray-100 flex items-center justify-between">
        <span className="text-xs text-gray-400">v1.0.0</span>
        <button
          onClick={toggleLang}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 text-xs font-semibold text-gray-600 hover:bg-gray-100 transition-colors"
        >
          <span className={lang === 'fr' ? 'text-brand-500' : 'text-gray-400'}>FR</span>
          <span className="text-gray-300">|</span>
          <span className={lang === 'en' ? 'text-brand-500' : 'text-gray-400'}>EN</span>
        </button>
      </div>
    </aside>
  )
}
