import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../lib/api';

interface HistoryItem {
  id: string;
  timestamp: string;
  db_id: string;
  question: string;
  route: string;
  status: string;
  sql: string;
  execution_time_ms: number;
}

interface QueryHistoryProps {
  onReplay: (dbId: string, question: string) => void;
}

export function QueryHistory({ onReplay }: QueryHistoryProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await authenticatedFetch('/api/history?limit=50');
      const data = await response.json();
      setHistory(data.items);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadHistory, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const deleteQuery = async (id: string) => {
    try {
      await authenticatedFetch(`/api/history/${id}`, {
        method: 'DELETE',
      });
      setHistory(history.filter(item => item.id !== id));
    } catch (error) {
      console.error('Failed to delete query:', error);
    }
  };

  const clearAll = async () => {
    if (!confirm('Clear all query history?')) return;
    
    try {
      await authenticatedFetch('/api/history', {
        method: 'DELETE',
      });
      setHistory([]);
    } catch (error) {
      console.error('Failed to clear history:', error);
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="glass rounded-3xl p-8 text-center">
        <div className="spinner mx-auto mb-4"></div>
        <p className="text-gray-400">Loading history...</p>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="glass rounded-3xl p-12 text-center card-3d">
        <div className="text-6xl mb-4">📜</div>
        <h3 className="text-2xl font-bold text-white mb-2">No Query History</h3>
        <p className="text-gray-400">Your executed queries will appear here</p>
      </div>
    );
  }

  return (
    <div className="glass rounded-3xl p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-2xl font-bold gradient-text flex items-center gap-2">
          <span>📜</span>
          <span>Query History</span>
          <span className="text-sm text-gray-400 font-normal">({history.length})</span>
        </h3>
        <div className="flex gap-2">
          <button
            onClick={loadHistory}
            className="btn-secondary text-sm"
          >
            🔄 Refresh
          </button>
          <button
            onClick={clearAll}
            className="btn-secondary text-sm hover:bg-red-500/20"
          >
            🗑️ Clear All
          </button>
        </div>
      </div>

      {/* History Items */}
      <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
        {history.map((item) => (
          <div
            key={item.id}
            className="glass rounded-xl p-4 hover:bg-white/5 transition-all duration-200 card-3d"
          >
            {/* Header Row */}
            <div className="flex items-start justify-between gap-4 mb-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-purple-400 uppercase tracking-wide">
                    {item.db_id}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                      item.route === 'local'
                        ? 'bg-green-500/20 text-green-400'
                        : item.route === 'api'
                        ? 'bg-orange-500/20 text-orange-400'
                        : item.route === 'upload'
                        ? 'bg-blue-500/20 text-blue-400'
                        : item.route === 'delete'
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}
                  >
                    {item.route === 'upload' ? '📤' : item.route === 'delete' ? '🗑️' : item.route}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                      item.status === 'ok'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}
                  >
                    {item.status === 'ok' ? '✓' : '✗'}
                  </span>
                  {item.route !== 'upload' && item.route !== 'delete' && (
                    <span className="text-xs text-gray-500">
                      {item.execution_time_ms.toFixed(0)}ms
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-200 truncate">
                  {item.question}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatTime(item.timestamp)}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 flex-shrink-0">
                {item.route !== 'delete' && (
                  <button
                    onClick={() => onReplay(item.db_id, item.question)}
                    className="btn-secondary text-xs px-3 py-1"
                    title={item.route === 'upload' ? 'Select this database' : 'Replay this query'}
                  >
                    {item.route === 'upload' ? '📂' : '▶️'}
                  </button>
                )}
                <button
                  onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                  className="btn-secondary text-xs px-3 py-1"
                  title="View details"
                >
                  {expanded === item.id ? '▼' : '▶'}
                </button>
                <button
                  onClick={() => deleteQuery(item.id)}
                  className="btn-secondary text-xs px-3 py-1 hover:bg-red-500/20"
                  title="Delete from history"
                >
                  🗑️
                </button>
              </div>
            </div>

            {/* Expanded Details */}
            {expanded === item.id && (
              <div className="mt-3 pt-3 border-t border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-gray-400 uppercase">
                    {item.route === 'upload' || item.route === 'delete' ? 'Details' : 'Generated SQL'}
                  </span>
                  <button
                    onClick={() => navigator.clipboard.writeText(item.sql)}
                    className="text-xs text-purple-400 hover:text-purple-300"
                  >
                    📋 Copy
                  </button>
                </div>
                <pre className="glass rounded-lg p-3 overflow-x-auto text-xs font-mono text-green-300">
                  {item.sql}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
