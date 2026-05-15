import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import NBA from './pages/NBA'
import NFL from './pages/NFL'
import MLB from './pages/MLB'
import Betting from './pages/Betting'

const nav = [
  { path: '/', label: '📊 Dashboard' },
  { path: '/nba', label: '🏀 NBA' },
  { path: '/nfl', label: '🏈 NFL' },
  { path: '/mlb', label: '⚾ MLB' },
  { path: '/betting', label: '🎯 EdgeAI Bets' },
]

export default function App() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <nav style={{ width: 220, background: '#1a1f2e', padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#60a5fa', marginBottom: 24, padding: '0 8px' }}>
          ⚡ Sports AI
        </div>
        {nav.map(({ path, label }) => (
          <NavLink key={path} to={path} end={path === '/'}
            style={({ isActive }) => ({
              padding: '10px 12px', borderRadius: 8, textDecoration: 'none',
              color: isActive ? '#fff' : '#94a3b8',
              background: isActive ? '#3b82f6' : 'transparent',
              fontWeight: isActive ? 600 : 400,
            })}>
            {label}
          </NavLink>
        ))}
      </nav>
      <main style={{ flex: 1, padding: 32, overflowY: 'auto' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/nba" element={<NBA />} />
          <Route path="/nfl" element={<NFL />} />
          <Route path="/mlb" element={<MLB />} />
          <Route path="/betting" element={<Betting />} />
        </Routes>
      </main>
    </div>
  )
}
