import { useEffect, useState } from 'react'

const fallbackAgents = {
  backend: {
    role: 'Agente A',
    stack: 'Flask + SQLite',
    model: 'CodeLlama',
  },
  frontend: {
    role: 'Agente B',
    stack: 'React + Vite',
    model: 'StarCoder',
  },
  infra: {
    role: 'Agente C',
    stack: 'Docker Compose + GitHub Actions',
    model: 'GPT4All',
  },
}

export default function App() {
  const [agents, setAgents] = useState(fallbackAgents)

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/agents`)
      .then((response) => response.json())
      .then((payload) => {
        if (payload.agents) {
          setAgents(payload.agents)
        }
      })
      .catch(() => {
        setAgents(fallbackAgents)
      })
  }, [])

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">VS Code + IA local + software libre</p>
        <h1>Un workspace para aprender backend, frontend e infraestructura en equipo.</h1>
        <p className="lede">
          Este ejemplo centraliza tres agentes de IA locales y gratuitos para estudiar,
          construir y desplegar aplicaciones sin depender de tokens pagos.
        </p>
      </section>

      <section className="grid">
        {Object.entries(agents).map(([key, value]) => (
          <article className="card" key={key}>
            <span className="badge">{value.role}</span>
            <h2>{key}</h2>
            <p><strong>Modelo:</strong> {value.model}</p>
            <p><strong>Stack:</strong> {value.stack}</p>
            <p>{value.goal}</p>
          </article>
        ))}
      </section>
    </main>
  )
}