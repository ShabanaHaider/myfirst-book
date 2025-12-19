import React, { useState } from 'react';
import LoadingSpinner from './LoadingSpinner';

interface InputAreaProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, isLoading }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <form className="input-area" onSubmit={handleSubmit} role="form" aria-label="Chat input form">
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your message here..."
          disabled={isLoading}
          className="flex-1 p-3 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Type your message"
          aria-disabled={isLoading}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className={`px-4 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed ${isLoading || !inputValue.trim() ? 'bg-blue-300' : 'bg-blue-600 hover:bg-blue-700'}`}
          aria-label={isLoading ? "Sending message" : "Send message"}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
      {isLoading && (
        <div className="w-full mt-2" role="status" aria-live="polite">
          <LoadingSpinner message="Thinking..." />
        </div>
      )}
    </form>
  );
};

export default InputArea;