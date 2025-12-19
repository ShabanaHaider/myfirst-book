'use client';

import React, { useState, useCallback } from 'react';
import MessageList from './MessageList';
import InputArea from './InputArea';
import { Message } from '../types/chat';
import { chatApi } from '../lib/api';

interface ChatContainerProps {
  initialMessages?: Message[];
}

const ChatContainer: React.FC<ChatContainerProps> = React.memo(({ initialMessages = [] }) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSendMessage = useCallback(async (messageText: string) => {
    try {
      // Add user message to the chat
      const userMessage: Message = {
        id: Date.now().toString(),
        content: messageText,
        role: 'user',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, userMessage]);
      setIsLoading(true);
      setError(null);

      // Call the API to get the response
      const response = await chatApi.sendMessage(messageText);

      // Add assistant message to the chat
      const assistantMessage: Message = {
        id: Date.now().toString(),
        content: response.answer,
        role: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while sending the message');
      console.error('Error sending message:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="chat-container">
      <h1 className="text-2xl font-bold mb-4">Chat Interface</h1>
      <MessageList messages={messages} />
      <InputArea onSendMessage={handleSendMessage} isLoading={isLoading} />
      {error && <div className="error" role="alert">{error}</div>}
    </div>
  );
});

export default ChatContainer;