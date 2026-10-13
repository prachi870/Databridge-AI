import { useRef, useState } from 'react';
import { authenticatedFetch } from '../lib/api';

interface DatabaseUploadProps {
  onUploadSuccess: (dbId: string) => void;
}

export const DatabaseUpload = ({ onUploadSuccess }: DatabaseUploadProps) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [datasetName, setDatasetName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
    e.target.value = '';
  };

  const handleFiles = async (files: File[]) => {
    const extensions = files.map((file) => file.name.toLowerCase().split('.').pop());
    const onlyCsv = extensions.every((extension) => extension === 'csv');
    const singleSupportedFile = files.length === 1
      && ['sqlite', 'db', 'sqlite3', 'csv', 'zip'].includes(extensions[0] || '');
    if (!onlyCsv && !singleSupportedFile) {
      setError('Choose one SQLite database, one CSV/ZIP, or multiple CSV files.');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    if (files.length > 1) {
      files.forEach((file) => formData.append('files', file));
    } else {
      formData.append('file', files[0]);
    }
    if (datasetName.trim()) {
      formData.append('db_id', datasetName.trim());
    }

    try {
      const response = await authenticatedFetch('/api/upload-database', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Upload failed (HTTP ${response.status})`);
      }

      const data = await response.json();

      if (data.source === 'csv') {
        const rowSummary = Object.entries(data.row_counts || {})
          .map(([table, rows]) => `${table}: ${rows} rows`)
          .join(', ');
        setSuccess(
          `Imported "${data.db_id}" with ${data.tables} table${data.tables === 1 ? '' : 's'}`
          + (rowSummary ? ` (${rowSummary})` : '')
          + '. Detected column types automatically.',
        );
      } else {
        setSuccess(`Imported "${data.db_id}" with ${data.tables} tables: ${data.table_names.join(', ')}.`);
      }

      setDatasetName('');
      onUploadSuccess(data.db_id);
      setTimeout(() => {
        setSuccess('');
      }, 10000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const onButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        className={`glass rounded-2xl p-8 border-2 border-dashed transition-all duration-300 cursor-pointer
          ${dragActive
            ? 'border-cyan-400 bg-cyan-400/10 scale-[1.01]'
            : 'border-white/20 hover:border-purple-500/50'
          }
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={!uploading ? onButtonClick : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".sqlite,.db,.sqlite3,.csv,.zip"
          multiple
          onChange={handleChange}
          disabled={uploading}
        />

        <div className="text-center space-y-4">
          {uploading ? (
            <>
              <div className="spinner mx-auto !w-12 !h-12"></div>
              <p className="text-gray-300">Uploading database...</p>
            </>
          ) : (
            <>
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-cyan-400/20 text-4xl shadow-lg shadow-purple-900/20">
                📤
              </div>
              <h3 className="text-2xl font-bold gradient-text">Upload Your Database</h3>
              <p className="text-gray-400">
                Drop files here or click to browse. Your original files are not changed.
              </p>
              <div className="flex flex-wrap justify-center gap-2 text-xs">
                {['SQLite', 'CSV', 'Multiple CSVs', 'ZIP of CSVs'].map((format) => (
                  <span key={format} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-gray-300">
                    {format}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <label className="block space-y-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-purple-300">
          Dataset name <span className="font-normal normal-case text-gray-500">(optional)</span>
        </span>
        <input
          value={datasetName}
          onChange={(event) => setDatasetName(event.target.value)}
          placeholder="Defaults to the file name"
          maxLength={64}
          disabled={uploading}
          className="input-field w-full"
        />
      </label>

      {/* Success Message */}
      {success && (
        <div className="glass rounded-xl p-4 border-l-4 border-green-500 bg-green-500/10">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">✓</span>
              <p className="text-green-300 font-medium">{success}</p>
            </div>
            <button
              onClick={() => setSuccess('')}
              className="text-green-300 hover:text-green-100 text-xl"
              title="Close"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="glass rounded-xl p-4 border-l-4 border-red-500 bg-red-500/10">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <p className="text-red-300 font-medium">{error}</p>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="glass rounded-xl p-4 space-y-2 text-sm text-gray-400">
          <p className="font-semibold text-purple-300">CSV imports</p>
          <ul className="space-y-1">
            <li>• Select several CSVs to create one table per file</li>
            <li>• Or upload a ZIP containing CSVs</li>
            <li>• The first row should contain column names</li>
            <li>• Numeric types are detected automatically</li>
          </ul>
        </div>
        <div className="glass rounded-xl p-4 space-y-2 text-sm text-gray-400">
          <p className="font-semibold text-cyan-300">Database imports</p>
          <ul className="space-y-1">
            <li>• SQLite files must contain at least one table</li>
            <li>• Maximum upload size: 100MB</li>
            <li>• Choose a dataset name or use the filename</li>
            <li>• Your dataset is selected after upload</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
