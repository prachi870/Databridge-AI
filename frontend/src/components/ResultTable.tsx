import React from 'react';

interface ResultTableProps {
  columns: string[];
  rows: any[][];
  maxHeight?: string;
}

export const ResultTable: React.FC<ResultTableProps> = ({ 
  columns, 
  rows, 
  maxHeight = '400px' 
}) => {
  if (!columns || columns.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        No results to display
      </div>
    );
  }

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden">
      <div className="overflow-auto" style={{ maxHeight }}>
        <table className="w-full border-collapse">
          <thead className="bg-gray-100 sticky top-0">
            <tr>
              {columns.map((col, idx) => (
                <th 
                  key={idx}
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b-2 border-gray-300"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white">
            {rows.length === 0 ? (
              <tr>
                <td 
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-gray-500"
                >
                  No rows returned
                </td>
              </tr>
            ) : (
              rows.map((row, rowIdx) => (
                <tr 
                  key={rowIdx}
                  className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                >
                  {row.map((cell, cellIdx) => (
                    <td 
                      key={cellIdx}
                      className="px-4 py-3 text-sm text-gray-900 border-b border-gray-200"
                    >
                      {cell === null ? (
                        <span className="text-gray-400 italic">NULL</span>
                      ) : typeof cell === 'object' ? (
                        <span className="font-mono text-xs">{JSON.stringify(cell)}</span>
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
      {rows.length > 0 && (
        <div className="bg-gray-50 px-4 py-2 text-xs text-gray-600 border-t border-gray-300">
          {rows.length} row{rows.length !== 1 ? 's' : ''} returned
        </div>
      )}
    </div>
  );
};
