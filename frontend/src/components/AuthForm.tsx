import { useState } from 'react'
import { supabase } from '../supabase'

export default function AuthForm() {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setIsLoading(true)
    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      } else {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        setInfo('Zkontrolujte e-mail a potvrďte registraci.')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Neznámá chyba')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleGoogle() {
    setError(null)
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin },
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        {/* Logo */}
        <div className="flex items-center gap-2 mb-8">
          <div className="w-2.5 h-2.5 rounded-full bg-[#1D9E75]" />
          <span className="font-semibold text-gray-800">ArchBrief</span>
        </div>

        <h1 className="text-xl font-semibold text-gray-800 mb-1">
          {mode === 'login' ? 'Přihlásit se' : 'Vytvořit účet'}
        </h1>
        <p className="text-sm text-gray-400 mb-6">
          {mode === 'login'
            ? 'Pro přístup k vašim projektům'
            : 'Začněte svůj první projekt'}
        </p>

        {/* Google */}
        <button
          onClick={handleGoogle}
          className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 border border-gray-200
            rounded-xl text-sm text-gray-700 hover:bg-gray-50 transition mb-4"
        >
          <svg width="18" height="18" viewBox="0 0 18 18">
            <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/>
            <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2.04a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/>
            <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07z"/>
            <path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"/>
          </svg>
          Pokračovat přes Google
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px bg-gray-100" />
          <span className="text-xs text-gray-300">nebo</span>
          <div className="flex-1 h-px bg-gray-100" />
        </div>

        {/* Email form */}
        <form onSubmit={handleEmailSubmit} className="space-y-3">
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="E-mail"
            required
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none
              focus:border-[#1D9E75] focus:ring-1 focus:ring-[#1D9E75]/30 transition"
          />
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Heslo"
            required
            minLength={6}
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm outline-none
              focus:border-[#1D9E75] focus:ring-1 focus:ring-[#1D9E75]/30 transition"
          />

          {error && <p className="text-xs text-red-500">{error}</p>}
          {info && <p className="text-xs text-[#1D9E75]">{info}</p>}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2.5 bg-[#1D9E75] text-white rounded-xl text-sm font-medium
              hover:bg-[#178a65] disabled:opacity-50 transition"
          >
            {isLoading ? 'Načítám…' : mode === 'login' ? 'Přihlásit se' : 'Vytvořit účet'}
          </button>
        </form>

        {/* Switch mode */}
        <p className="text-xs text-center text-gray-400 mt-4">
          {mode === 'login' ? 'Nemáte účet? ' : 'Máte účet? '}
          <button
            onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(null); setInfo(null) }}
            className="text-[#1D9E75] hover:underline"
          >
            {mode === 'login' ? 'Registrovat se' : 'Přihlásit se'}
          </button>
        </p>
      </div>
    </div>
  )
}
