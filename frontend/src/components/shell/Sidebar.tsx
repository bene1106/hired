import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'

import { HiredMark } from '@/components/brand/HiredMark'
import { HiredWordmark } from '@/components/brand/HiredWordmark'
import { Icon, type IconName } from '@/components/icons/Icon'
import { api } from '@/lib/api'
import { useTheme } from '@/lib/theme'
import type { ProfileResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface NavItem {
  to: string
  label: string
  icon: IconName
  end?: boolean
}

// Only routes that exist today. Materials (PR E), Interview Prep (PR G),
// and the design's "Current Job" land with their screens — the nav grows
// then. No dead/stub entries.
const NAV_ITEMS: NavItem[] = [
  { to: '/app', label: 'Job Feed', icon: 'feed', end: true },
  { to: '/app/applications', label: 'Applications', icon: 'kanban' },
  { to: '/app/settings', label: 'Settings', icon: 'settings' },
]

function initialsOf(name: string | null | undefined, email: string | null | undefined): string {
  const source = name?.trim() || email?.trim() || ''
  if (!source) return 'H'
  const words = source.split(/\s+/).filter(Boolean)
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
  return source.slice(0, 2).toUpperCase()
}

export function Sidebar() {
  const { theme, toggleTheme } = useTheme()
  const [profile, setProfile] = useState<ProfileResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .getProfile()
      .then((p) => {
        if (!cancelled) setProfile(p)
      })
      .catch(() => {
        /* footer just stays minimal — never block the shell */
      })
    return () => {
      cancelled = true
    }
  }, [])

  const displayName = profile?.name?.trim() || profile?.email || 'Your profile'
  const subtitle =
    [profile?.target_roles?.[0], profile?.target_locations?.[0]].filter(Boolean).join(' · ') ||
    (profile?.name ? profile?.email : '') ||
    ''

  return (
    <aside className="sticky top-0 flex h-screen flex-col border-r border-line bg-paper-sunk px-[14px] py-[18px]">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-2 pb-[18px]">
        <HiredMark size={32} />
        <div className="flex flex-col gap-1 leading-none">
          <HiredWordmark size={20} />
          <span className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
            Career Agent
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-px">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'flex w-full items-center gap-2.5 rounded-[7px] border px-2.5 py-2 text-left text-[13px] transition-colors',
                isActive
                  ? 'border-line bg-surface font-medium text-ink shadow-sm'
                  : 'border-transparent text-ink-2 hover:bg-surface-2',
              )
            }
          >
            <Icon name={item.icon} size={15} />
            <span className="flex-1">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="flex-1" />

      {/* Footer — user + theme toggle */}
      <div className="flex items-center gap-2 px-1.5 py-1.5">
        <div
          className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-green-soft text-[12px] font-semibold text-brand-green"
          aria-hidden="true"
        >
          {initialsOf(profile?.name, profile?.email)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[12px] font-medium text-ink">{displayName}</div>
          {subtitle ? <div className="truncate text-[10px] text-ink-3">{subtitle}</div> : null}
        </div>
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title="Toggle theme"
          className="flex h-[34px] w-[34px] items-center justify-center rounded-[10px] text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink"
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={14} />
        </button>
      </div>
    </aside>
  )
}
