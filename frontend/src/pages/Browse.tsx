import { useState, useEffect } from 'react';
import { authenticatedFetch } from '../lib/api';

interface Database {
  db_id: string;
  schema: string;
}

export default function Browse() {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [selectedDb, setSelectedDb] = useState('');
  const [schema, setSchema] = useState('');

  useEffect(() => {
    authenticatedFetch('/api/databases')
      .then(res => res.json())
      .then(data => setDatabases(data))
      .catch(err => console.error('Failed to load databases:', err));
  }, []);

  useEffect(() => {
    if (selectedDb) {
      const db = databases.find(d => d.db_id === selectedDb);
      setSchema(db?.schema || '');
    } else {
      setSchema('');
    }
  }, [selectedDb, databases]);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 mb-12">
        <div className="inline-block">
          <h1 className="text-6xl font-bold mb-2">
            <span className="gradient-text">Browse</span>
            <span className="text-white"> Databases</span>
          </h1>
          <div className="h-1 bg-gradient-to-r from-violet-600 via-purple-600 to-pink-600 rounded-full"></div>
        </div>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          Explore database schemas and structure 🗂️
        </p>
      </div>

      {/* Database Selection */}
      <div className="glass rounded-3xl p-8 card-3d space-y-4">
        <label className="block text-sm font-semibold text-purple-300 uppercase tracking-wide">
          🗄️ Select Database
        </label>
        <select
          value={selectedDb}
          onChange={(e) => setSelectedDb(e.target.value)}
          className="select-field"
        >
          <option value="">Choose a database...</option>
          {databases.map((db) => (
            <option key={db.db_id} value={db.db_id}>
              {db.db_id}
            </option>
          ))}
        </select>
      </div>

      {/* Schema Display */}
      {schema ? (
        <div className="glass rounded-3xl p-8 card-3d space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-3xl font-bold">
              <span className="gradient-text">Schema:</span>
              <span className="text-white"> {selectedDb}</span>
            </h2>
            <button
              onClick={() => navigator.clipboard.writeText(schema)}
              className="btn-secondary"
            >
              📋 Copy Schema
            </button>
          </div>
          
          <div className="relative">
            <pre className="glass rounded-xl p-6 overflow-x-auto text-sm font-mono text-cyan-300 border border-cyan-500/20 whitespace-pre-wrap">
              {schema}
            </pre>
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>
          </div>

          {/* Table count */}
          <div className="glass rounded-xl p-4 text-center">
            <span className="text-gray-400">Tables found:</span>
            <span className="ml-2 text-2xl font-bold text-purple-400">
              {schema.match(/CREATE TABLE/gi)?.length || 0}
            </span>
          </div>
        </div>
      ) : selectedDb ? (
        <div className="glass rounded-3xl p-16 text-center card-3d">
          <div className="spinner mx-auto !w-16 !h-16 mb-6"></div>
          <h3 className="text-2xl font-bold text-white">
            Loading schema...
          </h3>
        </div>
      ) : (
        <div className="glass rounded-3xl p-16 text-center card-3d">
          <div className="text-8xl mb-6 float-animation">🗂️</div>
          <h3 className="text-3xl font-bold text-white mb-3">
            Select a Database
          </h3>
          <p className="text-gray-400 text-lg">
            Choose a database from the dropdown to view its schema
          </p>
        </div>
      )}

      {/* Database Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-12">
        {databases.map((db, idx) => (
          <button
            key={db.db_id}
            onClick={() => setSelectedDb(db.db_id)}
            className={`glass rounded-2xl p-6 card-3d text-left transition-all duration-300 ${
              selectedDb === db.db_id ? 'ring-2 ring-purple-500' : ''
            }`}
            style={{ animationDelay: `${idx * 100}ms` }}
          >
            <div className="text-4xl mb-3">🗄️</div>
            <h3 className="text-lg font-bold text-white mb-2">{db.db_id}</h3>
            <div className="text-sm text-gray-400">
              {db.schema.match(/CREATE TABLE/gi)?.length || 0} tables
            </div>
            {selectedDb === db.db_id && (
              <div className="mt-3 h-1 bg-gradient-to-r from-violet-600 to-purple-600 rounded-full"></div>
            )}
          </button>
        ))}
      </div>
    </main>
  );
}
