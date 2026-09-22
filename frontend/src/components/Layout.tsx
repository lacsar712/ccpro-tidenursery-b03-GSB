import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { clearToken, clearUser, getUser } from '../api/client'

const links = [
  { to: '/', label: '看板', end: true },
  { to: '/hatcheries', label: '育苗场' },
  { to: '/ponds', label: '育苗塘' },
  { to: '/volume-requests', label: '体积变更审批' },
  { to: '/water-samples', label: '水质样' },
  { to: '/feed-events', label: '投喂事件' },
]

export default function Layout() {
  const navigate = useNavigate()
  const user = getUser()

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" />
          <div>
            <div className="brand-title">TideNursery</div>
            <div className="brand-sub">潮汐育苗台账</div>
          </div>
        </div>
        <nav className="nav">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="muted" style={{ fontSize: 13, padding: '0 4px' }}>
          {user ? `${user.display_name}（${user.role === 'admin' ? '场长' : '技术员'}）` : ''}
        </div>
        <button
          className="logout-btn"
          onClick={() => {
            clearToken()
            clearUser()
            navigate('/login')
          }}
        >
          退出登录
        </button>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
