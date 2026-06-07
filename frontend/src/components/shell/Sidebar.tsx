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

const NAV_ITEMS: NavItem[] = [
  { to: '/app', label: 'Job Feed', icon: 'feed', end: true },
  { to: '/app/applications', label: 'Applications', icon: 'kanban' },
  { to: '/app/sources', label: 'Job Sources', icon: 'globe' },
  { to: '/app/settings', label: 'Settings', icon: 'settings' },
]

function initialsOf(name: string | null | undefined, email: string | null | undefined): string {
  const source = name?.trim() || email?.trim() || ''
  if (!source) return 'H'
  const words = source.split(/\s+/).filter(Boolean)
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
  return source.slice(0, 2).toUpperCase()
}

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
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
        /* footer stays minimal — never block the shell */
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
    <aside
      className={cn(
        'sticky top-0 flex h-screen flex-col border-r border-line bg-paper-sunk py-[18px] transition-all duration-200',
        collapsed ? 'items-center px-[10px]' : 'px-[14px]',
      )}
    >
      {/* Brand + collapse toggle */}
      <div
        className={cn(
          'flex items-center pb-[18px]',
          collapsed ? 'justify-center' : 'justify-between gap-2.5 px-2',
        )}
      >
        {!collapsed && (
          <div className="flex items-center gap-2.5">
            <HiredMark size={32} />
            <div className="flex flex-col gap-1 leading-none">
              <HiredWordmark size={20} />
              <span className="font-mono text-[9.5px] uppercase tracking-[0.1em] text-ink-3">
                Career Agent
              </span>
            </div>
          </div>
        )}
        {collapsed && <HiredMark size={28} />}
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn(
            'flex h-[28px] w-[28px] items-center justify-center rounded-[8px] text-ink-3 transition-colors hover:bg-surface-2 hover:text-ink',
            collapsed && 'mt-1',
          )}
        >
          <Icon name={collapsed ? 'arrowRight' : 'arrowLeft'} size={13} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-px">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              cn(
                'flex w-full items-center rounded-[7px] border transition-colors',
                collapsed
                  ? 'justify-center px-1.5 py-2'
                  : 'gap-2.5 px-2.5 py-2 text-[13px]',
                isActive
                  ? 'border-line bg-surface font-medium text-ink shadow-sm'
                  : 'border-transparent text-ink-2 hover:bg-surface-2',
              )
            }
          >
            <Icon name={item.icon} size={15} />
            {!collapsed && <span className="flex-1">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="flex-1" />

      {/* Footer — user + theme toggle */}
      {collapsed ? (
        <div className="flex flex-col items-center gap-2 py-1.5">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-green-soft text-[12px] font-semibold text-brand-green"
            aria-hidden="true"
            title={displayName}
          >
            {initialsOf(profile?.name, profile?.email)}
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
      ) : (
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
      )}
    </aside>
  )
}
