import { useState } from 'react'
import { ChevronLeft, Download, RefreshCw } from 'lucide-react'
import type { IntentModel } from '../App'

const API = 'http://localhost:5000'

interface Props {
  sessionId: string
  projectName: string
  intentModel: IntentModel
  generatedImageUrl: string | null
  floorplanSvg: string | null
  authToken: string
  onBack: () => void
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

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center gap-3 shrink-0">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-700 transition"
        >
          <ChevronLeft size={16} />
          Zpět do projektu
        </button>
        <div className="flex-1" />
        <button
          onClick={() => void handleDownload()}
          disabled={isDownloading}
          className="flex items-center gap-2 px-4 py-2 bg-[#1D9E75] text-white
            rounded-xl text-sm font-medium hover:bg-[#178a65] disabled:opacity-50 transition"
        >
          {isDownloading
            ? <><RefreshCw size={14} className="animate-spin" />Generuji PDF…</>
            : <><Download size={14} />Stáhnout PDF</>}
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">

          {/* Titulek stránky */}
          <div className="flex items-center justify-between mb-2">
            <div>
              <h1 className="text-xl font-bold text-gray-800">Váš ArchBrief je připraven</h1>
              <p className="text-sm text-gray-400 mt-0.5">Náhled obsahu dokumentu</p>
            </div>
            <div className="text-2xl font-bold text-[#1D9E75]">ArchBrief</div>
          </div>

          {/* Titulní informace */}
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Titulní strana</span>
            </div>
            <p className="text-2xl font-bold text-[#1D9E75]">ArchBrief</p>
            <p className="text-lg text-gray-700 mt-0.5">{projectName}</p>
            <p className="text-xs text-gray-400 mt-2">Připraveno pro předání architektovi · {today}</p>
          </div>

          {/* Shrnutí záměru */}
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Shrnutí záměru</span>
            </div>
            <div className="space-y-1.5 text-sm">
              {intent.primary_goal && (
                <p><span className="text-gray-500">Primární cíl:</span>{' '}
                  <span className="text-gray-800">{String(intent.primary_goal)}</span></p>
              )}
              {project.type && (
                <p><span className="text-gray-500">Typ:</span>{' '}
                  <span className="text-gray-800">{String(project.type)}</span></p>
              )}
              {site.location && (
                <p><span className="text-gray-500">Lokalita:</span>{' '}
                  <span className="text-gray-800">{String(site.location)}</span></p>
              )}
              {(style.keywords || style.atmosphere) && (
                <p><span className="text-gray-500">Styl:</span>{' '}
                  <span className="text-gray-800">
                    {[style.keywords, style.atmosphere].filter(Boolean).map(String).join(' — ')}
                  </span></p>
              )}
              {(budget.target || budget.max) && (
                <p><span className="text-gray-500">Rozpočet:</span>{' '}
                  <span className="text-gray-800">
                    {[budget.target, budget.max].filter(Boolean).map(String).join(' / max ')}
                  </span></p>
              )}
            </div>
          </div>

          {/* AI vizualizace */}
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Vizualizace</span>
            </div>
            {generatedImageUrl ? (
              <img src={generatedImageUrl} alt="Vizualizace" className="w-full rounded-lg" />
            ) : (
              <p className="text-xs text-gray-400 italic">Vizualizace nebyla vygenerována</p>
            )}
          </div>

          {/* Půdorys */}
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Schematický půdorys</span>
            </div>
            {floorplanSvg ? (
              <div className="overflow-auto" dangerouslySetInnerHTML={{ __html: floorplanSvg }} />
            ) : (
              <p className="text-xs text-gray-400 italic">Půdorys nebyl vygenerován</p>
            )}
          </div>

          {/* Tabulka místností */}
          {spaces.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Prostorový program</span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#1D9E75] text-white text-xs">
                    <th className="text-left px-3 py-2 rounded-tl-lg">Místnost</th>
                    <th className="text-right px-3 py-2 rounded-tr-lg">Plocha</th>
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
                      <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-[#D4E8D4]/30'}>
                        <td className="px-3 py-2 text-gray-700">{name}</td>
                        <td className="px-3 py-2 text-gray-500 text-right">
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
          <div className="flex justify-center pt-2 pb-6">
            <button
              onClick={() => void handleDownload()}
              disabled={isDownloading}
              className="flex items-center gap-2 px-6 py-3 bg-[#1D9E75] text-white
                rounded-xl text-base font-medium hover:bg-[#178a65] disabled:opacity-50 transition shadow-sm"
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
