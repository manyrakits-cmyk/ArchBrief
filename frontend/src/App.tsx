import { useEffect, useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { supabase } from './supabase'
import AuthForm from './components/AuthForm'
import ProjectList from './components/ProjectList'
import ChatPanel from './components/ChatPanel'
import ModelPanel from './components/ModelPanel'
import { LogOut, ChevronLeft } from 'lucide-react'

const API = 'http://localhost:5000'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export type IntentModel = Record<string, unknown>

type View = 'auth' | 'projects' | 'chat'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [authToken, setAuthToken] = useState<string>('')
  const [view, setView] = useState<View>('auth')

  // Chat state
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [intentModel, setIntentModel] = useState<IntentModel>({})
  const [isLoading, setIsLoading] = useState(false)
  const [projectName, setProjectName] = useState<string>('Nový projekt')

  // Image state
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null)
  const [imagePrompt, setImagePrompt] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  // Auth listener
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user)
        setAuthToken(session.access_token)
        setView('projects')
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user)
        setAuthToken(session.access_token)
        setView('projects')
      } else {
        setUser(null)
        setAuthToken('')
        setView('auth')
        resetChat()
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  function resetChat() {
    setSessionId(null)
    setMessages([])
    setIntentModel({})
    setProjectName('Nový projekt')
    setGeneratedImageUrl(null)
    setImagePrompt(null)
  }

  async function authHeaders() {
    // Refresh token pokud vyprší
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token ?? authToken
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  }

  // Nový projekt — zavolá backend, dostane první zprávu agenta
  async function handleNewProject(name = 'Nový projekt') {
    setIsLoading(true)
    resetChat()
    try {
      const headers = await authHeaders()
      const res = await fetch(`${API}/api/session/new`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ project_name: name }),
      })
      const data = await res.json() as {
        session_id: string
        assistant_message: string
        intent_model: IntentModel
        error?: string
      }
      if (!res.ok || data.error) throw new Error(data.error ?? `HTTP ${res.status}`)
      setSessionId(data.session_id)
      setIntentModel(data.intent_model)
      setMessages([{ role: 'assistant', content: data.assistant_message }])
      setProjectName(name)
      setView('chat')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Chyba při vytváření projektu')
    } finally {
      setIsLoading(false)
    }
  }

  // Otevření existujícího projektu — obnoví konverzaci ze Supabase
  async function handleOpenProject(sid: string) {
    setIsLoading(true)
    resetChat()
    try {
      const headers = await authHeaders()
      const res = await fetch(`${API}/api/session/${sid}`, { headers })
      const data = await res.json() as {
        intent_model: IntentModel
        messages: Message[]
        error?: string
      }
      if (!res.ok || data.error) throw new Error(data.error ?? `HTTP ${res.status}`)
      setSessionId(sid)
      setIntentModel(data.intent_model)
      setMessages(data.messages ?? [])
      setGeneratedImageUrl((data as Record<string, unknown>).generated_image_url as string ?? null)
      setImagePrompt((data as Record<string, unknown>).image_prompt as string ?? null)
      setView('chat')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Chyba při načítání projektu')
    } finally {
      setIsLoading(false)
    }
  }

  async function generateImage(referenceUrl?: string) {
    if (!sessionId || isGenerating) return
    setIsGenerating(true)
    try {
      const headers = await authHeaders()
      const res = await fetch(`${API}/api/generate-image`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ session_id: sessionId, reference_image_url: referenceUrl ?? null }),
      })
      const data = await res.json() as { image_url?: string; prompt_used?: string; error?: string }
      if (!res.ok || data.error) throw new Error(data.error ?? `HTTP ${res.status}`)
      setGeneratedImageUrl(data.image_url ?? null)
      setImagePrompt(data.prompt_used ?? null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Chyba při generování obrázku')
    } finally {
      setIsGenerating(false)
    }
  }

  // Odeslání zprávy v chatu
  async function sendMessage(text: string) {
    if (!sessionId || !text.trim() || isLoading) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setIsLoading(true)

    try {
      const headers = await authHeaders()
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
      const data = await res.json() as {
        assistant_message?: string
        intent_model?: IntentModel
        error?: string
      }
      if (!res.ok || data.error) throw new Error(data.error ?? `HTTP ${res.status}`)
      setMessages(prev => [...prev, { role: 'assistant', content: data.assistant_message ?? '' }])
      setIntentModel(data.intent_model ?? {})
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Neznámá chyba'
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Chyba: ${msg}` }])
    } finally {
      setIsLoading(false)
    }
  }

  // ── Views ─────────────────────────────────────────────────────────────────

  if (view === 'auth') {
    return <AuthForm />
  }

  if (view === 'projects') {
    return (
      <ProjectList
        user={user!}
        authToken={authToken}
        onOpenProject={handleOpenProject}
        onNewProject={(name) => void handleNewProject(name)}
      />
    )
  }

  // view === 'chat'
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3 flex items-center gap-3 shrink-0">
        <button
          onClick={() => setView('projects')}
          className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-700 transition"
        >
          <ChevronLeft size={16} />
          Projekty
        </button>
        <div className="w-px h-4 bg-gray-200" />
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#1D9E75]" />
          <span className="font-semibold text-gray-800 text-sm">{projectName}</span>
        </div>
        <button
          onClick={() => supabase.auth.signOut()}
          className="ml-auto flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition"
        >
          <LogOut size={13} />
          Odhlásit
        </button>
      </header>

      {/* Panels */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-[60%] border-r border-gray-200">
          <ChatPanel messages={messages} onSend={sendMessage} isLoading={isLoading} />
        </div>
        <div className="w-[40%]">
          <ModelPanel
            model={intentModel}
            generatedImageUrl={generatedImageUrl}
            imagePrompt={imagePrompt}
            isGenerating={isGenerating}
            onGenerate={generateImage}
          />
        </div>
      </div>
    </div>
  )
}
