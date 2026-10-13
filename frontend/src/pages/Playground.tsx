import { lazy, Suspense, useState, useEffect } from 'react';
import { DatabaseUpload } from '../components/DatabaseUpload';
import { QueryHistory } from '../components/QueryHistory';
import { ExportResults } from '../components/ExportResults';
import { QueryTemplates } from '../components/QueryTemplates';
import { DatabaseInfo } from '../components/DatabaseInfo';
import { DataProfile } from '../components/DataProfile';
import { authenticatedFetch } from '../lib/api';

const ResultChart = lazy(() =>
  import('../components/ResultChart').then((module) => ({ default: module.ResultChart })),
);

interface Database {
  db_id: string;
  schema: string;
}

interface ConversationTurn {
  question: string;
  sql: string;
}

function explainQueryError(message: string): { title: string; guidance: string } {
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes('model') && (lowerMessage.includes('unavailable') || lowerMessage.includes('not found'))) {
    return {
      title: 'The AI model is unavailable',
      guidance: 'Ask the project administrator to update TEACHER_MODEL in .env and restart the backend.',
    };
  }
  if (lowerMessage.includes('api key') || lowerMessage.includes('api_key') || lowerMessage.includes('authentication')) {
    return {
      title: 'AI access is not configured',
      guidance: 'Add a valid provider API key to .env, then restart the backend.',
    };
  }
  if (lowerMessage.includes('daily api call limit') || lowerMessage.includes('rate limit')) {
    return {
      title: 'The request limit has been reached',
      guidance: 'Please wait before trying again, or ask the administrator to review the API limits.',
    };
  }
  if (lowerMessage.includes('failed to fetch') || lowerMessage.includes('networkerror')) {
    return {
      title: 'Could not reach the server',
      guidance: 'Check that the backend is running, then retry your question.',
    };
  }
  if (lowerMessage.includes('no such table') || lowerMessage.includes('no such column')) {
    return {
      title: 'The generated query did not match this dataset',
      guidance: 'Check the table and column names in the schema panel, then try asking in a different way.',
    };
  }

  return {
    title: 'We could not answer that question',
    guidance: 'Check the dataset schema and try a shorter question that names the table or column.',
  };
}

