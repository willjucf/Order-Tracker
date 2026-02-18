import React, { useRef, useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import type { ThemeName } from '../hooks/useTheme'

interface ThemesTabProps {
  themeCtx: {
    theme: ThemeName
    setTheme: (t: ThemeName) => void
    panelOpacity: number
    setPanelOpacity: (o: number) => void
  }
  backgroundPath: string | null
  onBackgroundChange: (path: string | null) => void
  username: string
  onUsernameChange: (name: string) => void
}

const THEMES: { key: ThemeName; label: string; colors: string[] }[] = [
  { key: 'dark', label: 'Dark', colors: ['#121212', '#1e1e1e', '#2d2d2d'] },
  { key: 'light', label: 'Light', colors: ['#f5f5f5', '#ffffff', '#e8e8e8'] },
  { key: 'blue', label: 'Blue', colors: ['#1a1a2e', '#16213e', '#0f3460'] },
  { key: 'red', label: 'Red', colors: ['#1a0a0a', '#2a1215', '#3d1a1e'] },
  { key: 'purple', label: 'Purple', colors: ['#120e1a', '#1e1730', '#2d2248'] },
  { key: 'green', label: 'Green', colors: ['#0a1a0e', '#122a18', '#1a3d22'] },
  { key: 'rose', label: 'Rosé', colors: ['#1a0e14', '#2a1522', '#3d1e32'] },
  { key: 'nord', label: 'Nord', colors: ['#2e3440', '#3b4252', '#434c5e'] },
  { key: 'midnight', label: 'Midnight', colors: ['#0a0a14', '#10101e', '#18182a'] },
  { key: 'sunset', label: 'Sunset', colors: ['#1a120e', '#2a1c15', '#3d281e'] },
]

export default function ThemesTab({ themeCtx, backgroundPath, onBackgroundChange, username, onUsernameChange }: ThemesTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('http://127.0.0.1:8420/api/themes/upload-bg', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (data.path) {
        onBackgroundChange(data.path)
      }
    } catch (err) {
      console.error('Upload failed:', err)
    }

    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleRemoveBackground = async () => {
    try {
      await api('/api/themes/bg', { method: 'DELETE' })
      onBackgroundChange(null)
    } catch {}
  }

  return (
    <div style={{ maxWidth: '600px' }}>
      <h3 style={{
        fontSize: '16px',
        fontWeight: 'bold',
        marginBottom: '20px',
        color: 'var(--text-primary)',
      }}>
        Customize
      </h3>

      {/* Username */}
      <div style={{ marginBottom: '32px' }}>
        <label style={{
          fontSize: '14px',
          fontWeight: '600',
          color: 'var(--text-primary)',
          display: 'block',
          marginBottom: '12px',
        }}>
          Display Name
        </label>
        <input
          type="text"
          value={username}
          onChange={e => onUsernameChange(e.target.value)}
          placeholder="Enter your name"
          style={{ width: '100%', maxWidth: '300px' }}
        />
      </div>

      {/* Theme selector */}
      <div style={{ marginBottom: '32px' }}>
        <label style={{
          fontSize: '14px',
          fontWeight: '600',
          color: 'var(--text-primary)',
          display: 'block',
          marginBottom: '12px',
        }}>
          Color Theme
        </label>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          {THEMES.map(t => (
            <button
              key={t.key}
              onClick={() => themeCtx.setTheme(t.key)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                padding: '16px 24px',
                borderRadius: '12px',
                backgroundColor: themeCtx.theme === t.key ? 'var(--bg-hover)' : 'var(--bg-header)',
                border: themeCtx.theme === t.key ? '2px solid var(--accent)' : '2px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {/* Color swatches */}
              <div style={{ display: 'flex', gap: '4px' }}>
                {t.colors.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '6px',
                      backgroundColor: c,
                      border: '1px solid rgba(128,128,128,0.3)',
                    }}
                  />
                ))}
              </div>
              <span style={{
                fontSize: '13px',
                fontWeight: themeCtx.theme === t.key ? 'bold' : 'normal',
                color: themeCtx.theme === t.key ? 'var(--accent)' : 'var(--text-secondary)',
              }}>
                {t.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Background Image */}
      <div style={{ marginBottom: '32px' }}>
        <label style={{
          fontSize: '14px',
          fontWeight: '600',
          color: 'var(--text-primary)',
          display: 'block',
          marginBottom: '12px',
        }}>
          Custom Background
        </label>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleUpload}
            style={{ display: 'none' }}
          />
          <button
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            style={{ padding: '8px 20px' }}
          >
            Upload Image
          </button>

          {backgroundPath && (
            <button
              onClick={handleRemoveBackground}
              style={{
                backgroundColor: 'var(--bg-header)',
                color: 'var(--danger)',
                padding: '8px 20px',
              }}
            >
              Remove
            </button>
          )}
        </div>

        {backgroundPath && (
          <div style={{ marginTop: '10px' }}>
            <div style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              marginBottom: '6px',
            }}>
              Background active
            </div>
            <div style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              backgroundColor: 'var(--bg-header)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '8px 12px',
              lineHeight: '1.5',
            }}>
              💡 <strong>Tip:</strong> For best results, resize the app window to match your image's aspect ratio. The image scales to fill the panel and will crop if the proportions don't match.
            </div>
          </div>
        )}
      </div>

      {/* Panel Opacity */}
      {backgroundPath && (
        <div style={{ marginBottom: '32px' }}>
          <label style={{
            fontSize: '14px',
            fontWeight: '600',
            color: 'var(--text-primary)',
            display: 'block',
            marginBottom: '12px',
          }}>
            Panel Opacity: {Math.round(themeCtx.panelOpacity * 100)}%
          </label>

          <input
            type="range"
            min="0.01"
            max="1"
            step="0.01"
            value={themeCtx.panelOpacity}
            onChange={e => themeCtx.setPanelOpacity(parseFloat(e.target.value))}
            style={{
              width: '100%',
              accentColor: 'var(--accent)',
            }}
          />

          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            marginTop: '4px',
          }}>
            <span>Transparent</span>
            <span>Opaque</span>
          </div>
        </div>
      )}
    </div>
  )
}
