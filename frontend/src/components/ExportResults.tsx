interface ExportResultsProps {
  result: {
    columns: string[];
    rows: any[][];
    sql: string;
    route: string;
    status: string;
    timing: {
      total_ms: number;
    };
  };
  dbId: string;
  question: string;
}

export function ExportResults({ result, dbId, question }: ExportResultsProps) {
  const exportToCSV = () => {
    // Create CSV content
    const headers = result.columns.join(',');
    const rows = result.rows
      .map(row => 
        row.map(cell => {
          // Handle special cases
          if (cell === null) return 'NULL';
          const str = String(cell);
          // Escape quotes and wrap in quotes if contains comma or quote
          if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return `"${str.replace(/"/g, '""')}"`;
          }
          return str;
        }).join(',')
      )
      .join('\n');
    
    const csv = `${headers}\n${rows}`;
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const filename = `${dbId}_${Date.now()}.csv`;
    link.download = filename;
    link.click();
    
    // Show success message
    console.log(`✓ CSV exported: ${filename} (${result.rows.length} rows)`);
  };

  const exportToJSON = () => {
    // Create JSON structure
    const data = {
      metadata: {
        database: dbId,
        question: question,
        timestamp: new Date().toISOString(),
        route: result.route,
        status: result.status,
        execution_time_ms: result.timing.total_ms,
      },
      sql: result.sql,
      results: {
        columns: result.columns,
        rows: result.rows,
        row_count: result.rows.length,
      },
    };
    
    // Download
    const blob = new Blob([JSON.stringify(data, null, 2)], { 
      type: 'application/json;charset=utf-8;' 
    });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    const filename = `${dbId}_${Date.now()}.json`;
    link.download = filename;
    link.click();
    
    // Show success message
    console.log(`✓ JSON exported: ${filename} (${result.rows.length} rows)`);
  };

  return (
    <div className="flex gap-2">
      <button
        onClick={exportToCSV}
        className="btn-secondary text-sm flex items-center gap-2 hover:scale-105 transition-transform"
        title="Export results as CSV"
      >
        <span>📊</span>
        <span>CSV</span>
      </button>
      <button
        onClick={exportToJSON}
        className="btn-secondary text-sm flex items-center gap-2 hover:scale-105 transition-transform"
        title="Export results as JSON"
      >
        <span>📄</span>
        <span>JSON</span>
      </button>
    </div>
  );
}
