import { useState } from 'react'
import { ChevronLeft, Download, RefreshCw } from 'lucide-react'
import type { IntentModel } from '../App'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000'

interface Props {
  sessionId: string
  projectName: string
  intentModel: IntentModel
  generatedImageUrl: string | null
  floorplanSvg: string | null
  authToken: string
  onBack: () => void
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-1.5 mb-3">
      <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75] shrink-0" />
      <span
        className="font-semibold tracking-[0.1em] uppercase"
        style={{ fontSize: 10, color: '#1D9E75' }}
      >
        {label}
      </span>
    </div>
  )
}

export default function ExportPage({
  sessionId,
  projectName,
  intentModel,
  generatedImageUrl,
  floorplanSvg,
  authToken,
  onBack,
}: Props) {
  const [isDownloading, setIsDownloading] = useState(false)

  const intent = (intentModel.intent as Record<string, unknown>) ?? {}
  const project = (intentModel.project as Record<string, unknown>) ?? {}
  const site = (intentModel.site as Record<string, unknown>) ?? {}
  const style = (intentModel.style as Record<string, unknown>) ?? {}
  const budget = (intentModel.budget as Record<string, unknown>) ?? {}
  const program = (intentModel.program as Record<string, unknown>) ?? {}
  const spaces = (program.spaces as unknown[]) ?? []
  const today = new Date().toLocaleDateString('cs-CZ', { day: 'numeric', month: 'long', year: 'numeric' })

  async function handleDownload() {
    setIsDownloading(true)
    try {
      const res = await fetch(`${API}/api/export-pdf`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({})) as { error?: string }
        throw new Error(err.error ?? `HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `archbrief-${projectName.toLowerCase().replace(/\s+/g, '-')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Chyba při generování PDF')
    } finally {
      setIsDownloading(false)
    }
  }

  const sectionStyle: React.CSSProperties = {
    background: '#111',
    border: '1px solid #1E1E1E',
    borderRadius: 12,
    padding: 24,
    marginBottom: 12,
  }

  const bodyTextStyle: React.CSSProperties = {
    fontSize: 13,
    color: '#888',
    lineHeight: 1.65,
  }

  return (
    <div className="h-screen flex flex-col bg-[#0A0A0A]">
      {/* Header */}
      <header
        className="bg-[#0A0A0A] px-5 flex items-center gap-3 shrink-0"
        style={{ height: 52, borderBottom: '1px solid #1E1E1E' }}
      >
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm transition-colors duration-150"
          style={{ color: '#666' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#888')}
          onMouseLeave={e => (e.currentTarget.style.color = '#666')}
        >
          <ChevronLeft size={16} />
          Zpět do projektu
        </button>
        <div className="flex-1" />
        <button
          onClick={() => void handleDownload()}
          disabled={isDownloading}
          className="flex items-center gap-2 px-4 py-2 bg-[#1D9E75] text-white
            rounded-lg text-sm font-medium hover:bg-[#17856A] disabled:opacity-50 transition-colors duration-150"
        >
          {isDownloading
            ? <><RefreshCw size={14} className="animate-spin" />Generuji PDF…</>
            : <><Download size={14} />Stáhnout PDF</>}
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-[860px] mx-auto">

          {/* Nadpis */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="font-semibold text-[#E8E8E8]" style={{ fontSize: 22 }}>
                Váš ArchBrief je připraven
              </h1>
              <p style={{ fontSize: 13, color: '#666', marginTop: 3 }}>Náhled obsahu dokumentu</p>
            </div>
            <div className="font-bold text-[#1D9E75]" style={{ fontSize: 20 }}>ArchBrief</div>
          </div>

          {/* Titulní strana */}
          <div style={sectionStyle}>
            <SectionLabel label="Titulní strana" />
            <p className="font-bold text-[#1D9E75]" style={{ fontSize: 22 }}>ArchBrief</p>
            <p className="text-[#E8E8E8] mt-1" style={{ fontSize: 16 }}>{projectName}</p>
            <p style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
              Připraveno pro předání architektovi · {today}
            </p>
          </div>

          {/* Shrnutí záměru */}
          <div style={sectionStyle}>
            <SectionLabel label="Shrnutí záměru" />
            <div className="space-y-1.5" style={bodyTextStyle}>
              {intent.primary_goal && (
                <p><span style={{ color: '#777' }}>Primární cíl:</span>{' '}
                  <span style={{ color: '#888' }}>{intent.primary_goal}</span></p>
              )}
              {project.type && (
                <p><span style={{ color: '#777' }}>Typ:</span>{' '}
                  <span style={{ color: '#888' }}>{project.type}</span></p>
              )}
              {site.location && (
                <p><span style={{ color: '#777' }}>Lokalita:</span>{' '}
                  <span style={{ color: '#888' }}>{site.location}</span></p>
              )}
              {(style.keywords || style.atmosphere) && (
                <p><span style={{ color: '#777' }}>Styl:</span>{' '}
                  <span style={{ color: '#888' }}>
                    {[style.keywords, style.atmosphere].filter(Boolean).join(' — ')}
                  </span></p>
              )}
              {(budget.target || budget.max) && (
                <p><span style={{ color: '#777' }}>Rozpočet:</span>{' '}
                  <span style={{ color: '#888' }}>
                    {[budget.target, budget.max].filter(Boolean).join(' / max ')}
                  </span></p>
              )}
              {!intent.primary_goal && !project.type && !site.location && (
                <p style={{ color: '#777', fontStyle: 'italic' }}>Záměr zatím nebyl specifikován</p>
              )}
            </div>
          </div>

          {/* Vizualizace */}
          <div style={sectionStyle}>
            <SectionLabel label="Vizualizace" />
            {generatedImageUrl ? (
              <img src={generatedImageUrl} alt="Vizualizace" className="w-full rounded-lg"
                style={{ border: '1px solid #1E1E1E' }} />
            ) : (
              <p style={{ ...bodyTextStyle, fontStyle: 'italic', color: '#777' }}>
                Vizualizace nebyla vygenerována
              </p>
            )}
          </div>

          {/* Půdorys */}
          <div style={sectionStyle}>
            <SectionLabel label="Schematický půdorys" />
            {floorplanSvg ? (
              <div className="overflow-auto" dangerouslySetInnerHTML={{ __html: floorplanSvg }} />
            ) : (
              <p style={{ ...bodyTextStyle, fontStyle: 'italic', color: '#777' }}>
                Půdorys nebyl vygenerován
              </p>
            )}
          </div>

          {/* Tabulka místností */}
          {spaces.length > 0 && (
            <div style={sectionStyle}>
              <SectionLabel label="Prostorový program" />
              <table className="w-full" style={{ fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#1D9E75', color: '#fff' }}>
                    <th className="text-left px-3 py-2 rounded-tl-lg" style={{ fontSize: 12 }}>Místnost</th>
                    <th className="text-right px-3 py-2 rounded-tr-lg" style={{ fontSize: 12 }}>Plocha</th>
                  </tr>
                </thead>
                <tbody>
                  {spaces.map((space, i) => {
                    const name = typeof space === 'object' && space !== null
                      ? String((space as Record<string, unknown>).name ?? '—')
                      : String(space)
                    const area = typeof space === 'object' && space !== null
                      ? (space as Record<string, unknown>).area_target ?? (space as Record<string, unknown>).area
                      : null
                    return (
                      <tr key={i} style={{ background: i % 2 === 0 ? '#161616' : '#111' }}>
                        <td className="px-3 py-2" style={{ color: '#888' }}>{name}</td>
                        <td className="px-3 py-2 text-right" style={{ color: '#777' }}>
                          {area ? `${area} m²` : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* CTA */}
          <div className="flex justify-center pt-2 pb-8">
            <button
              onClick={() => void handleDownload()}
              disabled={isDownloading}
              className="flex items-center gap-2 px-7 py-3 bg-[#1D9E75] text-white
                rounded-lg font-medium hover:bg-[#17856A] disabled:opacity-50 transition-colors duration-150"
              style={{ fontSize: 14, width: '100%', justifyContent: 'center' }}
            >
              {isDownloading
                ? <><RefreshCw size={16} className="animate-spin" />Generuji PDF…</>
                : <><Download size={16} />Stáhnout PDF</>}
            </button>
          </div>

        </div>
      </div>
    </div>
  )
}
