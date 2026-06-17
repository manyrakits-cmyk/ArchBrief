interface Props {
  svg: string | null
}

export default function FloorplanPanel({ svg }: Props) {
  if (!svg) {
    return (
      <div className="flex flex-col items-center justify-center h-40 text-center px-4">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center mb-3"
          style={{ background: '#161616' }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#555"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
        </div>
        <p className="text-xs text-[#555] leading-relaxed">
          Půdorys se zobrazí jakmile<br />popíšete místnosti
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-auto w-full">
      <div dangerouslySetInnerHTML={{ __html: svg }} />
    </div>
  )
}
