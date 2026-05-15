import { useEffect, useState } from 'react'
import { fetchNBAScores, fetchNFLScores, fetchMLBScores, fetchAIInsights } from '../utils/api'
import aiIcon from '../assets/ai-icon.svg'

export default function Dashboard() {
  const [data, setData] = useState<any>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([fetchNBAScores(), fetchNFLScores(), fetchMLBScores(), fetchAIInsights()])
      .then(([nba, nfl, mlb, ai]) => {
        setData({
          nba: nba.status === 'fulfilled' ? nba.value.data : null,
          nfl: nfl.status === 'fulfilled' ? nfl.value.data : null,
          mlb: mlb.status === 'fulfilled' ? mlb.value.data : null,
          ai: ai.status === 'fulfilled' ? ai.value.data : null,
        })
        setLoading(false)
      })
  }, [])

  const cards = [
    { label: 'NBA Games', value: data.nba?.count ?? '--', color: '#f97316', icon: (
      <svg viewBox="0 0 100 100" width="48" height="48">
        <circle cx="50" cy="50" r="45" fill="#f97316" opacity="0.15"/>
        <circle cx="50" cy="50" r="35" fill="none" stroke="#f97316" strokeWidth="3"/>
        <path d="M50 15 C50 15 50 85 50 85" stroke="#f97316" strokeWidth="2.5"/>
        <path d="M15 50 C15 50 85 50 85 50" stroke="#f97316" strokeWidth="2.5"/>
        <path d="M22 28 C35 38 35 62 22 72" fill="none" stroke="#f97316" strokeWidth="2.5"/>
        <path d="M78 28 C65 38 65 62 78 72" fill="none" stroke="#f97316" strokeWidth="2.5"/>
      </svg>
    )},
    { label: 'NFL Games', value: data.nfl?.count ?? '--', color: '#22c55e', icon: (
      <svg viewBox="0 0 100 100" width="48" height="48">
        <circle cx="50" cy="50" r="45" fill="#22c55e" opacity="0.15"/>
        <ellipse cx="50" cy="50" rx="32" ry="22" fill="none" stroke="#22c55e" strokeWidth="3"/>
        <line x1="50" y1="28" x2="50" y2="72" stroke="#22c55e" strokeWidth="2"/>
        <line x1="38" y1="38" x2="62" y2="38" stroke="#22c55e" strokeWidth="2"/>
        <line x1="35" y1="50" x2="65" y2="50" stroke="#22c55e" strokeWidth="2"/>
        <line x1="38" y1="62" x2="62" y2="62" stroke="#22c55e" strokeWidth="2"/>
      </svg>
    )},
    { label: 'MLB Games', value: data.mlb?.count ?? '--', color: '#3b82f6', icon: (
      <svg viewBox="0 0 100 100" width="48" height="48">
        <circle cx="50" cy="50" r="45" fill="#3b82f6" opacity="0.15"/>
        <circle cx="50" cy="50" r="32" fill="none" stroke="#3b82f6" strokeWidth="3"/>
        <path d="M26 30 C35 42 35 58 26 70" fill="none" stroke="#3b82f6" strokeWidth="2"/>
        <path d="M74 30 C65 42 65 58 74 70" fill="none" stroke="#3b82f6" strokeWidth="2"/>
        <circle cx="50" cy="50" r="5" fill="#3b82f6" opacity="0.6"/>
      </svg>
    )},
    { label: 'AI Insights', value: data.ai?.gamesAnalyzed ?? '--', color: '#a855f7', icon: (
      <img src={aiIcon} width="48" height="48" alt="AI" />
    )},
  ]

  const formatInsights = (text: string) => {
    return text.split('\n').map((line, i) => {
      if (line.startsWith('**') && line.endsWith('**')) {
        return <div key={i} style={{ color: '#a855f7', fontWeight: 700, fontSize: 15, marginTop: 16, marginBottom: 4 }}>{line.replace(/\*\*/g, '')}</div>
      }
      if (line.match(/^\d+\./)) {
        return <div key={i} style={{ color: '#e2e8f0', padding: '4px 0 4px 16px', borderLeft: '2px solid #a855f7', marginBottom: 6 }}>{line}</div>
      }
      if (line.trim() === '') return <div key={i} style={{ height: 8 }} />
      return <div key={i} style={{ color: '#94a3b8', marginBottom: 4 }}>{line}</div>
    })
  }

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Dashboard</h1>
      <p style={{ color: '#64748b', marginBottom: 32 }}>Live sports data powered by AI</p>
      {loading && <p style={{ color: '#64748b' }}>Loading live data...</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 32 }}>
        {cards.map(({ label, value, color, icon }) => (
          <div key={label} style={{ background: '#1a1f2e', borderRadius: 12, padding: 24, borderLeft: `4px solid ${color}` }}>
            <div style={{ marginBottom: 12 }}>{icon}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
            <div style={{ color: '#94a3b8', marginTop: 4 }}>{label}</div>
          </div>
        ))}
      </div>

      {data.ai?.insights && (
        <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
            <img src={aiIcon} width="32" height="32" alt="AI" />
            <h2 style={{ color: '#a855f7', fontSize: 18, fontWeight: 700 }}>Latest AI Insights</h2>
            <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: 12 }}>
              {data.ai.gamesAnalyzed} games analyzed
            </span>
          </div>
          <div style={{ lineHeight: 1.7 }}>
            {formatInsights(data.ai.insights)}
          </div>
        </div>
      )}
    </div>
  )
}
