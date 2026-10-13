import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../lib/api';

export default function Results() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authenticatedFetch('/api/metrics/summary')
      .then(res => res.json())
      .then(data => {
        setSummary(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load summary:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4">
            <div className="spinner mx-auto !w-16 !h-16"></div>
            <p className="text-gray-400 text-lg">Loading results...</p>
          </div>
        </div>
      </main>
    );
  }

  const metrics = summary ? [
    { label: 'Test Cases', value: summary.n_test || 0, suffix: '', color: 'from-blue-600 to-cyan-600', icon: '📊' },
    { label: 'Router Accuracy', value: ((summary.router_acc || 0) * 100).toFixed(1), suffix: '%', color: 'from-violet-600 to-purple-600', icon: '🎯' },
    { label: 'API Accuracy', value: ((summary.api_acc || 0) * 100).toFixed(1), suffix: '%', color: 'from-green-600 to-emerald-600', icon: '✓' },
    { label: 'Cost Savings', value: ((summary.cost_saving_pct || 0) * 100).toFixed(1), suffix: '%', color: 'from-amber-600 to-orange-600', icon: '💰' },
    { label: 'Base Model', value: ((summary.greedy_acc_base || 0) * 100).toFixed(1), suffix: '%', color: 'from-slate-600 to-gray-600', icon: '🤖' },
    { label: 'Fine-tuned', value: ((summary.greedy_acc_ft || 0) * 100).toFixed(1), suffix: '%', color: 'from-indigo-600 to-blue-600', icon: '⚡' },
    { label: 'Escape Rate', value: ((summary.esc_rate || 0) * 100).toFixed(1), suffix: '%', color: 'from-rose-600 to-pink-600', icon: '🚀' },
    { label: 'AUROC', value: (summary.auroc_sep || 0).toFixed(3), suffix: '', color: 'from-teal-600 to-cyan-600', icon: '📈' },
  ] : [];

  return (
    <main className="mx-auto max-w-7xl px-6 py-10 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 mb-12">
        <div className="inline-block">
          <h1 className="text-6xl font-bold mb-2">
            <span className="gradient-text">Benchmark</span>
            <span className="text-white"> Results</span>
          </h1>
          <div className="h-1 bg-gradient-to-r from-violet-600 via-purple-600 to-pink-600 rounded-full"></div>
        </div>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          Performance metrics from SQL Router evaluation 📊
        </p>
      </div>

      {summary ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {metrics.map((metric, idx) => (
            <div
              key={idx}
              className="glass rounded-2xl p-6 card-3d relative overflow-hidden group"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              {/* Glow effect */}
              <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${metric.color} opacity-20 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-500`}></div>
              
              {/* Content */}
              <div className="relative z-10 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-3xl">{metric.icon}</span>
                  <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${metric.color} pulse-glow`}></div>
                </div>
                
                <div>
                  <div className="text-sm font-semibold text-purple-300 uppercase tracking-wide">
                    {metric.label}
                  </div>
                  <div className={`text-4xl font-bold bg-gradient-to-r ${metric.color} bg-clip-text text-transparent mt-2`}>
                    {metric.value}{metric.suffix}
                  </div>
                </div>

                {/* Progress bar */}
                <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className={`h-full bg-gradient-to-r ${metric.color} rounded-full transition-all duration-1000`}
                    style={{ 
                      width: metric.suffix === '%' ? `${metric.value}%` : '100%' 
                    }}
                  ></div>
                </div>
              </div>

              {/* Shine effect on hover */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 shine"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass rounded-3xl p-16 text-center card-3d">
          <div className="text-8xl mb-6 float-animation">📊</div>
          <h3 className="text-3xl font-bold text-white mb-3">
            No Results Available
          </h3>
          <p className="text-gray-400 text-lg">
            Run benchmark evaluation to see results here
          </p>
        </div>
      )}

      {/* Additional Info Cards */}
      {summary && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-12">
          {/* Performance Card */}
          <div className="glass rounded-3xl p-8 card-3d space-y-4 lg:col-span-2">
            <h3 className="text-2xl font-bold gradient-text mb-6">Performance Insights</h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 glass rounded-xl">
                <span className="text-gray-300">Router vs API Accuracy Gap</span>
                <span className="text-2xl font-bold text-purple-400">
                  {((summary.api_acc - summary.router_acc) * 100).toFixed(1)}%
                </span>
              </div>
              
              <div className="flex items-center justify-between p-4 glass rounded-xl">
                <span className="text-gray-300">Fine-tuning Improvement</span>
                <span className="text-2xl font-bold text-green-400">
                  +{((summary.greedy_acc_ft - summary.greedy_acc_base) * 100).toFixed(1)}%
                </span>
              </div>
              
              <div className="flex items-center justify-between p-4 glass rounded-xl">
                <span className="text-gray-300">Local Model Efficiency</span>
                <span className="text-2xl font-bold text-blue-400">
                  {((1 - summary.esc_rate) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {/* Quick Stats Card */}
          <div className="glass rounded-3xl p-8 card-3d space-y-4">
            <h3 className="text-2xl font-bold gradient-text mb-6">Quick Stats</h3>
            
            <div className="space-y-4">
              <div className="text-center p-4 glass rounded-xl">
                <div className="text-4xl mb-2">🎯</div>
                <div className="text-3xl font-bold text-purple-400">
                  {summary.n_test}
                </div>
                <div className="text-sm text-gray-400 mt-1">Test Queries</div>
              </div>
              
              <div className="text-center p-4 glass rounded-xl">
                <div className="text-4xl mb-2">⚡</div>
                <div className="text-3xl font-bold text-green-400">
                  {(summary.auroc_sep * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Probe AUROC</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