export default function Playground() {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [selectedDb, setSelectedDb] = useState('');
  const [question, setQuestion] = useState('');
  const [clarification, setClarification] = useState('');
  const [needsClarification, setNeedsClarification] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const [feedbackError, setFeedbackError] = useState('');
  const [showExpectedAnswer, setShowExpectedAnswer] = useState(false);
  const [expectedAnswer, setExpectedAnswer] = useState('');
  const [result, setResult] = useState<any>(null);
  const [conversation, setConversation] = useState<ConversationTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showSchemaInfo, setShowSchemaInfo] = useState(true);
  const [dbLoading, setDbLoading] = useState(true);
  const [dbError, setDbError] = useState('');
  const selectedDatabase = databases.find((database) => database.db_id === selectedDb);
  const tableNames = selectedDatabase
    ? Array.from(
        selectedDatabase.schema.matchAll(/CREATE TABLE\s+"?([^"\s(]+)"?\s*\(/gi),
        (match) => match[1],
      )
    : [];
  const questionSuggestions = tableNames.slice(0, 4).map((tableName) => ({
    label: `Count ${tableName}`,
    question: `How many rows are in ${tableName}?`,
  }));
  const queryError = error ? explainQueryError(error) : null;
  const resultError = result?.status === 'err' && result.error
    ? explainQueryError(result.error)
    : null;

  const loadDatabases = async (newDatabaseId?: string) => {
    setDbLoading(true);
    setDbError('');
    try {
      const response = await authenticatedFetch('/api/databases');
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const detail = typeof errorData?.detail === 'string'
          ? errorData.detail
          : `Request failed (HTTP ${response.status})`;
        throw new Error(detail);
      }
      const data = await response.json();
      setDatabases(data);
      
      if (newDatabaseId) {
        setSelectedDb(newDatabaseId);
        setConversation([]);
        setResult(null);
        setError('');
      }
    } catch (err: any) {
      console.error('Failed to load databases:', err);
      setDbError(err.message || 'Failed to connect to backend');
    } finally {
      setDbLoading(false);
    }
  };

  useEffect(() => {
    loadDatabases();
  }, []);

  const handleQuery = async (clarifiedQuestion?: string) => {
    const queryText = clarifiedQuestion ?? question.trim();
    if (!selectedDb || !queryText) {
      setError('Please select a database and enter a question');
      return;
    }

    if (!clarifiedQuestion && /\b(top|best|most|highest|lowest|recent|latest)\b/i.test(queryText)) {
      setNeedsClarification(true);
      setError('');
      return;
    }

    setNeedsClarification(false);
    setFeedbackSaved(false);
    setFeedbackError('');
    setShowExpectedAnswer(false);
    setExpectedAnswer('');
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await authenticatedFetch('/api/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          db_id: selectedDb,
          question: queryText,
          mode: 'auto',
          preview_only: true,
          context: conversation.slice(-4),
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const detail = errorData?.detail;
        const message = Array.isArray(detail)
          ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join('. ')
          : typeof detail === 'string'
            ? detail
            : `Request failed (HTTP ${response.status})`;
        throw new Error(message);
      }
      const data = await response.json();
      setResult({ ...data, previewQuestion: queryText });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const submitFeedback = async (correct: boolean) => {
    if (!result?.query_id) return;
    setFeedbackError('');
    try {
      const response = await authenticatedFetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_id: result.query_id,
          correct,
          expected_answer: expectedAnswer.trim() || null,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(typeof data?.detail === 'string' ? data.detail : `Feedback could not be saved (HTTP ${response.status})`);
      }
      setFeedbackSaved(true);
      setShowExpectedAnswer(false);
    } catch (err) {
      setFeedbackError(err instanceof Error ? err.message : 'Feedback could not be saved');
    }
  };

  const handleExecutePreview = async () => {
    if (!result?.query_id || !result?.sql) return;
    setLoading(true);
    setError('');
    try {
      const response = await authenticatedFetch('/api/execute-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_id: result.query_id,
          db_id: selectedDb,
          question: result.previewQuestion,
          sql: result.sql,
          route: result.route,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(typeof errorData?.detail === 'string' ? errorData.detail : `Execution failed (HTTP ${response.status})`);
      }
      const executed = await response.json();
      setConversation((turns) => [
        ...turns,
        { question: result.previewQuestion, sql: result.sql },
      ].slice(-20));
      setResult({
        ...result,
        ...executed,
        requires_confirmation: false,
        timing: {
          ...result.timing,
          execute_ms: executed.execution_ms,
          total_ms: result.timing.total_ms + executed.execution_ms,
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not execute reviewed SQL');
    } finally {
      setLoading(false);
    }
  };

  const handleReplayQuery = (dbId: string, queryText: string) => {
    setSelectedDb(dbId);
    setConversation([]);
    setResult(null);
    // Don't set the question for upload/delete entries (they have emoji prefixes)
    if (!queryText.startsWith('📤') && !queryText.startsWith('🗑️')) {
      setQuestion(queryText);
    }
    setShowHistory(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectTemplate = (template: string) => {
    setQuestion(template);
    setShowTemplates(false);
  };

  return (
    <main className="mx-auto max-w-7xl px-6 py-10 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 mb-12">
        <div className="inline-block">
          <h1 className="text-4xl font-bold mb-2 sm:text-6xl">
            <span className="gradient-text">SQL Router</span>
            <span className="text-white"> Playground</span>
          </h1>
          <div className="h-1 bg-gradient-to-r from-violet-600 via-purple-600 to-pink-600 rounded-full"></div>
        </div>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          Test natural language queries with AI-powered routing ✨
        </p>
      </div>

      <section className="glass mx-auto grid max-w-4xl gap-3 rounded-2xl p-4 sm:grid-cols-3 sm:p-5" aria-label="How to use the query playground">
        {[
          ['1', 'Choose data', 'Select an uploaded dataset or add one.'],
          ['2', 'Ask a question', 'Use everyday language; name a table for clarity.'],
          ['3', 'Review results', 'Check the answer and generated SQL.'],
        ].map(([number, title, description]) => (
          <div key={number} className="flex items-start gap-3 rounded-xl p-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-purple-500/20 text-sm font-bold text-purple-200">
              {number}
            </span>
            <div>
              <p className="font-semibold text-white">{title}</p>
              <p className="mt-1 text-sm text-gray-400">{description}</p>
            </div>
          </div>
        ))}
      </section>

      {/* Toolbar */}
      <div className="mx-auto grid w-full max-w-lg grid-cols-2 gap-2 sm:flex sm:max-w-none sm:flex-wrap sm:justify-center sm:gap-3">
        <button
          onClick={() => setShowTemplates(!showTemplates)}
          className={`btn-secondary flex items-center justify-center gap-2 px-3 py-2.5 sm:px-6 ${showTemplates ? 'ring-2 ring-purple-400' : ''}`}
        >
          <span className="text-xl">📝</span>
          <span>Templates</span>
        </button>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className={`btn-secondary flex items-center justify-center gap-2 px-3 py-2.5 sm:px-6 ${showHistory ? 'ring-2 ring-purple-400' : ''}`}
        >
          <span className="text-xl">📜</span>
          <span>History</span>
        </button>
        <button
          onClick={() => setShowSchemaInfo(!showSchemaInfo)}
          className={`btn-secondary flex items-center justify-center gap-2 px-3 py-2.5 sm:px-6 ${showSchemaInfo ? 'ring-2 ring-purple-400' : ''}`}
        >
          <span className="text-xl">🗄️</span>
          <span>Schema</span>
        </button>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className={`btn-secondary flex items-center justify-center gap-2 px-3 py-2.5 sm:px-6 ${showUpload ? 'ring-2 ring-purple-400' : ''}`}
        >
          <span className="text-xl">📤</span>
          <span>Add dataset</span>
        </button>
      </div>

      {/* Database Loading Error */}
      {dbError && (
        <div className="glass rounded-xl p-4 border-l-4 border-red-500 bg-red-500/10">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <p className="text-red-300 font-medium">Failed to load databases</p>
                <p className="text-sm text-red-400">{dbError}</p>
              </div>
            </div>
            <button
              onClick={() => loadDatabases()}
              className="btn-secondary text-sm"
            >
              🔄 Retry
            </button>
          </div>
        </div>
      )}

      {/* Query Templates Section */}
      {showTemplates && (
        <div className="glass rounded-3xl p-6 card-3d">
          <QueryTemplates onSelectTemplate={handleSelectTemplate} />
        </div>
      )}

      {/* Query History Section */}
      {showHistory && (
        <QueryHistory onReplay={handleReplayQuery} />
      )}

      {conversation.length > 0 && (
        <section className="glass mx-auto w-full max-w-4xl rounded-2xl p-4 sm:p-5" aria-label="Current conversation">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-white">Conversation continued</h2>
              <p className="mt-1 text-sm text-gray-400">
                Follow-up questions can refer to the previous {conversation.length === 1 ? 'question' : `${conversation.length} questions`}.
                The latest four guide the next SQL draft.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setConversation([])}
              className="btn-secondary px-3 py-2 text-sm"
            >
              New conversation
            </button>
          </div>
          <details className="mt-3">
            <summary className="cursor-pointer text-sm text-violet-200">View previous questions</summary>
            <ol className="mt-3 space-y-3">
              {conversation.slice(-4).map((turn, index) => (
                <li key={`${turn.question}-${index}`} className="rounded-xl border border-white/5 bg-white/[0.03] p-3">
                  <p className="text-sm text-gray-200">{turn.question}</p>
                  <code className="mt-2 block max-h-20 overflow-auto whitespace-pre-wrap break-all text-xs text-cyan-200/80">
                    {turn.sql}
                  </code>
                </li>
              ))}
            </ol>
          </details>
        </section>
      )}

      {/* Input Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Input Card */}
        <div className="lg:col-span-2 glass rounded-3xl p-8 card-3d space-y-6">
          {/* Upload Section */}
          {showUpload && (
            <DatabaseUpload 
              onUploadSuccess={(dbId) => loadDatabases(dbId)}
            />
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Database Selection */}
            <div className="space-y-3">
              <label className="block text-sm font-semibold text-purple-300 uppercase tracking-wide">
                1. Choose your dataset
              </label>
              <select
                value={selectedDb}
                onChange={(e) => {
                  setSelectedDb(e.target.value);
                  setConversation([]);
                  setResult(null);
                  setError('');
                }}
                disabled={dbLoading}
                className="select-field"
              >
                <option value="">{dbLoading ? 'Loading databases...' : 'Choose a database...'}</option>
                {databases.map((db) => (
                  <option key={db.db_id} value={db.db_id}>
                    {db.db_id.replace(/[_-]+/g, ' ')}
                  </option>
                ))}
              </select>
              {selectedDatabase && (
                <p className="text-xs text-gray-400">
                  {tableNames.length} table{tableNames.length === 1 ? '' : 's'} available
                  {tableNames.length > 0 ? `: ${tableNames.join(', ')}` : ''}
                </p>
              )}
            </div>

            <div className="flex flex-col justify-center rounded-xl border border-white/5 bg-white/[0.03] p-4">
              <p className="text-sm font-semibold text-purple-300">Need an idea?</p>
              <p className="mt-1 text-sm text-gray-400">
                {selectedDatabase
                  ? 'Start with a suggested question for one of this dataset’s tables.'
                  : 'Choose a dataset to see questions based on its tables.'}
              </p>
            </div>
          </div>

          {/* Question Input */}
          <div className="space-y-3">
            <label className="block text-sm font-semibold text-purple-300 uppercase tracking-wide">
              2. What would you like to know?
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={selectedDatabase
                ? conversation.length > 0
                  ? 'Ask a follow-up, e.g. Break that down by month'
                  : `For example: How many rows are in ${tableNames[0] || 'this dataset'}?`
                : 'Choose a dataset first, then type a question in everyday language.'}
              className="input-field resize-none"
              rows={4}
              maxLength={500}
            />
            {questionSuggestions.length > 0 && (
              <div className="flex flex-wrap gap-2" aria-label="Suggested questions">
                {questionSuggestions.map((suggestion) => (
                  <button
                    key={suggestion.question}
                    type="button"
                    onClick={() => setQuestion(suggestion.question)}
                    className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1.5 text-xs text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/10"
                  >
                    {suggestion.label}
                  </button>
                ))}
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-500">
              <span>
                Your question is converted to SQL for your review before running on the selected dataset.
              </span>
              <span>{question.length}/500</span>
            </div>
            {needsClarification && (
              <div className="rounded-xl border border-amber-300/20 bg-amber-300/5 p-4">
                <p className="font-semibold text-amber-100">Let’s make that question more precise</p>
                <p className="mt-1 text-sm text-gray-300">
                  Words like “top”, “best”, or “recent” can mean different things. What should the answer be based on?
                </p>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <input
                    value={clarification}
                    onChange={(event) => setClarification(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && clarification.trim()) {
                        handleQuery(`${question.trim()}. Clarification: ${clarification.trim()}`);
                      }
                    }}
                    placeholder="For example: highest number of flights"
                    className="input-field min-w-0 flex-1"
                    aria-label="Clarify the meaning of your question"
                  />
                  <button
                    type="button"
                    disabled={!clarification.trim() || loading}
                    onClick={() => handleQuery(`${question.trim()}. Clarification: ${clarification.trim()}`)}
                    className="btn-secondary"
                  >
                    Continue with clarification
                  </button>
                  <button
                    type="button"
                    onClick={() => setNeedsClarification(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Execute Button */}
          <button
            onClick={() => handleQuery()}
            disabled={loading || !selectedDb || !question.trim()}
            className="btn-primary w-full relative overflow-hidden group"
          >
            <span className="relative z-10 flex items-center justify-center gap-3">
              {loading ? (
                <>
                  <div className="spinner"></div>
                  <span>Executing...</span>
                </>
              ) : (
                <>
                  <span className="text-2xl">⚡</span>
                  <span>{conversation.length > 0 ? 'Ask follow-up' : 'Get answer'}</span>
                </>
              )}
            </span>
            <div className="absolute inset-0 bg-gradient-to-r from-pink-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
          </button>

          {/* Error Display */}
          {queryError && (
            <div role="alert" className="glass rounded-xl border-l-4 border-red-500 bg-red-500/10 p-4">
              <div className="flex items-start gap-3">
                <span className="text-2xl" aria-hidden="true">⚠️</span>
                <div>
                  <p className="font-semibold text-red-200">{queryError.title}</p>
                  <p className="mt-1 text-sm text-red-100/80">{queryError.guidance}</p>
                  <details className="mt-2 text-xs text-red-200/70">
                    <summary className="cursor-pointer">Technical details</summary>
                    <p className="mt-1 break-words">{error}</p>
                  </details>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Schema Info Panel */}
        {showSchemaInfo && (
          <div className="lg:col-span-1">
            <div className="space-y-4">
              <DatabaseInfo dbId={selectedDb} />
              <DataProfile dbId={selectedDb} />
            </div>
          </div>
        )}
      </div>

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          <div className="glass rounded-2xl border-l-4 border-emerald-400 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-200">3. Answer</p>
            {result.requires_confirmation ? (
              <p className="mt-2 text-sm text-gray-300">Review the generated SQL below, then choose whether to run it.</p>
            ) : resultError ? (
              <div role="alert" className="mt-2">
                <p className="font-semibold text-amber-200">{resultError.title}</p>
                <p className="mt-1 text-sm text-gray-300">{resultError.guidance}</p>
                <details className="mt-2 text-xs text-gray-400">
                  <summary className="cursor-pointer">Technical details</summary>
                  <p className="mt-1 break-words">{result.error}</p>
                </details>
              </div>
            ) : result.rows?.length === 1 && result.rows[0]?.length === 1 ? (
              <p className="mt-1 text-3xl font-bold text-white">{String(result.rows[0][0])}</p>
            ) : (
              <p className="mt-1 text-sm text-gray-300">
                {result.rows?.length ?? 0} result row{result.rows?.length === 1 ? '' : 's'} found.
                See the table below for details.
              </p>
            )}
          </div>
          {!result.requires_confirmation && result.query_id && (
            <section className="glass rounded-2xl p-5" aria-label="Answer feedback">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold text-white">Was this answer correct?</p>
                  <p className="mt-1 text-xs text-gray-400">Your feedback is saved locally to help build a project evaluation set.</p>
                </div>
                {feedbackSaved ? (
                  <span className="text-sm font-medium text-emerald-200">Thanks — feedback saved ✓</span>
                ) : (
                  <div className="flex gap-2">
                    <button type="button" onClick={() => submitFeedback(true)} className="btn-secondary text-sm">Yes, correct</button>
                    <button type="button" onClick={() => setShowExpectedAnswer(true)} className="btn-secondary text-sm">No, incorrect</button>
                  </div>
                )}
              </div>
              {showExpectedAnswer && !feedbackSaved && (
                <div className="mt-4 space-y-2">
                  <label htmlFor="expected-answer" className="text-sm text-gray-300">What should the answer have been? (optional)</label>
                  <textarea
                    id="expected-answer"
                    value={expectedAnswer}
                    onChange={(event) => setExpectedAnswer(event.target.value)}
                    maxLength={2000}
                    rows={2}
                    className="input-field w-full resize-y"
                    placeholder="Enter the expected result or a correction"
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={() => submitFeedback(false)} className="btn-primary text-sm">Save feedback</button>
                    <button type="button" onClick={() => setShowExpectedAnswer(false)} className="btn-secondary text-sm">Cancel</button>
                  </div>
                </div>
              )}
              {feedbackError && <p role="alert" className="mt-3 text-sm text-red-300">{feedbackError}</p>}
            </section>
          )}
          {/* Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Route Card */}
            <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-violet-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
              <div className="relative z-10">
                <div className="text-sm font-semibold text-purple-300 mb-2 uppercase tracking-wide">🎯 Route</div>
                <div className={`text-4xl font-bold mb-2 ${
                  result.route === 'local' ? 'text-green-400' : 'text-orange-400'
                }`}>
                  {result.route?.toUpperCase() || 'N/A'}
                </div>
                <div className="text-xs text-gray-400">
                  {result.route === 'local' ? 'Fast & Efficient' : 'High Accuracy'}
                </div>
              </div>
            </div>

            {/* Status Card */}
            <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-green-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
              <div className="relative z-10">
                <div className="text-sm font-semibold text-purple-300 mb-2 uppercase tracking-wide">✓ Status</div>
                <div className={`text-4xl font-bold mb-2 ${
                  result.status === 'ok' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {result.requires_confirmation ? 'Review SQL' : result.status === 'ok' ? '✓ Success' : '✗ Error'}
                </div>
                <div className="text-xs text-gray-400">
                  {result.requires_confirmation ? 'Not executed yet' : result.status === 'ok' ? 'Query executed' : 'Query failed'}
                </div>
              </div>
            </div>

            {/* Time Card */}
            <div className="glass rounded-2xl p-6 card-3d relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-600/20 to-transparent rounded-full blur-2xl group-hover:scale-150 transition-transform duration-500"></div>
              <div className="relative z-10">
                <div className="text-sm font-semibold text-purple-300 mb-2 uppercase tracking-wide">⚡ Time</div>
                <div className="text-4xl font-bold text-blue-400 mb-2">
                  {result.timing?.total_ms?.toFixed(0) || 0}
                  <span className="text-xl text-gray-400">ms</span>
                </div>
                <div className="text-xs text-gray-400">Execution time</div>
              </div>
            </div>
          </div>

          {/* Generated SQL */}
          {result.sql && (
            <div className="glass rounded-3xl p-6 card-3d space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl font-bold gradient-text">Generated SQL</h3>
                <div className="flex gap-2">
                  {result.requires_confirmation && (
                    <>
                      <button
                        type="button"
                        onClick={handleExecutePreview}
                        disabled={loading}
                        className="btn-primary text-sm"
                      >
                        {loading ? 'Executing...' : 'Run read-only query'}
                      </button>
                      <button type="button" onClick={() => setResult(null)} className="btn-secondary text-sm">
                        Cancel
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => navigator.clipboard.writeText(result.sql)}
                    className="btn-secondary text-sm"
                  >
                    📋 Copy
                  </button>
                  {!result.requires_confirmation && result.columns && result.rows && (
                    <ExportResults 
                      result={result}
                      dbId={selectedDb}
                      question={question}
                    />
                  )}
                </div>
              </div>
              {result.requires_confirmation && (
                <div className="rounded-xl border border-amber-300/20 bg-amber-300/5 p-4 text-sm text-amber-100">
                  <p className="font-semibold">Review before running</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-100/80">
                    {(result.safety_warnings || []).map((warning: string) => <li key={warning}>{warning}</li>)}
                  </ul>
                </div>
              )}
              <div className="relative">
                <pre className="glass rounded-xl p-6 overflow-x-auto text-sm font-mono text-green-300 border border-green-500/20">
                  {result.sql}
                </pre>
                <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 rounded-full blur-2xl"></div>
              </div>
            </div>
          )}

          {/* Query Results */}
          {!result.requires_confirmation && result.status === 'ok' && result.columns && result.rows?.length > 1 && (
            <Suspense fallback={<div className="glass rounded-2xl p-6 text-sm text-gray-400">Preparing chart...</div>}>
              <ResultChart columns={result.columns} rows={result.rows} />
            </Suspense>
          )}
          {!result.requires_confirmation && result.columns && result.rows && (
            <div className="glass rounded-3xl p-6 card-3d space-y-4">
              <h3 className="text-2xl font-bold gradient-text">Query Results</h3>
              <div className="table-3d">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr>
                        {result.columns.map((col: string, idx: number) => (
                          <th key={idx} className="px-6 py-4 text-left text-sm font-bold text-purple-300 uppercase tracking-wider">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="glass">
                      {result.rows.length === 0 ? (
                        <tr>
                          <td colSpan={result.columns.length} className="px-6 py-12 text-center text-gray-400">
                            <div className="text-4xl mb-2">📭</div>
                            <div>No rows returned</div>
                          </td>
                        </tr>
                      ) : (
                        result.rows.map((row: any[], rowIdx: number) => (
                          <tr key={rowIdx}>
                            {row.map((cell: any, cellIdx: number) => (
                              <td key={cellIdx} className="px-6 py-4 text-sm text-gray-200">
                                {cell === null ? (
                                  <span className="text-gray-500 italic">NULL</span>
                                ) : (
                                  String(cell)
                                )}
                              </td>
                            ))}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="text-sm text-gray-400 text-center pt-2">
                {result.rows.length} row{result.rows.length !== 1 ? 's' : ''} returned
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && !error && (
        <div className="glass rounded-3xl p-12 text-center card-3d">
          <div className="text-8xl mb-6 float-animation">🎯</div>
          <h3 className="text-3xl font-bold text-white mb-3">
            Ready to Query
          </h3>
          <p className="text-gray-400 text-lg">
            Select a database, enter your question, and click Execute!
          </p>
        </div>
      )}
    </main>
  );
}
