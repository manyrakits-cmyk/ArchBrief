import { useEffect, useState } from 'react'
import { Plus, LogOut, FolderOpen } from 'lucide-react'
import type { User } from '@supabase/supabase-js'
import { supabase } from '../supabase'

interface Project {
  id: string
  name: string
  type: string | null
  updated_at: string
  session_id: string | null
}

interface Props {
  user: User
  authToken: string
  onOpenProject: (sessionId: string) => void
  onNewProject: () => void
}

const API = 'http://localhost:5000'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('cs-CZ', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

export default function ProjectList({ user, authToken, onOpenProject, onNewProject }: Props) {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void loadProjects()
  }, [])

  async function loadProjects() {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/projects`, {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (!res.ok) throw new Error('Nepodařilo se načíst projekty')
      const data = await res.json() as Project[]
      setProjects(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chyba')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleLogout() {
    await supabase.auth.signOut()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center gap-2.5">
        <div className="w-2 h-2 rounded-full bg-[#1D9E75]" />
        <span className="font-semibold text-gray-800 text-sm">ArchBrief</span>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-400">{user.email}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 transition"
          >
            <LogOut size={14} />
            Odhlásit
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">Moje projekty</h1>
            <p className="text-sm text-gray-400 mt-1">Vaše architektonické záměry</p>
          </div>
          <button
            onClick={onNewProject}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#1D9E75] text-white
              rounded-xl text-sm font-medium hover:bg-[#178a65] transition"
          >
            <Plus size={16} />
            Nový projekt
          </button>
        </div>

        {isLoading && (
          <div className="text-center py-16 text-gray-400 text-sm">Načítám projekty…</div>
        )}

        {error && (
          <div className="text-center py-16">
            <p className="text-red-500 text-sm mb-2">{error}</p>
            <button onClick={loadProjects} className="text-sm text-[#1D9E75] hover:underline">
              Zkusit znovu
            </button>
          </div>
        )}

        {!isLoading && !error && projects.length === 0 && (
          <div className="text-center py-16">
            <FolderOpen size={40} className="mx-auto text-gray-200 mb-4" />
            <p className="text-gray-400 text-sm mb-4">Zatím žádné projekty</p>
            <button
              onClick={onNewProject}
              className="px-4 py-2 bg-[#1D9E75] text-white rounded-xl text-sm hover:bg-[#178a65] transition"
            >
              Začít první projekt
            </button>
          </div>
        )}

        {!isLoading && !error && projects.length > 0 && (
          <div className="grid gap-3">
            {projects.map(project => (
              <button
                key={project.id}
                onClick={() => project.session_id && onOpenProject(project.session_id)}
                disabled={!project.session_id}
                className="w-full text-left bg-white border border-gray-100 rounded-2xl p-5
                  hover:border-[#1D9E75]/40 hover:shadow-sm transition group"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-gray-800 group-hover:text-[#1D9E75] transition">
                      {project.name}
                    </h3>
                    {project.type && (
                      <span className="inline-block mt-1 text-xs text-gray-400 bg-gray-50
                        px-2 py-0.5 rounded-full">
                        {project.type}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-gray-300 shrink-0 ml-4">
                    {formatDate(project.updated_at)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
