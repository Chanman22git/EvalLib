// Minimal client-side CSV export for audit-ready inventory downloads (FR-UI-1).

function escapeCell(value: unknown): string {
  const s = value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Accepts any array of plain objects (typed API rows assign to `object`).
export function toCsv(rows: readonly object[]): string {
  if (!rows.length) return "";
  const records = rows as ReadonlyArray<Record<string, unknown>>;
  const headers = Object.keys(records[0]);
  const lines = [headers.join(",")];
  for (const row of records) {
    lines.push(headers.map((h) => escapeCell(row[h])).join(","));
  }
  return lines.join("\n");
}

export function downloadCsv(filename: string, rows: readonly object[]): void {
  const blob = new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
