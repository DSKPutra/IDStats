import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input, Textarea } from '@/components/ui/textarea'
import { ColumnPicker } from './ColumnPicker'
import type { GroupRaw } from './fields'

interface GroupsInputProps {
  id: string
  value: GroupRaw[]
  onChange: (v: GroupRaw[]) => void
  itemLabel: string
  minItems: number
}

export function GroupsInput({ id, value, onChange, itemLabel, minItems }: GroupsInputProps) {
  const update = (i: number, patch: Partial<GroupRaw>) => onChange(value.map((g, j) => (j === i ? { ...g, ...patch } : g)))
  return (
    <div className="flex flex-col gap-3">
      {value.map((g, i) => (
        <div key={i} className="grid gap-2 rounded-lg border p-3 sm:grid-cols-[12rem_1fr_auto]">
          <div className="flex flex-col gap-1.5">
            <Input
              aria-label={`Nama ${itemLabel.toLowerCase()} ${i + 1}`}
              value={g.name}
              onChange={(e) => update(i, { name: e.target.value })}
            />
            <ColumnPicker label="Dari dataset" onPick={(vals, col) => update(i, { values: vals.join(', '), name: col })} />
          </div>
          <Textarea
            id={i === 0 ? id : undefined}
            aria-label={`Data ${g.name || `${itemLabel} ${i + 1}`}`}
            className="min-h-16"
            value={g.values}
            placeholder="Contoh: 23, 25, 21, 22"
            onChange={(e) => update(i, { values: e.target.value })}
          />
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Hapus ${g.name}`}
            disabled={value.length <= minItems}
            onClick={() => onChange(value.filter((_, j) => j !== i))}
          >
            <Trash2 />
          </Button>
        </div>
      ))}
      <Button
        variant="outline"
        size="sm"
        className="self-start"
        onClick={() => onChange([...value, { name: `${itemLabel} ${value.length + 1}`, values: '' }])}
      >
        <Plus /> Tambah {itemLabel.toLowerCase()}
      </Button>
    </div>
  )
}
