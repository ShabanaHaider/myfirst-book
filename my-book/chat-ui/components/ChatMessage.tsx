import React from 'react';
import { Message } from '../types/chat';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const { role, content, timestamp } = message;

  // Format the timestamp for display
  const formattedTime = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div
      className={`message ${role}`}
      role="log"
      aria-label={`${role} message: ${content}`}
    >
      <div className="content">{content}</div>
      <div className="time text-xs opacity-70 mt-1" aria-hidden="true">
        {formattedTime}
      </div>
    </div>
  );
};

export default ChatMessage;