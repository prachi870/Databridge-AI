import React from 'react';

interface ScoreScaleProps {
  score: number;
  min?: number;
  max?: number;
  label?: string;
  showValue?: boolean;
}

export const ScoreScale: React.FC<ScoreScaleProps> = ({ 
  score, 
  min = 0, 
  max = 1, 
  label,
  showValue = true 
}) => {
  const percentage = ((score - min) / (max - min)) * 100;
  const clampedPercentage = Math.max(0, Math.min(100, percentage));

  // Color based on score
  const getColor = () => {
    if (percentage < 33) return 'var(--color-fault)';
    if (percentage < 67) return 'var(--color-api)';
    return 'var(--color-local)';
  };

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          {showValue && (
            <span className="text-sm font-bold text-gray-900">
              {score.toFixed(3)}
            </span>
          )}
        </div>
      )}
      <div className="relative w-full h-8 bg-gray-200 rounded-lg overflow-hidden">
        <div 
          className="h-full transition-all duration-500 ease-out"
          style={{ 
            width: `${clampedPercentage}%`,
            backgroundColor: getColor()
          }}
        />
        {/* Marker line */}
        <div 
          className="absolute top-0 bottom-0 w-0.5 bg-gray-800"
          style={{ left: `${clampedPercentage}%` }}
        />
      </div>
      {/* Scale markers */}
      <div className="flex justify-between mt-1 text-xs text-gray-500">
        <span>{min.toFixed(2)}</span>
        <span>{((min + max) / 2).toFixed(2)}</span>
        <span>{max.toFixed(2)}</span>
      </div>
    </div>
  );
};
