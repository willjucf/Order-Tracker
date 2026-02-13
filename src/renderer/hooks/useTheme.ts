import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from './useApi'

export type ThemeName = 'dark' | 'light' | 'blue' | 'red' | 'purple' | 'green' | 'rose' | 'nord' | 'midnight' | 'sunset'

const VALID_THEMES: ThemeName[] = ['dark', 'light', 'blue', 'red', 'purple', 'green', 'rose', 'nord', 'midnight', 'sunset']

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeName>('dark')
  const [panelOpacity, setPanelOpacityState] = useState<number>(0.85)
  const initialized = useRef(false)

  // Load settings from backend on mount
  useEffect(() => {
    api<{ theme?: string; panelOpacity?: number }>('/api/settings')
      .then(settings => {
        if (settings.theme && VALID_THEMES.includes(settings.theme as ThemeName)) {
          setThemeState(settings.theme as ThemeName)
        }
        if (settings.panelOpacity !== undefined) {
          setPanelOpacityState(settings.panelOpacity)
        }
        initialized.current = true
      })
      .catch(() => {
        initialized.current = true
      })
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    if (initialized.current) {
      api('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({ theme }),
      }).catch(() => {})
    }
  }, [theme])

  useEffect(() => {
    document.documentElement.style.setProperty('--panel-opacity', String(panelOpacity))
    if (initialized.current) {
      api('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({ panelOpacity }),
      }).catch(() => {})
    }
  }, [panelOpacity])

  const setTheme = useCallback((t: ThemeName) => {
    setThemeState(t)
  }, [])

  const setPanelOpacity = useCallback((o: number) => {
    setPanelOpacityState(o)
  }, [])

  return { theme, setTheme, panelOpacity, setPanelOpacity }
}
