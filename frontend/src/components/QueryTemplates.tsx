import { useState } from 'react';

interface Template {
  id: string;
  name: string;
  description: string;
  template: string;
  category: string;
  icon: string;
}

const templates: Template[] = [
  {
    id: 'count-all',
    name: 'Count All Records',
    description: 'Get total number of records in a table',
    template: 'How many {table_name} are there?',
    category: 'Aggregation',
    icon: '🔢',
  },
  {
    id: 'list-all',
    name: 'List All Records',
    description: 'Show all records from a table',
    template: 'List all {table_name}',
    category: 'Selection',
    icon: '📋',
  },
  {
    id: 'top-n',
    name: 'Top N Records',
    description: 'Get top records by a column',
    template: 'Show top {number} {table_name} by {column_name}',
    category: 'Sorting',
    icon: '🏆',
  },
  {
    id: 'filter-equals',
    name: 'Filter by Value',
    description: 'Find records matching a value',
    template: 'Find {table_name} where {column_name} equals {value}',
    category: 'Filtering',
    icon: '🔍',
  },
  {
    id: 'filter-range',
    name: 'Filter by Range',
    description: 'Find records within a range',
    template: 'Find {table_name} where {column_name} is between {min} and {max}',
    category: 'Filtering',
    icon: '📏',
  },
  {
    id: 'group-count',
    name: 'Group and Count',
    description: 'Count records by category',
    template: 'How many {table_name} are there in each {category_column}?',
    category: 'Aggregation',
    icon: '📊',
  },
  {
    id: 'average',
    name: 'Calculate Average',
    description: 'Get average value of a column',
    template: 'What is the average {column_name} of {table_name}?',
    category: 'Aggregation',
    icon: '📈',
  },
  {
    id: 'min-max',
    name: 'Find Min/Max',
    description: 'Get minimum or maximum value',
    template: 'What is the maximum {column_name} in {table_name}?',
    category: 'Aggregation',
    icon: '⚡',
  },
  {
    id: 'join-simple',
    name: 'Simple Join',
    description: 'Combine data from two tables',
    template: 'Show {table1} with their {table2}',
    category: 'Join',
    icon: '🔗',
  },
  {
    id: 'search-text',
    name: 'Text Search',
    description: 'Search for text pattern',
    template: 'Find {table_name} where {column_name} contains {text}',
    category: 'Filtering',
    icon: '🔎',
  },
  {
    id: 'date-filter',
    name: 'Filter by Date',
    description: 'Find records by date',
    template: 'Show {table_name} from {year}',
    category: 'Filtering',
    icon: '📅',
  },
  {
    id: 'distinct',
    name: 'Unique Values',
    description: 'Get distinct values',
    template: 'Show all unique {column_name} from {table_name}',
    category: 'Selection',
    icon: '✨',
  },
];

interface QueryTemplatesProps {
  onSelectTemplate: (template: string) => void;
}

export function QueryTemplates({ onSelectTemplate }: QueryTemplatesProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [searchTerm, setSearchTerm] = useState('');

  const categories = ['All', ...Array.from(new Set(templates.map(t => t.category)))];

  const filteredTemplates = templates.filter(t => {
    const matchesCategory = selectedCategory === 'All' || t.category === selectedCategory;
    const matchesSearch = searchTerm === '' || 
      t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.template.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold gradient-text flex items-center gap-2">
          <span>📝</span>
          <span>Query Templates</span>
        </h3>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search templates..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field flex-1 text-sm"
        />
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="select-field text-sm"
        >
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
        {filteredTemplates.map((template) => (
          <button
            key={template.id}
            onClick={() => onSelectTemplate(template.template)}
            className="glass rounded-xl p-4 text-left hover:bg-white/5 transition-all duration-200 card-3d group"
          >
            <div className="flex items-start gap-3">
              <span className="text-3xl flex-shrink-0 group-hover:scale-110 transition-transform">
                {template.icon}
              </span>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-white mb-1 group-hover:text-purple-300 transition-colors">
                  {template.name}
                </h4>
                <p className="text-xs text-gray-400 mb-2">
                  {template.description}
                </p>
                <div className="glass rounded-lg px-2 py-1 text-xs font-mono text-green-300 overflow-hidden">
                  <span className="block truncate">
                    {template.template}
                  </span>
                </div>
                <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">
                  {template.category}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="glass rounded-xl p-8 text-center">
          <div className="text-4xl mb-2">🔍</div>
          <p className="text-gray-400">No templates found</p>
        </div>
      )}
    </div>
  );
}
