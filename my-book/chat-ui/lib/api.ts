import { ChatRequest, ChatResponse } from '../types/chat';

const DEFAULT_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export class ChatApi {
  private baseUrl: string;

  constructor() {
    this.baseUrl = DEFAULT_API_BASE_URL;
  }

  async sendMessage(message: string): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API request failed with status ${response.status}`);
    }

    return response.json();
  }
}

export const chatApi = new ChatApi();