import { useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

interface ResultChartProps {
  columns: string[];
  rows: unknown[][];
}

export function ResultChart({ columns, rows }: ResultChartProps) {
  const [chartType, setChartType] = useState<'bar' | 'line'>('bar');
  const chart = useMemo(() => {
    const numericIndex = columns.findIndex((_, index) =>
      rows.some((row) => typeof row[index] === 'number' && Number.isFinite(row[index])),
    );
    if (numericIndex < 0) return null;
    const labelIndex = columns.findIndex((_, index) => index !== numericIndex);
    const data = rows
      .filter((row) => typeof row[numericIndex] === 'number' && Number.isFinite(row[numericIndex]))
      .map((row, index) => ({
        label: labelIndex >= 0 ? String(row[labelIndex] ?? 'NULL') : String(index + 1),
        value: row[numericIndex] as number,
      }));
    return { data, label: columns[labelIndex] ?? 'Row', value: columns[numericIndex] };
  }, [columns, rows]);
  const insights = useMemo(() => {
    if (!chart || chart.data.length === 0) return null;
    const highest = chart.data.reduce((best, item) => item.value > best.value ? item : best);
    const lowest = chart.data.reduce((best, item) => item.value < best.value ? item : best);
    const average = chart.data.reduce((sum, item) => sum + item.value, 0) / chart.data.length;
    return { highest, lowest, average };
  }, [chart]);

  if (rows.length < 2) return null;

  return (
    <section className="glass rounded-3xl p-6 card-3d space-y-4" aria-label="Chart of query results">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold gradient-text">Visualize results</h3>
          <p className="text-xs text-gray-400">Automatic chart suggestion based on numeric result columns.</p>
        </div>
        {chart && (
          <div className="flex gap-2" role="group" aria-label="Chart type">
            {(['bar', 'line'] as const).map((type) => (
              <button
                key={type}
                type="button"
                aria-pressed={chartType === type}
                onClick={() => setChartType(type)}
                className={`btn-secondary px-3 py-1.5 text-sm ${chartType === type ? 'ring-2 ring-cyan-400' : ''}`}
              >
                {type === 'bar' ? 'Bar' : 'Line'}
              </button>
            ))}
          </div>
        )}
      </div>
      {!chart || !chart.data.length ? (
        <p className="rounded-xl bg-white/5 p-4 text-sm text-gray-400">
          This result has no numeric column to chart. Try a query that returns a count, sum, or other number.
        </p>
      ) : (
        <>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              {chartType === 'bar' ? (
                <BarChart data={chart.data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff18" />
                  <XAxis dataKey="label" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#111827', border: '1px solid #ffffff22', borderRadius: 8 }} />
                  <Bar dataKey="value" name={chart.value} fill="#a78bfa" radius={[5, 5, 0, 0]} />
                </BarChart>
              ) : (
                <LineChart data={chart.data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff18" />
                  <XAxis dataKey="label" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#111827', border: '1px solid #ffffff22', borderRadius: 8 }} />
                  <Line type="monotone" dataKey="value" name={chart.value} stroke="#67e8f9" strokeWidth={2} />
                </LineChart>
              )}
            </ResponsiveContainer>
          </div>
          <p className="text-xs text-gray-500">Showing {chart.value} by {chart.label}.</p>
          {insights && (
            <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/5 p-4 text-sm text-gray-200">
              <p className="font-semibold text-cyan-100">Quick insight</p>
              <p className="mt-1">
                Highest: {insights.highest.label} ({insights.highest.value}); lowest: {insights.lowest.label} ({insights.lowest.value});
                {' '}average {chart.value}: {insights.average.toFixed(2)}.
              </p>
              <p className="mt-1 text-xs text-gray-400">Summary is based on the rows returned for this query.</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
