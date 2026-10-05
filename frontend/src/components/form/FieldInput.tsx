import { Input, Textarea } from '@/components/ui/textarea'
import { parseNumbers } from '@/lib/utils'
import { ColumnPicker } from './ColumnPicker'
import { ALTERNATIVE_OPTIONS, type FieldDef, type GroupRaw, type RawValue, type RawValues } from './fields'
import { GraphEditor } from './GraphEditor'
import { GroupsInput } from './GroupsInput'

const selectClass =
  'h-9 w-full rounded-md border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50'

export function FieldInput({ field, value, onChange, raw = {} }: { field: FieldDef; value: RawValue; onChange: (v: RawValue) => void; raw?: RawValues }) {
  const id = `f-${field.key.replace(/\W/g, '-')}`
  const text = typeof value === 'string' ? value : ''
  let control
  switch (field.type) {
    case 'graph': {
      const directed = typeof field.graphDirected === 'function' ? field.graphDirected(raw) : Boolean(field.graphDirected)
      control = <GraphEditor id={id} value={text} onChange={onChange} valueCount={field.graphValues ?? 1} directed={directed} placeholder={field.placeholder} />
      break
    }
    case 'textarea':
      control = (
        <Textarea
          id={id}
          className="min-h-40 leading-relaxed"
          spellCheck={false}
          value={text}
          placeholder={field.placeholder}
          onChange={(e) => onChange(e.target.value)}
        />
      )
      break
    case 'numbers':
    case 'matrix':
    case 'cells': {
      const count = field.type === 'numbers' && text ? parseNumbers(text).values.length : null
      control = (
        <>
          <Textarea
            id={id}
            className={field.type === 'numbers' ? 'min-h-20' : 'min-h-28'}
            value={text}
            placeholder={field.placeholder}
            onChange={(e) => onChange(e.target.value)}
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            {count !== null && <span className="text-xs text-muted-foreground">Terbaca {count} angka.</span>}
            {field.type === 'numbers' && <ColumnPicker onPick={(vals) => onChange(vals.join(', '))} />}
          </div>
        </>
      )
      break
    }
    case 'groups':
    case 'variables':
      control = (
        <GroupsInput
          id={id}
          value={value as GroupRaw[]}
          onChange={onChange}
          itemLabel={field.itemLabel ?? (field.type === 'variables' ? 'Variabel' : 'Kelompok')}
          minItems={field.minItems ?? 2}
        />
      )
      break
    case 'select':
    case 'alternative':
      control = (
        <select id={id} className={selectClass} value={text} onChange={(e) => onChange(e.target.value)}>
          {(field.type === 'alternative' ? ALTERNATIVE_OPTIONS : (field.options ?? [])).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )
      break
    case 'boolean':
      control = (
        <label className="flex items-center gap-2 text-sm">
          <input id={id} type="checkbox" className="size-4 accent-primary" checked={text === 'true'} onChange={(e) => onChange(String(e.target.checked))} />
          {field.placeholder ?? 'Ya'}
        </label>
      )
      break
    default:
      control = (
        <Input
          id={id}
          inputMode={['number', 'integer', 'alpha'].includes(field.type) ? 'decimal' : undefined}
          value={text}
          placeholder={field.placeholder}
          onChange={(e) => onChange(e.target.value)}
        />
      )
  }
  const wide = ['numbers', 'matrix', 'cells', 'groups', 'variables', 'textarea', 'graph'].includes(field.type)
  return (
    <div className={wide ? 'flex flex-col gap-1.5 sm:col-span-2' : 'flex flex-col gap-1.5'}>
      {field.type !== 'boolean' && (
        <label htmlFor={id} className="text-sm font-medium">
          {field.label}
          {field.required && <span className="text-danger"> *</span>}
        </label>
      )}
      {control}
      {field.hint && <p className="text-xs text-muted-foreground">{field.hint}</p>}
    </div>
  )
}
