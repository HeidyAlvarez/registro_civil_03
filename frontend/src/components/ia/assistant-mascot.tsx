import { useEffect, useState } from 'react'
import '../../../../ia/static/ia/css/mascota.css'

type Estado = 'idle' | 'pensando' | 'hablando' | 'saludo'

const frases = {
  ciudadano: {
    idle: '¿En qué trámite te ayudo?',
    pensando: 'Estoy revisando el catálogo…',
    hablando: 'Listo, te lo explico.',
    saludo: '¡Hola! Soy el asistente del Registro Civil.',
  },
  interno: {
    idle: '¿Qué decisión revisamos?',
    pensando: 'Estoy consultando la agenda…',
    hablando: 'Esto muestran los datos de hoy.',
    saludo: 'Listo para apoyar. La decisión la tomas tú.',
  },
} as const

export function AssistantMascot({ modo, estado }: { modo: 'ciudadano' | 'interno'; estado: 'idle' | 'pensando' | 'hablando' }) {
  const [visible, setVisible] = useState<Estado>(estado)
  const [mirada, setMirada] = useState({ x: 0, y: 0 })

  useEffect(() => { setVisible(estado) }, [estado])
  useEffect(() => {
    if (visible !== 'hablando' && visible !== 'saludo') return
    const timer = window.setTimeout(() => setVisible('idle'), 2800)
    return () => window.clearTimeout(timer)
  }, [visible])

  const texto = frases[modo][visible]
  return (
    <div className={`rc-mascota${visible === 'saludo' ? ' is-saludo' : ''}`} data-estado={visible}>
      <div
        className="rc-mascota-escena"
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect()
          setMirada({
            x: ((event.clientX - rect.left) / rect.width - 0.5) * 5,
            y: ((event.clientY - rect.top) / rect.height - 0.5) * 4,
          })
        }}
        onMouseLeave={() => setMirada({ x: 0, y: 0 })}
      >
        <p className="rc-mascota-burbuja">
          {texto}
          <span className="rc-mascota-puntos" aria-hidden="true"><i /><i /><i /></span>
        </p>
        <div className="rc-mascota-tarjeta" aria-hidden="true">
          <span className="rc-mascota-avatar" />
          <span className="rc-mascota-linea" />
          <span className="rc-mascota-linea rc-mascota-linea--corta" />
        </div>
        <button type="button" className="rc-mascota-robot" aria-label="Saludar al asistente" onClick={() => setVisible('saludo')}>
          <svg viewBox="0 0 180 210" aria-hidden="true">
            <line x1="90" y1="28" x2="90" y2="12" stroke="#d1fae5" strokeWidth="4" strokeLinecap="round" />
            <circle className="rc-antena-luz" cx="90" cy="10" r="6" fill="#34d399" />
            <path d="M52 64c0-30 16-46 38-46s38 16 38 46" fill="none" stroke="#d1fae5" strokeWidth="7" strokeLinecap="round" />
            <rect x="46" y="30" width="88" height="74" rx="34" fill="#f7fffb" stroke="#0b4a2b" strokeWidth="3" />
            <circle cx="50" cy="72" r="9" fill="#0b4a2b" />
            <path d="M42 74c6 8 6 16 0 24" fill="none" stroke="#d1fae5" strokeWidth="3" strokeLinecap="round" />
            <g className="rc-ojo"><ellipse cx="74" cy="64" rx="13" ry="15" fill="#34d399" /><circle className="rc-pupila" cx="74" cy="66" r="5" fill="#064e3b" transform={`translate(${mirada.x} ${mirada.y})`} /></g>
            <g className="rc-ojo"><ellipse cx="106" cy="64" rx="13" ry="15" fill="#34d399" /><circle className="rc-pupila" cx="106" cy="66" r="5" fill="#064e3b" transform={`translate(${mirada.x} ${mirada.y})`} /></g>
            <path className="rc-sonrisa" d="M78 86q12 10 24 0" fill="none" stroke="#0b4a2b" strokeWidth="3" strokeLinecap="round" />
            <ellipse className="rc-boca" cx="90" cy="88" rx="7" ry="4" fill="#0b4a2b" />
            <rect x="58" y="110" width="64" height="62" rx="26" fill="#f7fffb" stroke="#0b4a2b" strokeWidth="3" />
            <circle cx="90" cy="138" r="13" fill="#0b4a2b" />
            <circle cx="90" cy="138" r="6" fill="#d1fae5" />
            <rect x="34" y="118" width="20" height="46" rx="10" fill="#f7fffb" stroke="#0b4a2b" strokeWidth="3" />
            <g className="rc-brazo">
              <rect x="126" y="112" width="20" height="48" rx="10" fill="#f7fffb" stroke="#0b4a2b" strokeWidth="3" />
              <circle cx="136" cy="166" r="11" fill="#f7fffb" stroke="#0b4a2b" strokeWidth="3" />
            </g>
            <rect x="70" y="174" width="14" height="22" rx="7" fill="#d1fae5" />
            <rect x="96" y="174" width="14" height="22" rx="7" fill="#d1fae5" />
          </svg>
        </button>
      </div>
    </div>
  )
}
