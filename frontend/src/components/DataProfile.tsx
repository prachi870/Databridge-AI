import { useEffect, useState } from 'react';
import { authenticatedFetch } from '../lib/api';

interface ProfileColumn {
  name: string;
  type: string;
  null_count: number;
  min: number | null;
  max: number | null;
}

interface ProfileTable {
  name: string;
  row_count: number;
  columns: ProfileColumn[];
  examples: Record<string, unknown>[];
}

interface DataProfileResponse {
  db_id: string;
  tables: ProfileTable[];
}

export function DataProfile({ dbId }: { dbId: string }) {
  const [profile, setProfile] = useState<DataProfileResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!dbId) {
      setProfile(null);
      setError('');
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError('');
    authenticatedFetch(`/api/database/${encodeURIComponent(dbId)}/profile`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new Error(typeof data?.detail === 'string' ? data.detail : `Profile request failed (HTTP ${response.status})`);
        }
        return response.json() as Promise<DataProfileResponse>;
      })
      .then(setProfile)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        setError(reason instanceof Error ? reason.message : 'Could not profile this dataset.');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [dbId]);

  if (!dbId) return null;

  return (
    <section className="glass rounded-2xl p-5 space-y-4" aria-label="Dataset profile">
      <div>
        <h3 className="text-lg font-bold text-white">Dataset profile</h3>
        <p className="text-xs text-gray-400">Table sizes, missing values, numeric ranges, and sample records.</p>
      </div>
      {loading && <p className="text-sm text-gray-400">Analyzing dataset...</p>}
      {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
      {profile?.tables.map((table) => (
        <details key={table.name} className="rounded-xl border border-white/10 bg-white/[0.03] p-3" open={profile.tables.length === 1}>
          <summary className="cursor-pointer font-semibold text-cyan-100">
            {table.name} <span className="text-xs font-normal text-gray-400">· {table.row_count.toLocaleString()} rows · {table.columns.length} columns</span>
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-gray-400">
                <tr><th className="py-2 pr-3">Column</th><th className="py-2 pr-3">Type</th><th className="py-2 pr-3">Missing</th><th className="py-2">Range</th></tr>
              </thead>
              <tbody>
                {table.columns.map((column) => (
                  <tr key={column.name} className="border-t border-white/5">
                    <td className="py-2 pr-3 text-gray-200">{column.name}</td>
                    <td className="py-2 pr-3 text-purple-200">{column.type}</td>
                    <td className="py-2 pr-3 text-gray-300">{column.null_count}</td>
                    <td className="py-2 text-gray-300">{column.min === null ? '—' : `${column.min} to ${column.max}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {table.examples.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Example rows</p>
              {table.examples.map((row, index) => (
                <pre key={index} className="overflow-x-auto rounded-lg bg-black/20 p-2 text-xs text-gray-300">{JSON.stringify(row)}</pre>
              ))}
            </div>
          )}
        </details>
      ))}
    </section>
  );
}
