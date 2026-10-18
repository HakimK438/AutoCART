// Turns rows into a CSV file and downloads it. `columns` is [[header, (row) => value], ...].
const cell = (v) => {
  const s = v == null ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export function toCsv(columns, rows) {
  return [columns.map(([h]) => cell(h)).join(','), ...rows.map((r) => columns.map(([, get]) => cell(get(r))).join(','))].join('\n');
}

export function downloadCsv(filename, columns, rows) {
  const blob = new Blob(['﻿' + toCsv(columns, rows)], { type: 'text/csv;charset=utf-8;' });  // BOM so Excel reads ₹ and accents correctly
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
