/**
 * Ícone de ajuda (ⓘ) que mostra um texto explicativo ao passar o mouse.
 * Uso: <InfoTip text="explicação..." />
 */
export function InfoTip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex align-middle ml-1">
      <span className="flex items-center justify-center w-4 h-4 rounded-full bg-gray-300 text-white text-[10px] font-bold cursor-help select-none">
        i
      </span>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-1 hidden group-hover:block z-50 w-60 rounded-lg bg-gray-900 text-white text-xs font-normal leading-snug px-3 py-2 shadow-lg"
      >
        {text}
      </span>
    </span>
  )
}
