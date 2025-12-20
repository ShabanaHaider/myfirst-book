import React from 'react';
import ChatBot from '@site/src/components/ChatBot';

// This component wraps the entire app
// It's the perfect place to add global components like the chatbot
export default function Root({ children }) {
  return (
    <>
      {children}
      <ChatBot />
    </>
  );
}
