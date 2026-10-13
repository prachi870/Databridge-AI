import { useCallback, useEffect, useState } from 'react';
import { authenticatedFetch } from '../lib/api';

interface Table {
  name: string;
  columns: Array<{ name: string; type: string }>;
}

interface DatabaseInfoProps {
  dbId: string;
}

export function DatabaseInfo({ dbId }: DatabaseInfoProps) {
  const [schema, setSchema] = useState<string>('');
  const [tables, setTables] = useState<Table[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedTable, setExpandedTable] = useState<string | null>(null);

  const loadSchema = useCallback(async () => {
    setLoading(true);
    try {
      const response = await authenticatedFetch('/api/databases');
      const databases = await response.json();
      const db = databases.find((d: any) => d.db_id === dbId);
      
      if (db) {
        setSchema(db.schema);
        parseSchema(db.schema);
      }
    } catch (error) {
      console.error('Failed to load schema:', error);
    } finally {
      setLoading(false);
    }
  }, [dbId]);

  useEffect(() => {
    if (!dbId) {
      setSchema('');
      setTables([]);
      return;
    }

    loadSchema();
  }, [dbId, loadSchema]);

  const parseSchema = (schemaText: string) => {
    const parsedTables: Table[] = [];
    
    const lines = schemaText.split('\n');
    let currentTable: Table | null = null;
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      // Detect table creation
      if (trimmed.startsWith('CREATE TABLE')) {
        const match = trimmed.match(/CREATE TABLE\s+"?([^"(\s]+)"?\s*\(/i);
        if (match) {
          if (currentTable) {
            parsedTables.push(currentTable);
          }
          currentTable = { name: match[1], columns: [] };
        }
      } else if (currentTable && trimmed && !trimmed.startsWith(')') && !trimmed.startsWith('--')) {
        // Parse column definition
        const colMatch = trimmed.match(/"?([^"\s,]+)"?\s+([A-Z]+)/i);
        if (colMatch && !trimmed.toUpperCase().includes('PRIMARY KEY') && !trimmed.toUpperCase().includes('FOREIGN KEY')) {
          currentTable.columns.push({
            name: colMatch[1],
            type: colMatch[2],
          });
        }
      }
    }
    
    if (currentTable) {
      parsedTables.push(currentTable);
    }
    
    setTables(parsedTables);
  };

  if (!dbId) {
    return (
      <div className="glass rounded-xl p-6 text-center">
        <div className="text-4xl mb-2">🗄️</div>
        <p className="text-gray-400 text-sm">Select a database to view schema</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass rounded-xl p-6 text-center">
        <div className="spinner mx-auto mb-2"></div>
        <p className="text-gray-400 text-sm">Loading schema...</p>
      </div>
    );
  }

  return (
    <div className="glass rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-purple-300 uppercase tracking-wide flex items-center gap-2">
          <span>🗄️</span>
          <span>Database Schema</span>
        </h3>
        <button
          onClick={() => navigator.clipboard.writeText(schema)}
          className="text-xs text-purple-400 hover:text-purple-300"
        >
          📋 Copy
        </button>
      </div>

      {tables.length > 0 ? (
        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
          {tables.map((table) => (
            <div key={table.name} className="glass rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedTable(expandedTable === table.name ? null : table.name)}
                className="w-full px-3 py-2 flex items-center justify-between hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono text-cyan-400 font-bold">
                    {table.name}
                  </span>
                  <span className="text-xs text-gray-500">
                    ({table.columns.length} columns)
                  </span>
                </div>
                <span className="text-gray-400">
                  {expandedTable === table.name ? '▼' : '▶'}
                </span>
              </button>
              
              {expandedTable === table.name && (
                <div className="px-3 pb-2 space-y-1">
                  {table.columns.map((col, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 text-xs py-1 px-2 hover:bg-white/5 rounded"
                    >
                      <span className="text-green-400 font-mono">{col.name}</span>
                      <span className="text-gray-500">:</span>
                      <span className="text-orange-400 font-mono">{col.type}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-4">
          <p className="text-gray-400 text-xs">No tables found</p>
        </div>
      )}
    </div>
  );
}
