function cellText(value: unknown): string {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function ResultTable({
  title,
  columns,
  rows,
}: {
  title: string
  columns: string[]
  rows: unknown[][]
}) {
  if (!columns.length && !rows.length) {
    return (
      <div className="result-table-wrap">
        <div className="result-table-title">{title}</div>
        <div className="result-table-empty">（空结果）</div>
      </div>
    )
  }

  const cols = columns.length
    ? columns
    : rows[0]?.map((_, i) => `col${i + 1}`) ?? []

  if (cols.length > 0 && rows.length === 0) {
    return (
      <div className="result-table-wrap">
        <div className="result-table-title">{title}</div>
        <div className="result-table-scroll">
          <table className="result-table">
            <thead>
              <tr>
                {cols.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={cols.length} className="result-table-empty">
                  （空结果）
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return (
    <div className="result-table-wrap">
      <div className="result-table-title">{title}</div>
      <div className="result-table-scroll">
        <table className="result-table">
          <thead>
            <tr>
              {cols.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri}>
                {cols.map((_, ci) => (
                  <td key={ci}>{cellText(row[ci])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
