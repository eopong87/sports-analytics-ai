import { useEffect, useState } from 'react'
import { fetchOdds, fetchAIInsights } from '../utils/api'
import aiIcon from '../assets/ai-icon.svg'

export default function Betting() {
  const [odds, setOdds] = useState<any>(null)
  const [insights, setInsights] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([fetchOdds(), fetchAIInsights()])
      .then(([o, i]) => {
        setOdds(o.status === 'fulfilled' ? o.value.data : null)
        setInsights(i.status === 'fulfilled' ? i.value.data : null)
        setLoading(false)
      })
  }, [])

  const formatInsights = (text: string) => {
    return text.split('\n').map((line, i) => {
      if (line.startsWith('**') && line.endsWith('**')) {
        return <div key={i} style={{ color: '#a855f7', fontWeight: 700, fontSize: 15, marginTop: 16, marginBottom: 4 }}>{line.replace(/\*\*/g, '')}</div>
      }
      if (line.match(/^\d+\./)) {
        const confidence = line.includes('High') ? '#22c55e' : line.includes('Medium') ? '#f97316' : '#64748b'
        return <div key={i} style={{ color: '#e2e8f0', padding: '8px 12px', borderLeft: `3px solid ${confidence}`, background: '#0f1117', borderRadius: '0 8px 8px 0', marginBottom: 8 }}>{line}</div>
      }
      if (line.trim() === '') return <div key={i} style={{ height: 8 }} />
      return <div key={i} style={{ color: '#94a3b8', marginBottom: 4 }}>{line}</div>
    })
  }

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>🎯 EdgeAI Betting</h1>
      <p style={{ color: '#64748b', marginBottom: 32 }}>AI-powered props and confidence scores</p>
      {loading && <p style={{ color: '#64748b' }}>Loading betting data...</p>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
        {odds && (
          <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 24 }}>
            <h2 style={{ marginBottom: 16, color: '#f97316', display: 'flex', alignItems: 'center', gap: 8 }}>
              📈 Live Odds
            </h2>
            <div style={{ color: '#94a3b8', fontSize: 13 }}>
              <div style={{ padding: '12px 0', borderBottom: '1px solid #2d3748' }}>
                <span style={{ color: '#e2e8f0' }}>Status</span>
                <span style={{ float: 'right', color: '#22c55e' }}>● Active</span>
              </div>
              <div style={{ padding: '12px 0', borderBottom: '1px solid #2d3748' }}>
                <span style={{ color: '#e2e8f0' }}>Odds Processed</span>
                <span style={{ float: 'right' }}>{odds.oddsProcessed ?? 0}</span>
              </div>
              <div style={{ padding: '12px 0' }}>
                <span style={{ color: '#e2e8f0' }}>Last Updated</span>
                <span style={{ float: 'right' }}>{new Date(odds.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
        )}

        {insights?.insights && (
          <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <img src={aiIcon} width="28" height="28" alt="AI" />
              <h2 style={{ color: '#a855f7', fontSize: 18, fontWeight: 700 }}>AI Picks</h2>
              <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: 12 }}>
                {insights.gamesAnalyzed} games analyzed
              </span>
            </div>
            <div style={{ lineHeight: 1.8 }}>
              {formatInsights(insights.insights)}
            </div>
          </div>
        )}

        {!insights?.insights && !loading && (
          <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
            <img src={aiIcon} width="48" height="48" alt="AI" />
            <p style={{ color: '#64748b' }}>No active games to analyze right now</p>
            <p style={{ color: '#475569', fontSize: 13 }}>AI picks will appear when games are live</p>
          </div>
        )}
      </div>
    </div>
  )
}
