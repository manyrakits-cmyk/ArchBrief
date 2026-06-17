import { useEffect, useState } from 'react'
import { Plus, LogOut, FolderOpen, Pencil } from 'lucide-react'
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
  onOpenProject: (sessionId: string, name: string) => void
  onNewProject: (name: string) => void
}

const API = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('cs-CZ', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

export default function ProjectList({ user, authToken, onOpenProject, onNewProject }: Props) {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isNaming, setIsNaming] = useState(false)
  const [newName, setNewName] = useState('Nový projekt')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')

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

  function startNaming() {
    setNewName('Nový projekt')
    setIsNaming(true)
  }

  function confirmName() {
    const name = newName.trim() || 'Nový projekt'
    setIsNaming(false)
    onNewProject(name)
  }

  function handleNameKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') confirmName()
    if (e.key === 'Escape') setIsNaming(false)
  }

  function startEditing(project: Project, e: React.MouseEvent) {
    e.stopPropagation()
    setEditingId(project.id)
    setEditingName(project.name)
  }

  async function saveEditing(projectId: string) {
    const name = editingName.trim() || 'Nový projekt'
    setEditingId(null)
    setProjects(prev => prev.map(p => p.id === projectId ? { ...p, name } : p))
    try {
      await fetch(`${API}/api/projects/${projectId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
    } catch {
      void loadProjects()
    }
  }

  function handleEditKeyDown(e: React.KeyboardEvent<HTMLInputElement>, projectId: string) {
    if (e.key === 'Enter') void saveEditing(projectId)
    if (e.key === 'Escape') setEditingId(null)
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      {/* Navbar */}
      <header className="bg-[#0A0A0A] border-b border-[#1E1E1E] px-6 flex items-center gap-2.5" style={{ height: 52 }}>
        <div className="w-2 h-2 rounded-full bg-[#1D9E75]" />
        <span className="font-semibold text-white text-sm">ArchBrief</span>
        <div className="ml-auto flex items-center gap-4">
          <span className="text-xs text-[#666]">{user.email}</span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-[#666] hover:text-[#888] transition-colors duration-150"
          >
            <LogOut size={13} />
            Odhlásit
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-[760px] mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-[22px] font-semibold text-[#E8E8E8]">Moje projekty</h1>
            <p className="text-[13px] font-medium text-[#666] mt-1">Vaše architektonické záměry</p>
          </div>
          {isNaming ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                type="text"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onKeyDown={handleNameKeyDown}
                className="px-3 py-2 rounded-lg bg-[#111] border border-[#1D9E75] text-sm text-[#E8E8E8]
                  placeholder-[#333] outline-none w-48"
              />
              <button
                onClick={confirmName}
                className="px-3 py-2 bg-[#1D9E75] text-white rounded-lg text-sm font-medium
                  hover:bg-[#17856A] transition-colors duration-150"
              >
                Vytvořit
              </button>
              <button
                onClick={() => setIsNaming(false)}
                className="px-3 py-2 text-sm text-[#666] hover:text-[#888] transition-colors duration-150"
              >
                Zrušit
              </button>
            </div>
          ) : (
            <button
              onClick={startNaming}
              className="flex items-center gap-2 px-4 py-[9px] bg-[#1D9E75] text-white
                rounded-lg text-[13px] font-medium hover:bg-[#17856A] transition-colors duration-150"
            >
              <Plus size={15} />
              Nový projekt
            </button>
          )}
        </div>

        {isLoading && (
          <div className="text-center py-16 text-[#666] text-sm">Načítám projekty…</div>
        )}

        {error && (
          <div className="text-center py-16">
            <p className="text-red-400 text-sm mb-2">{error}</p>
            <button onClick={loadProjects} className="text-sm text-[#1D9E75] hover:underline">
              Zkusit znovu
            </button>
          </div>
        )}

        {!isLoading && !error && projects.length === 0 && (
          <div className="text-center py-16">
            <FolderOpen size={40} className="mx-auto text-[#222] mb-4" />
            <p className="text-[#666] text-sm mb-4">Zatím žádné projekty</p>
            <button
              onClick={startNaming}
              className="px-4 py-2 bg-[#1D9E75] text-white rounded-lg text-sm
                hover:bg-[#17856A] transition-colors duration-150"
            >
              Začít první projekt
            </button>
          </div>
        )}

        {!isLoading && !error && projects.length > 0 && (
          <div className="grid gap-3">
            {projects.map(project => (
              <div
                key={project.id}
                onClick={() => editingId !== project.id && project.session_id && onOpenProject(project.session_id, project.name)}
                className="w-full text-left bg-[#111] border border-[#1E1E1E] rounded-xl
                  px-5 py-4 hover:border-[#2A2A2A] hover:bg-[#141414]
                  transition-all duration-150 group cursor-pointer"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    {editingId === project.id ? (
                      <input
                        autoFocus
                        type="text"
                        value={editingName}
                        onChange={e => setEditingName(e.target.value)}
                        onKeyDown={e => handleEditKeyDown(e, project.id)}
                        onBlur={() => void saveEditing(project.id)}
                        onClick={e => e.stopPropagation()}
                        className="w-full font-medium text-[#E8E8E8] border-b border-[#1D9E75]
                          outline-none bg-transparent pb-0.5"
                      />
                    ) : (
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-[14px] text-[#E8E8E8] group-hover:text-[#1D9E75]
                          transition-colors duration-150 truncate">
                          {project.name}
                        </h3>
                        <button
                          onClick={e => startEditing(project, e)}
                          className="opacity-0 group-hover:opacity-100 text-[#555]
                            hover:text-[#1D9E75] transition-all duration-150 shrink-0"
                        >
                          <Pencil size={12} />
                        </button>
                      </div>
                    )}
                    {project.type && (
                      <span className="inline-block mt-1 text-xs text-[#666] bg-[#161616]
                        px-2 py-0.5 rounded-full">
                        {project.type}
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-medium text-[#555] shrink-0">
                    {formatDate(project.updated_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
