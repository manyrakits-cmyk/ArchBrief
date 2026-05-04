import { useEffect, useState } from 'react'
import ChatPanel from './components/ChatPanel'
import ModelPanel from './components/ModelPanel'

const API = 'http://localhost:5000'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export type IntentModel = Record<string, unknown>

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [intentModel, setIntentModel] = useState<IntentModel>({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void initSession()
  }, [])

  async function initSession() {
    setError(null)
    setIsLoading(true)
    try {
      const res = await fetch(`${API}/api/session/new`, { method: 'POST' })
      if (!res.ok) throw new Error('Server vrátil chybu')
      const data = await res.json() as { session_id: string; assistant_message: string; intent_model: IntentModel }
      setSessionId(data.session_id)
      setIntentModel(data.intent_model)
      setMessages([{ role: 'assistant', content: data.assistant_message }])
    } catch {
      setError('Nelze se připojit k backendu. Spusťte Flask server na portu 5000.')
    } finally {
      setIsLoading(false)
    }
  }

  async function sendMessage(text: string) {
    if (!sessionId || !text.trim() || isLoading) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
      if (!res.ok) throw new Error('Chyba serveru')
      const data = await res.json() as { assistant_message: string; intent_model: IntentModel }
      setMessages(prev => [...prev, { role: 'assistant', content: data.assistant_message }])
      setIntentModel(data.intent_model)
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '⚠️ Chyba komunikace se serverem.' },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8 bg-white rounded-2xl shadow-sm border max-w-sm">
          <p className="text-red-500 font-medium mb-3">{error}</p>
          <button
            onClick={() => void initSession()}
            className="text-sm text-[#1D9E75] hover:underline"
          >
            Zkusit znovu
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center gap-2.5 shrink-0">
        <div className="w-2 h-2 rounded-full bg-[#1D9E75]" />
        <h1 className="font-semibold text-gray-800 text-sm tracking-wide">ArchBrief</h1>
        <span className="text-xs text-gray-400 ml-auto">Konverzační asistent architekta</span>
      </header>

      {/* Panels */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-[60%] border-r border-gray-200">
          <ChatPanel messages={messages} onSend={sendMessage} isLoading={isLoading} />
        </div>
        <div className="w-[40%]">
          <ModelPanel model={intentModel} />
        </div>
      </div>
    </div>
  )
}
