import { useRef, useState } from 'react'
import { Image, Upload, RefreshCw } from 'lucide-react'
import { supabase } from '../supabase'
import type { IntentModel } from '../App'
import FloorplanPanel from './FloorplanPanel'

interface Props {
  model: IntentModel
  generatedImageUrl: string | null
  imagePrompt: string | null
  isGenerating: boolean
  onGenerate: (referenceUrl?: string) => void
  floorplanSvg: string | null
}

// ── JSON tree ─────────────────────────────────────────────────────────────────

function JsonNode({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) {
    return <span style={{ color: '#555' }} className="italic">null</span>
  }
  if (typeof value === 'boolean') {
    return <span style={{ color: '#888' }}>{value.toString()}</span>
  }
  if (typeof value === 'number') {
    return <span style={{ color: '#A0C8B0' }}>{value}</span>
  }
  if (typeof value === 'string') {
    if (value === '') return <span style={{ color: '#555' }} className="italic">{`""`}</span>
    return <span style={{ color: '#888' }}>{`"${value}"`}</span>
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span style={{ color: '#666' }}>{'[ ]'}</span>
    return (
      <div className="ml-3 pl-2 space-y-0.5 mt-0.5" style={{ borderLeft: '1px solid #1E1E1E' }}>
        {value.map((item, i) => (
          <div key={i} className="flex gap-1.5 items-start">
            <span style={{ color: '#666' }} className="select-none shrink-0 mt-0.5">•</span>
            <div className="min-w-0"><JsonNode value={item} depth={depth + 1} /></div>
          </div>
        ))}
      </div>
    )
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return <span style={{ color: '#666' }}>{'{ }'}</span>
    return (
      <div
        className={`space-y-0.5 ${depth > 0 ? 'ml-3 pl-2 mt-0.5' : ''}`}
        style={depth > 0 ? { borderLeft: '1px solid #1E1E1E' } : undefined}
      >
        {entries.map(([key, val]) => (
          <div key={key} className="flex flex-wrap gap-x-1.5 items-start">
            <span style={{ color: '#1D9E75' }} className="font-semibold shrink-0">{key}</span>
            <span style={{ color: '#666' }} className="shrink-0">:</span>
            <div className="min-w-0"><JsonNode value={val} depth={depth + 1} /></div>
          </div>
        ))}
      </div>
    )
  }
  return <span style={{ color: '#666' }}>{String(value)}</span>
}

// ── ModelPanel ────────────────────────────────────────────────────────────────

