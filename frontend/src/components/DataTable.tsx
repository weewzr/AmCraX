import type { ReactNode } from 'react'

export interface Column<T> {
  key: string
  label: string
  unit?: string
  align?: 'left' | 'right'
  render?: (row: T) => ReactNode
  /** plain-text value for CSV export (defaults to String(row[key])) */
  csv?: (row: T) => string
}

function csvCell(s: string): string {
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function toCsv<T>(columns: Column<T>[], rows: T[]): string {
  const head = columns.map((c) => csvCell(c.unit ? `${c.label} [${c.unit}]` : c.label)).join(',')
  const body = rows.map((r) =>
    columns.map((c) => csvCell(c.csv ? c.csv(r) : String((r as Record<string, unknown>)[c.key] ?? ''))).join(','),
  )
  return [head, ...body].join('\r\n')
}

export function DataTable<T>({ columns, rows, caption, filename }: { columns: Column<T>[]; rows: T[]; caption: string; filename?: string }) {
  const download = () => {
    const blob = new Blob([toCsv(columns, rows)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename ?? 'table.csv'
    a.click()
    URL.revokeObjectURL(url)
  }
  return (
    <div className="table-wrap">
      <div className="table-bar">
        <span className="table-caption">{caption}</span>
        <button type="button" className="btn btn-sm" onClick={download}>Export CSV</button>
      </div>
      <div className="table-scroll" tabIndex={0} role="region" aria-label={caption}>
        <table className="data">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} scope="col" className={c.align === 'right' ? 'r' : ''}>
                  {c.label}{c.unit ? <span className="unit"> [{c.unit}]</span> : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {columns.map((c) => (
                  <td key={c.key} className={c.align === 'right' ? 'r' : ''}>
                    {c.render ? c.render(r) : String((r as Record<string, unknown>)[c.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
