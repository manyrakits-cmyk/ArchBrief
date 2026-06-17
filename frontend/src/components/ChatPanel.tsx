import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import type { Message } from '../App'

interface Props {
  messages: Message[]
  onSend: (text: string) => void
  isLoading: boolean
}

export default function ChatPanel({ messages, onSend, isLoading }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  function handleSend() {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    onSend(text)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full flex flex-col bg-[#0A0A0A]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className="max-w-[78%] px-4 py-3 text-[13px] leading-[1.65]"
              style={{
                background: msg.role === 'user' ? '#1D9E75' : '#111111',
                color: msg.role === 'user' ? '#fff' : '#C8C8C8',
                border: msg.role === 'user' ? 'none' : '1px solid #1E1E1E',
                borderRadius: msg.role === 'user' ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Loading dots */}
        {isLoading && (
          <div className="flex justify-start">
            <div
              className="px-4 py-3"
              style={{
                background: '#111',
                border: '1px solid #1E1E1E',
                borderRadius: '4px 12px 12px 12px',
              }}
            >
              <div className="flex gap-1 items-center">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-[#1D9E75] animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-[14px] border-t border-[#141414]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Napište zprávu…"
            disabled={isLoading}
            className="flex-1 px-[14px] py-[10px] rounded-lg bg-[#111] border border-[#1E1E1E]
              text-[13px] text-[#E8E8E8] placeholder-[#555] outline-none
              focus:border-[#2A2A2A] disabled:opacity-50 transition-colors duration-150"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-4 py-[10px] bg-[#1D9E75] text-white rounded-lg
              hover:bg-[#17856A] active:scale-95
              disabled:opacity-40 disabled:cursor-not-allowed
              transition-all duration-150 flex items-center"
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
