import React from 'react';

interface SqlBlockProps {
  sql: string;
  title?: string;
  maxHeight?: string;
}

export const SqlBlock: React.FC<SqlBlockProps> = ({ sql, title, maxHeight = '300px' }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Simple SQL syntax highlighting
  const highlightSql = (text: string) => {
    const keywords = /\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|ORDER BY|GROUP BY|HAVING|LIMIT|OFFSET|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TABLE|INDEX|VIEW|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|CASE|WHEN|THEN|ELSE|END|IN|NOT|NULL|IS|LIKE|BETWEEN)\b/gi;
    const strings = /('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")/g;
    const numbers = /\b(\d+)\b/g;

    let highlighted = text
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    highlighted = highlighted.replace(keywords, '<span class="text-blue-600 font-semibold">$1</span>');
    highlighted = highlighted.replace(strings, '<span class="text-green-700">$1</span>');
    highlighted = highlighted.replace(numbers, '<span class="text-purple-600">$1</span>');

    return highlighted;
  };

  return (
    <div className="relative">
      {title && (
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-semibold text-gray-700">{title}</h4>
          <button
            onClick={handleCopy}
            className="text-xs px-3 py-1 rounded bg-gray-200 hover:bg-gray-300 transition-colors"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
        </div>
      )}
      <div 
        className="bg-gray-50 border border-gray-300 rounded-lg p-4 overflow-auto font-mono text-sm"
        style={{ maxHeight }}
      >
        <pre 
          className="whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: highlightSql(sql) }}
        />
      </div>
    </div>
  );
};
