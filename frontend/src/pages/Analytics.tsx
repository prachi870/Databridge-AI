import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../lib/api';
import { EvaluationDashboard } from '../components/EvaluationDashboard';

interface PerformanceStats {
  total_queries: number;
  avg_execution_time_ms: number;
  local_route_count: number;
  api_route_count: number;
  success_count: number;
  error_count: number;
  fastest_query_ms: number;
  slowest_query_ms: number;
  queries_by_database: Record<string, number>;
}

export default function Analytics() {
  const [stats, setStats] = useState<PerformanceStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = async () => {
    setLoading(true);
    try {
      const response = await authenticatedFetch('/api/performance');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadStats, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-10">
        <div className="glass rounded-3xl p-12 text-center">
          <div className="spinner mx-auto mb-4"></div>
          <p className="text-gray-400">Loading analytics...</p>
        </div>
      </main>
    );
  }

  if (!stats || stats.total_queries === 0) {
    return (
      <main className="mx-auto max-w-7xl space-y-8 px-6 py-10">
        <div className="glass rounded-3xl p-12 text-center card-3d">
          <div className="text-8xl mb-6 float-animation">📊</div>
          <h3 className="text-3xl font-bold text-white mb-3">
            No Analytics Data Yet
          </h3>
          <p className="text-gray-400 text-lg">
            Execute some queries to see performance analytics
          </p>
        </div>
        <EvaluationDashboard />
      </main>
    );
  }

  const successRate = (stats.success_count / stats.total_queries) * 100;
  const localRoutePercent = (stats.local_route_count / stats.total_queries) * 100;
  const apiRoutePercent = (stats.api_route_count / stats.total_queries) * 100;

  return (
    <main className="mx-auto max-w-7xl px-6 py-10 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 mb-12">
        <div className="inline-block">
          <h1 className="text-6xl font-bold mb-2">
            <span className="gradient-text">Performance</span>
            <span className="text-white"> Analytics</span>
          </h1>
          <div className="h-1 bg-gradient-to-r from-violet-600 via-purple-600 to-pink-600 rounded-full"></div>
        </div>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          Real-time insights into your query performance 📊
        </p>
        <button onClick={loadStats} className="btn-secondary text-sm">
          🔄 Refresh Data
        </button>
      </div>

      <EvaluationDashboard />

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Queries */}
        <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10">
            <div className="text-4xl mb-2">📊</div>
            <div className="text-sm font-semibold text-blue-300 mb-1 uppercase tracking-wide">
              Total Queries
            </div>
            <div className="text-4xl font-bold text-blue-400">
              {stats.total_queries}
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-green-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10">
            <div className="text-4xl mb-2">✅</div>
            <div className="text-sm font-semibold text-green-300 mb-1 uppercase tracking-wide">
              Success Rate
            </div>
            <div className="text-4xl font-bold text-green-400">
              {successRate.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400 mt-1">
              {stats.success_count} / {stats.total_queries}
            </div>
          </div>
        </div>

        {/* Avg Execution Time */}
        <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-purple-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10">
            <div className="text-4xl mb-2">⚡</div>
            <div className="text-sm font-semibold text-purple-300 mb-1 uppercase tracking-wide">
              Avg Response
            </div>
            <div className="text-4xl font-bold text-purple-400">
              {stats.avg_execution_time_ms.toFixed(0)}
              <span className="text-xl text-gray-400">ms</span>
            </div>
          </div>
        </div>

        {/* Error Count */}
        <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-red-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
          <div className="relative z-10">
            <div className="text-4xl mb-2">⚠️</div>
            <div className="text-sm font-semibold text-red-300 mb-1 uppercase tracking-wide">
              Errors
            </div>
            <div className="text-4xl font-bold text-red-400">
              {stats.error_count}
            </div>
          </div>
        </div>
      </div>

      {/* Routing Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Route Distribution */}
        <div className="glass rounded-3xl p-6 card-3d space-y-4">
          <h3 className="text-2xl font-bold gradient-text">Route Distribution</h3>
          
          <div className="space-y-4">
            {/* Local Routes */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-green-300 flex items-center gap-2">
                  <span>🟢</span>
                  <span>Local Model</span>
                </span>
                <span className="text-sm text-gray-400">
                  {stats.local_route_count} queries ({localRoutePercent.toFixed(1)}%)
                </span>
              </div>
              <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-500"
                  style={{ width: `${localRoutePercent}%` }}
                ></div>
              </div>
            </div>

            {/* API Routes */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-orange-300 flex items-center gap-2">
                  <span>🟠</span>
                  <span>API Model</span>
                </span>
                <span className="text-sm text-gray-400">
                  {stats.api_route_count} queries ({apiRoutePercent.toFixed(1)}%)
                </span>
              </div>
              <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-orange-500 to-orange-400 transition-all duration-500"
                  style={{ width: `${apiRoutePercent}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>

        {/* Speed Stats */}
        <div className="glass rounded-3xl p-6 card-3d space-y-4">
          <h3 className="text-2xl font-bold gradient-text">Speed Stats</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 glass rounded-xl">
              <div className="flex items-center gap-3">
                <span className="text-3xl">🚀</span>
                <div>
                  <div className="text-sm text-gray-400">Fastest Query</div>
                  <div className="text-2xl font-bold text-green-400">
                    {stats.fastest_query_ms.toFixed(0)}ms
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 glass rounded-xl">
              <div className="flex items-center gap-3">
                <span className="text-3xl">🐌</span>
                <div>
                  <div className="text-sm text-gray-400">Slowest Query</div>
                  <div className="text-2xl font-bold text-orange-400">
                    {stats.slowest_query_ms.toFixed(0)}ms
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Queries by Database */}
      {Object.keys(stats.queries_by_database).length > 0 && (
        <div className="glass rounded-3xl p-6 card-3d space-y-4">
          <h3 className="text-2xl font-bold gradient-text">Queries by Database</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(stats.queries_by_database)
              .sort(([, a], [, b]) => b - a)
              .map(([dbId, count]) => (
                <div key={dbId} className="glass rounded-xl p-4 card-3d">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">🗄️</span>
                      <span className="font-mono text-sm text-cyan-400">{dbId}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-purple-400">{count}</div>
                      <div className="text-xs text-gray-400">
                        {((count / stats.total_queries) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}
    </main>
  );
}
