# Quickstart Guide: Next.js Chat UI

## Overview
This guide provides step-by-step instructions to set up and run the Next.js chat UI application that integrates with your existing FastAPI RAG backend.

## Prerequisites
- Node.js 18+ installed
- npm or yarn package manager
- Access to the existing FastAPI backend with the `/chat` endpoint
- Git (optional, for version control)

## Setup Instructions

### 1. Create the Project Directory
```bash
mkdir my-book/chat-ui
cd my-book/chat-ui
```

### 2. Initialize Next.js Application
```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

### 3. Install Additional Dependencies (if needed)
```bash
npm install
```

### 4. Configure Environment Variables
Create a `.env.local` file in the project root:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Replace `http://localhost:8000` with your actual FastAPI backend URL.

### 5. Create Project Structure
Create the following directory structure:
```
chat-ui/
├── components/
├── lib/
├── types/
└── public/
```

### 6. Create Type Definitions
Create `types/chat.ts`:
```typescript
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  answer: string;
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  inputValue: string;
}
```

### 7. Create API Service
Create `lib/api.ts`:
```typescript
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
```

### 8. Run the Application
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

## Configuration Options

### Backend URL
- Set `NEXT_PUBLIC_API_BASE_URL` in `.env.local` to point to your FastAPI backend
- Default value: `http://localhost:8000`

### Development vs Production
- Use different backend URLs for different environments
- Example for production: `NEXT_PUBLIC_API_BASE_URL=https://your-backend.com`

## Testing the Integration

### 1. Verify Backend Connection
- Ensure your FastAPI backend is running and accessible
- Test that the `/chat` endpoint is responding correctly

### 2. Test Chat Functionality
- Open the application in a browser
- Type a message in the input field
- Click "Send" or press Enter
- Verify that you receive a response from the backend
- Check that both your message and the response appear in the chat history

## Troubleshooting

### Common Issues

#### Backend Not Reachable
- Verify the `NEXT_PUBLIC_API_BASE_URL` is correct
- Check that the FastAPI backend is running
- Ensure there are no firewall or CORS issues

#### Type Errors
- Verify that TypeScript types match the API contract
- Check that all required fields are present in requests and responses

#### Build Errors
- Ensure all dependencies are installed: `npm install`
- Verify Node.js version is compatible (18+)

## Next Steps

1. Implement the UI components (MessageList, MessageItem, InputArea, etc.)
2. Add styling and responsive design
3. Implement error handling and loading states
4. Add auto-scroll functionality
5. Test with various query types to the backend