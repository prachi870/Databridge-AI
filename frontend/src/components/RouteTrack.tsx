import React from 'react';

interface RouteTrackProps {
  decision: 'local' | 'api';
  confidence: number;
  threshold: number;
}

export const RouteTrack: React.FC<RouteTrackProps> = ({ decision, confidence, threshold }) => {
  const localActive = decision === 'local';
  const apiActive = decision === 'api';

  return (
    <div className="relative w-full max-w-2xl mx-auto py-8">
      {/* SVG Visualization */}
      <svg viewBox="0 0 400 120" className="w-full h-auto">
        {/* Background paths */}
        <path
          d="M 50 60 Q 125 20, 200 60"
          fill="none"
          stroke="var(--color-line)"
          strokeWidth="2"
          opacity="0.3"
        />
        <path
          d="M 50 60 Q 125 100, 200 60"
          fill="none"
          stroke="var(--color-line)"
          strokeWidth="2"
          opacity="0.3"
        />

        {/* Active path - Local */}
        {localActive && (
          <path
            d="M 50 60 Q 125 20, 200 60"
            fill="none"
            stroke="var(--color-local)"
            strokeWidth="3"
            className="flow"
          />
        )}

        {/* Active path - API */}
        {apiActive && (
          <path
            d="M 50 60 Q 125 100, 200 60"
            fill="none"
            stroke="var(--color-api)"
            strokeWidth="3"
            className="flow"
          />
        )}

        {/* Router output lines */}
        <line x1="200" y1="60" x2="350" y2="30" stroke="var(--color-line)" strokeWidth="2" opacity="0.3" />
        <line x1="200" y1="60" x2="350" y2="90" stroke="var(--color-line)" strokeWidth="2" opacity="0.3" />

        {/* Nodes */}
        <circle cx="50" cy="60" r="8" fill="var(--color-ink)" />
        <circle 
          cx="200" 
          cy="60" 
          r="10" 
          fill={localActive ? 'var(--color-local)' : apiActive ? 'var(--color-api)' : 'var(--color-muted)'}
        />
        <circle cx="350" cy="30" r="8" fill={localActive ? 'var(--color-local)' : 'var(--color-line)'} />
        <circle cx="350" cy="90" r="8" fill={apiActive ? 'var(--color-api)' : 'var(--color-line)'} />

        {/* Labels */}
        <text x="50" y="85" textAnchor="middle" fontSize="12" fill="var(--color-ink)">Query</text>
        <text x="200" y="85" textAnchor="middle" fontSize="12" fill="var(--color-ink)">Router</text>
        <text x="350" y="20" textAnchor="middle" fontSize="11" fill="var(--color-local)">Local</text>
        <text x="350" y="110" textAnchor="middle" fontSize="11" fill="var(--color-api)">API</text>
      </svg>

      {/* Decision Info */}
      <div className="mt-6 p-4 bg-white rounded-lg border-2 border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-medium text-gray-600">Routed to:</span>
            <span 
              className={`ml-2 text-lg font-bold ${
                localActive ? 'text-[var(--color-local)]' : 'text-[var(--color-api)]'
              }`}
            >
              {decision.toUpperCase()}
            </span>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-600">Confidence</div>
            <div className="text-xl font-bold text-gray-900">{(confidence * 100).toFixed(1)}%</div>
          </div>
        </div>
        <div className="mt-3 flex items-center">
          <span className="text-xs text-gray-500 mr-2">Threshold: {(threshold * 100).toFixed(1)}%</span>
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-[var(--color-local)] to-[var(--color-api)]"
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
