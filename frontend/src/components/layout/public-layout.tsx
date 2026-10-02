import { Outlet } from 'react-router-dom'
import { PublicFooter } from '@/components/public/public-footer'
import { PublicHeader } from '@/components/public/public-header'

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-warm-100 text-warm-900">
      <a href="#contenido" className="sr-only z-50 rounded-xl bg-white p-3 focus:not-sr-only focus:fixed focus:left-4 focus:top-4">
        Saltar al contenido
      </a>
      <PublicHeader />
      <main id="contenido" className="mx-auto w-full max-w-7xl px-4 py-8 md:py-12" tabIndex={-1}>
        <Outlet />
      </main>
      <PublicFooter />
    </div>
  )
}