export default function ModelPanel({ model, generatedImageUrl, imagePrompt, isGenerating, onGenerate, floorplanSvg }: Props) {
  const [referenceFile, setReferenceFile] = useState<File | null>(null)
  const [referencePreview, setReferencePreview] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [activeTab, setActiveTab] = useState<'model' | 'floorplan'>('model')

  const isEmpty = Object.keys(model).length === 0
  const busy = isGenerating || isUploading

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setReferenceFile(file)
    setReferencePreview(URL.createObjectURL(file))
    e.target.value = ''
  }

  async function handleGenerate() {
    let referenceUrl: string | undefined
    if (referenceFile) {
      setIsUploading(true)
      try {
        const path = `${Date.now()}-${referenceFile.name}`
        const { data, error } = await supabase.storage.from('reference-images').upload(path, referenceFile)
        if (data && !error) {
          const { data: { publicUrl } } = supabase.storage.from('reference-images').getPublicUrl(data.path)
          referenceUrl = publicUrl
        }
      } finally {
        setIsUploading(false)
      }
    }
    onGenerate(referenceUrl)
  }

  return (
    <div className="h-full flex flex-col bg-[#0A0A0A]">
      {/* Header */}
      <div
        className="px-4 flex items-center gap-2 shrink-0"
        style={{ height: 44, borderBottom: '1px solid #141414' }}
      >
        <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
        <h2 className="text-sm font-semibold text-[#E8E8E8]">Model záměru</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Vygenerovaný obrázek */}
        {generatedImageUrl && (
          <div
            className="rounded-xl overflow-hidden"
            style={{ border: '1px solid #1E1E1E', background: '#111' }}
          >
            <img src={generatedImageUrl} alt="Vizualizace" className="w-full" />
            {imagePrompt && (
              <p className="p-3 leading-relaxed line-clamp-3" style={{ fontSize: 11, color: '#555' }}>
                {imagePrompt}
              </p>
            )}
          </div>
        )}

        {/* Sekce generování */}
        <div
          className="rounded-xl p-3 space-y-2"
          style={{ background: '#111', border: '1px solid #1E1E1E' }}
        >
          {/* Náhled referenčního obrázku */}
          {referencePreview && (
            <div className="relative">
              <img src={referencePreview} alt="Inspirace" className="w-full h-28 object-cover rounded-lg" />
              <button
                onClick={() => { setReferenceFile(null); setReferencePreview(null) }}
                className="absolute top-1.5 right-1.5 bg-black/50 text-white rounded-full
                  w-5 h-5 flex items-center justify-center text-xs hover:bg-black/70 transition"
              >
                ×
              </button>
              <span className="absolute bottom-1.5 left-2 text-xs text-white/80 bg-black/40 px-1.5 py-0.5 rounded">
                Inspirace
              </span>
            </div>
          )}

          {/* Tlačítka */}
          <div className="flex gap-2">
            <button
              onClick={() => void handleGenerate()}
              disabled={busy}
              className="flex-1 flex items-center justify-center gap-2 py-[10px] bg-[#1D9E75] text-white
                rounded-lg text-[13px] font-medium hover:bg-[#17856A] disabled:opacity-50 transition-colors duration-150"
            >
              {busy ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  {isUploading ? 'Nahrávám…' : 'Generuji… (10–20 s)'}
                </>
              ) : (
                <>
                  <Image size={14} />
                  {generatedImageUrl ? 'Regenerovat' : 'Vygenerovat vizualizaci'}
                </>
              )}
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={busy}
              className="px-3 py-[10px] rounded-lg disabled:opacity-50 transition-colors duration-150"
              style={{ border: '1px solid #1E1E1E', color: '#666' }}
              title="Nahrát referenční fotku"
              onMouseEnter={e => {
                ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#444'
                ;(e.currentTarget as HTMLButtonElement).style.color = '#666'
              }}
              onMouseLeave={e => {
                ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#1E1E1E'
                ;(e.currentTarget as HTMLButtonElement).style.color = '#444'
              }}
            >
              <Upload size={14} />
            </button>
          </div>

          {!referencePreview && (
            <p className="text-xs text-center" style={{ color: '#555' }}>
              Pro image-to-image nahrajte inspiraci →{' '}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-[#1D9E75] hover:underline"
              >
                vybrat fotku
              </button>
            </p>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

        {/* Záložky */}
        <div className="flex shrink-0" style={{ borderBottom: '1px solid #141414' }}>
          <button
            onClick={() => setActiveTab('model')}
            className="flex-1 py-2 text-xs font-medium transition-colors duration-150"
            style={{
              color: activeTab === 'model' ? '#E8E8E8' : '#444',
              borderBottom: activeTab === 'model' ? '2px solid #1D9E75' : '2px solid transparent',
              background: activeTab === 'model' ? '#0D0D0D' : 'transparent',
            }}
          >
            Model záměru
          </button>
          <button
            onClick={() => setActiveTab('floorplan')}
            className="flex-1 py-2 text-xs font-medium transition-colors duration-150"
            style={{
              color: activeTab === 'floorplan' ? '#E8E8E8' : '#444',
              borderBottom: activeTab === 'floorplan' ? '2px solid #1D9E75' : '2px solid transparent',
              background: activeTab === 'floorplan' ? '#0D0D0D' : 'transparent',
            }}
          >
            Půdorys
          </button>
        </div>

        {/* Obsah záložky */}
        {activeTab === 'model' ? (
          isEmpty ? (
            <p className="text-xs text-center mt-4" style={{ color: '#555' }}>Zahajte rozhovor…</p>
          ) : (
            <div
              className="rounded-xl p-4 text-xs font-mono"
              style={{ background: '#111', border: '1px solid #1E1E1E', lineHeight: 1.75 }}
            >
              <JsonNode value={model} />
            </div>
          )
        ) : (
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: '#111', border: '1px solid #1E1E1E' }}
          >
            <FloorplanPanel svg={floorplanSvg} />
          </div>
        )}
      </div>
    </div>
  )
}
