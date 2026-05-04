import type { IntentModel } from '../App'

interface Props {
  model: IntentModel
}

function JsonNode({ value, depth = 0 }: { value: unknown; depth?: number }) {
  // null / undefined
  if (value === null || value === undefined) {
    return <span className="text-gray-300 italic">null</span>
  }
  // boolean
  if (typeof value === 'boolean') {
    return <span className="text-purple-400">{value.toString()}</span>
  }
  // number
  if (typeof value === 'number') {
    return <span className="text-blue-400">{value}</span>
  }
  // string
  if (typeof value === 'string') {
    if (value === '') return <span className="text-gray-300 italic">""</span>
    return <span className="text-emerald-700">"{value}"</span>
  }
  // array
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-300">[ ]</span>
    return (
      <div className="ml-3 pl-2 border-l border-gray-100 space-y-0.5 mt-0.5">
        {value.map((item, i) => (
          <div key={i} className="flex gap-1.5 items-start">
            <span className="text-gray-300 select-none shrink-0 mt-0.5">•</span>
            <div className="min-w-0">
              <JsonNode value={item} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    )
  }
  // object
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if (entries.length === 0) return <span className="text-gray-300">{ }</span>
    return (
      <div className={`space-y-0.5 ${depth > 0 ? 'ml-3 pl-2 border-l border-gray-100 mt-0.5' : ''}`}>
        {entries.map(([key, val]) => (
          <div key={key} className="flex flex-wrap gap-x-1.5 items-start">
            <span className="text-cyan-700 font-semibold shrink-0">{key}</span>
            <span className="text-gray-300 shrink-0">:</span>
            <div className="min-w-0">
              <JsonNode value={val} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <span className="text-gray-700">{String(value)}</span>
}

export default function ModelPanel({ model }: Props) {
  const isEmpty = Object.keys(model).length === 0

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center gap-2 shrink-0">
        <div className="w-1.5 h-1.5 rounded-full bg-[#1D9E75]" />
        <h2 className="text-sm font-semibold text-gray-700">Model záměru</h2>
      </div>

      {/* JSON tree */}
      <div className="flex-1 overflow-y-auto p-4">
        {isEmpty ? (
          <p className="text-xs text-gray-400 text-center mt-8">Zahajte rozhovor…</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm text-xs font-mono leading-5">
            <JsonNode value={model} />
          </div>
        )}
      </div>
    </div>
  )
}
