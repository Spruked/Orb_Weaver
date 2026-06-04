import React from 'react';

interface ScoreCircleProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const ScoreCircle: React.FC<ScoreCircleProps> = ({ score, size = 'md', label }) => {
  const getScoreClass = (s: number) => {
    if (s >= 80) return 'score-excellent';
    if (s >= 60) return 'score-good';
    if (s >= 40) return 'score-fair';
    return 'score-poor';
  };

  const sizeClasses = {
    sm: 'w-16 h-16 text-lg',
    md: 'w-24 h-24 text-2xl',
    lg: 'w-32 h-32 text-3xl'
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`score-circle ${getScoreClass(score)} ${sizeClasses[size]}`}>
        {score}
      </div>
      {label && <span className="text-sm font-medium text-gray-600">{label}</span>}
    </div>
  );
};

export default ScoreCircle;