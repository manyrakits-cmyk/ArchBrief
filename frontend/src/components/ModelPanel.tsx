import { useRef, useState } from 'react'
import { Image, Upload, RefreshCw } from 'lucide-react'
import { supabase } from '../supabase'
import type { IntentModel } from '../App'

interface Props {
  model: IntentModel
  generatedImageUrl: string | null
  imagePrompt: string | null
  isGenerating: boolean
  onGenerate: (referenceUrl?: string) => void
}

// ── JSON tree ─────────────────────────────────────────────────────────────────

function JsonNode({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) {
    return <span className="text-gray-300 italic">null</span>
  }
  if (typeof value === 'boolean') {
    return <span className="text-purple-400">{value.toString()}</span>
  }
  if (typeof value === 'number') {
    return <span className="text-blue-400">{value}</span>
  }
  if (typeof value === 'string') {
    if (value === '') return <span className="text-gray-300 italic">""</span>
    return <span className="text-emerald-700">"{value}"</span>
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-300">[ ]</span>
    return (
      <div className="ml-3 pl-2 border-l border-gray-100 space-y-0.5 mt-0.5">
        {value.map((item, i) => (
          <div key={i} className="flex gap-1.5 items-start">
            <span className="text-gray-300 select-none shrink-0 mt-0.5">•</span>
            <div className="min-w-0"><JsonNode value={item} depth={depth + 1} /></div>
          </div>
        ))}
      </div>
    )
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return <span className="text-gray-300">{ }</span>
    return (
      <div className={`space-y-0.5 ${depth > 0 ? 'ml-3 pl-2 border-l border-gray-100 mt-0.5' : ''}`}>
        {entries.map(([key, val]) => (
          <div key={key} className="flex flex-wrap gap-x-1.5 items-start">
            <span className="text-cyan-700 font-semibold shrink-0">{key}</span>
            <span className="text-gray-300 shrink-0">:</span>
            <div className="min-w-0"><JsonNode value={val} depth={depth + 1} /></div>
          </div>
        ))}
      </div>
    )
  }
  return <span className="text-gray-700">{String(value)}</span>
}

// ── ModelPanel ────────────────────────────────────────────────────────────────

export default function ModelPanel({ model, generatedImageUrl, imagePrompt, isGenerating, onGenerate }: Props) {
  const [referenceFile, setReferenceFile] = useState<File | null>(null)
  const [referencePreview, setReferencePreview] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center gap-2 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
        <h2 className="text-sm font-semibold text-gray-700">Model záměru</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">

        {/* Vygenerovaný obrázek */}
        {generatedImageUrl && (
          <div className="bg-white rounded-xl border border-gray-100 overflow-hidden shadow-sm">
            <img src={generatedImageUrl} alt="Vizualizace" className="w-full" />
            {imagePrompt && (
              <p className="text-xs text-gray-400 p-3 leading-relaxed line-clamp-3">{imagePrompt}</p>
            )}
          </div>
        )}

        {/* Sekce generování */}
        <div className="bg-white rounded-xl border border-gray-100 p-3 shadow-sm space-y-2">
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
              className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#1D9E75] text-white
                rounded-xl text-sm font-medium hover:bg-[#178a65] disabled:opacity-50 transition"
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
              className="px-3 py-2.5 border border-gray-200 rounded-xl text-gray-500
                hover:border-gray-300 hover:text-gray-700 disabled:opacity-50 transition"
              title="Nahrát referenční fotku"
            >
              <Upload size={14} />
            </button>
          </div>

          {!referencePreview && (
            <p className="text-xs text-gray-400 text-center">
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

        {/* JSON model */}
        {isEmpty ? (
          <p className="text-xs text-gray-400 text-center mt-4">Zahajte rozhovor…</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-xs font-mono leading-5">
            <JsonNode value={model} />
          </div>
        )}
      </div>
    </div>
  )
}
