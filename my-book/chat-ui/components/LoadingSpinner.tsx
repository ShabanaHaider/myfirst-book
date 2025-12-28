import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message = 'Thinking...' }) => {
  return (
    <div className="loading">
      <div className="spinner"></div>
      <span className="ml-2">{message}</span>
    </div>
  );
};

export default LoadingSpinner;