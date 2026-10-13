import { useEffect, useState } from 'react';
import { api, type EvaluationSummary } from '../lib/api';

function AccuracyCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="glass rounded-xl p-4">
      <p className="text-sm text-gray-400">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${color}`}>{value.toFixed(1)}%</p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${color.replace('text-', 'bg-')}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

export function EvaluationDashboard() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getEvaluation()
      .then(setSummary)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Could not load benchmark results.'));
  }, []);

  return (
    <section className="glass rounded-3xl p-6 card-3d space-y-5" aria-labelledby="benchmark-evaluation-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-cyan-300">Model comparison</p>
          <h2 id="benchmark-evaluation-title" className="mt-1 text-2xl font-bold gradient-text">
            Benchmark Evaluation
          </h2>
        </div>
        {summary && <span className="text-sm text-gray-400">{summary.sample_count} saved test examples</span>}
      </div>

      {error ? (
        <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">{error}</p>
      ) : !summary ? (
        <p className="text-sm text-gray-400">Loading benchmark results...</p>
      ) : summary.sample_count === 0 ? (
        <p className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-gray-300">
          No saved benchmark examples are available yet. Add evaluation data to compare the models.
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <AccuracyCard label="Local model accuracy" value={summary.local_accuracy} color="text-emerald-300" />
            <AccuracyCard label="API model accuracy" value={summary.api_accuracy} color="text-orange-300" />
            <AccuracyCard label="Router-selected accuracy" value={summary.routed_accuracy} color="text-cyan-300" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="text-sm text-gray-400">Questions escalated to API</p>
              <p className="mt-1 text-2xl font-semibold text-orange-200">{summary.api_route_percent.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="text-sm text-gray-400">Estimated savings vs always using API</p>
              <p className="mt-1 text-2xl font-semibold text-green-200">{summary.estimated_cost_savings_percent.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
              <p className="text-sm text-gray-400">User-reviewed answers</p>
              <p className="mt-1 text-2xl font-semibold text-purple-200">{summary.user_feedback_count}</p>
              {summary.user_feedback_count > 0 && (
                <p className="mt-1 text-xs text-gray-400">{summary.user_feedback_accuracy.toFixed(1)}% marked correct</p>
              )}
            </div>
          </div>
          <p className="text-xs leading-relaxed text-gray-500">
            Accuracy is calculated from saved benchmark outcomes using the current routing threshold.
            Cost savings are estimates based on configured model costs, not live billing data.
          </p>
        </>
      )}
    </section>
  );
}
