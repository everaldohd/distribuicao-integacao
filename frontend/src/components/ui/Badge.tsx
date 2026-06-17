import { clsx } from 'clsx'

interface Props {
  label: string
  color?: 'gray' | 'blue' | 'green' | 'yellow' | 'red'
}

const colors = {
  gray:   'bg-gray-100 text-gray-700',
  blue:   'bg-blue-100 text-blue-700',
  green:  'bg-green-100 text-green-700',
  yellow: 'bg-yellow-100 text-yellow-700',
  red:    'bg-red-100 text-red-700',
}

export function Badge({ label, color = 'gray' }: Props) {
  return (
    <span className={clsx('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', colors[color])}>
      {label}
    </span>
  )
}
