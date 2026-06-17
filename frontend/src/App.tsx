import { useEffect, useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { supabase } from './supabase'
import AuthForm from './components/AuthForm'
import ProjectList from './components/ProjectList'
import ChatPanel from './components/ChatPanel'
import ModelPanel from './components/ModelPanel'
import ExportPage from './components/ExportPage'
import { LogOut, ChevronLeft, Download } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000'
const LS_SESSION = 'archbrief_session_id'
const LS_PROJECT_NAME = 'archbrief_project_name'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export type IntentModel = Record<string, unknown>

type View = 'auth' | 'projects' | 'chat' | 'export'

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

  // Floorplan state
  const [floorplanSvg, setFloorplanSvg] = useState<string | null>(null)

  // Export state
  const [projectId, setProjectId] = useState<string | null>(null)

  // Auth listener
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user)
        setAuthToken(session.access_token)
        const savedSid = localStorage.getItem(LS_SESSION)
        const savedName = localStorage.getItem(LS_PROJECT_NAME) ?? 'Nový projekt'
        if (savedSid) {
          void handleOpenProject(savedSid, savedName)
        } else {
          setView('projects')
        }
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
    setFloorplanSvg(null)
    setProjectId(null)
    localStorage.removeItem(LS_SESSION)
    localStorage.removeItem(LS_PROJECT_NAME)
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
      setProjectId((data as Record<string, unknown>).project_id as string ?? null)
      setIntentModel(data.intent_model)
      setMessages([{ role: 'assistant', content: data.assistant_message }])
      setProjectName(name)
      localStorage.setItem(LS_SESSION, data.session_id)
      localStorage.setItem(LS_PROJECT_NAME, name)
      setView('chat')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Chyba při vytváření projektu')
    } finally {
      setIsLoading(false)
    }
  }

  // Otevření existujícího projektu — obnoví konverzaci ze Supabase
  async function handleOpenProject(sid: string, name?: string) {
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
      const resolvedName = name ?? 'Nový projekt'
      setSessionId(sid)
      setIntentModel(data.intent_model)
      setMessages(data.messages ?? [])
      setProjectId((data as Record<string, unknown>).project_id as string ?? null)
      setGeneratedImageUrl((data as Record<string, unknown>).generated_image_url as string ?? null)
      setImagePrompt((data as Record<string, unknown>).image_prompt as string ?? null)
      setFloorplanSvg((data as Record<string, unknown>).floorplan_svg as string ?? null)
      setProjectName(resolvedName)
      localStorage.setItem(LS_SESSION, sid)
      localStorage.setItem(LS_PROJECT_NAME, resolvedName)
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

  async function fetchFloorplan(sid: string) {
    try {
      const headers = await authHeaders()
      const res = await fetch(`${API}/api/floorplan-svg`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ session_id: sid }),
      })
      const data = await res.json() as { svg?: string; error?: string }
      if (res.ok && !data.error && data.svg) setFloorplanSvg(data.svg)
    } catch { /* non-fatal */ }
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
      if (sessionId) void fetchFloorplan(sessionId)
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
        onOpenProject={(sid, name) => void handleOpenProject(sid, name)}
        onNewProject={(name) => void handleNewProject(name)}
      />
    )
  }

  if (view === 'export') {
    return (
      <ExportPage
        sessionId={sessionId!}
        projectName={projectName}
        intentModel={intentModel}
        generatedImageUrl={generatedImageUrl}
        floorplanSvg={floorplanSvg}
        authToken={authToken}
        onBack={() => setView('chat')}
      />
    )
  }

  // view === 'chat'
  return (
    <div className="h-screen flex flex-col bg-[#0A0A0A]">
      {/* Header */}
      <header
        className="bg-[#0A0A0A] px-5 flex items-center gap-3 shrink-0"
        style={{ height: 52, borderBottom: '1px solid #1E1E1E' }}
      >
        <button
          onClick={() => setView('projects')}
          className="flex items-center gap-1 text-xs transition-colors duration-150"
          style={{ color: '#666' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#999')}
          onMouseLeave={e => (e.currentTarget.style.color = '#666')}
        >
          <ChevronLeft size={15} />
          Projekty
        </button>
        <div className="w-px h-4" style={{ background: '#1E1E1E' }} />
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#1D9E75]" />
          <span className="font-medium text-[#E8E8E8]" style={{ fontSize: 13 }}>{projectName}</span>
        </div>
        <button
          onClick={() => setView('export')}
          className="flex items-center gap-1.5 transition-colors duration-150 rounded-md px-2.5 py-1.5"
          style={{ fontSize: 12, color: '#888', border: '1px solid #2A2A2A' }}
          onMouseEnter={e => {
            ;(e.currentTarget as HTMLButtonElement).style.color = '#1D9E75'
            ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#1D9E75'
          }}
          onMouseLeave={e => {
            ;(e.currentTarget as HTMLButtonElement).style.color = '#888'
            ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#2A2A2A'
          }}
        >
          <Download size={12} />
          Exportovat
        </button>
        <button
          onClick={() => supabase.auth.signOut()}
          className="ml-auto flex items-center gap-1.5 text-xs transition-colors duration-150"
          style={{ color: '#666' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#999')}
          onMouseLeave={e => (e.currentTarget.style.color = '#666')}
        >
          <LogOut size={13} />
          Odhlásit
        </button>
      </header>

      {/* Panels */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-[60%]" style={{ borderRight: '1px solid #141414' }}>
          <ChatPanel messages={messages} onSend={sendMessage} isLoading={isLoading} />
        </div>
        <div className="w-[40%]">
          <ModelPanel
            model={intentModel}
            generatedImageUrl={generatedImageUrl}
            imagePrompt={imagePrompt}
            isGenerating={isGenerating}
            onGenerate={generateImage}
            floorplanSvg={floorplanSvg}
          />
        </div>
      </div>
    </div>
  )
}
