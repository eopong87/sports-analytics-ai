import { useEffect, useState } from 'react'
import { fetchNFLScores } from '../utils/api'

export default function NFL() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchNFLScores()
      .then(r => { setData(r.data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  return (
    <div>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>🏈 NFL</h1>
      <p style={{ color: '#64748b', marginBottom: 32 }}>Weekly schedule and player props</p>
      {loading && <p style={{ color: '#64748b' }}>Loading NFL data...</p>}
      {error && <p style={{ color: '#ef4444' }}>Error: {error}</p>}
      {data && (
        <div style={{ background: '#1a1f2e', borderRadius: 12, padding: 24 }}>
          <pre style={{ color: '#94a3b8', fontSize: 13, whiteSpace: 'pre-wrap' }}>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
