import { ArrowRight, CircleAlert, MapPin, Utensils } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink, Outlet } from 'react-router'

export function Layout() {
  return (
    <div className="site">
      <header className="site-header">
        <div className="wrap nav">
          <Link to="/" className="brand"><span className="brand-icon"><Utensils size={19} /></span> FoodMatch<span className="brand-dot">.</span></Link>
          <nav aria-label="Main navigation">
            <NavLink to="/solo">Find Food</NavLink>
            <NavLink to="/create" className="nav-group">Create Group <ArrowRight size={15} /></NavLink>
          </nav>
        </div>
      </header>
      <main className="main"><Outlet /></main>
      <footer className="site-footer wrap">
        <span>FoodMatch <span aria-hidden="true">·</span> Good food, good company.</span>
        <div><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link></div>
      </footer>
    </div>
  )
}

export function Page({ eyebrow, title, description, children }: {
  eyebrow?: string; title: string; description?: ReactNode; children: ReactNode
}) {
  return (
    <section className="page wrap">
      <div className="page-heading">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="subtle">{description}</p>}
      </div>
      {children}
    </section>
  )
}

export function Loading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="loading panel" role="status" aria-label={label}>
      <div className="skeleton skeleton-picture" />
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-line" />
      <span className="sr-only">{label}…</span>
    </div>
  )
}

export function Problem({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="problem" role="alert">
      <CircleAlert size={19} />
      <span>{message}</span>
      {retry && <button type="button" className="text-link" onClick={retry}>Try again</button>}
    </div>
  )
}

export function Location({ name }: { name: string }) {
  return <span className="location"><MapPin size={16} /> {name}</span>
}
