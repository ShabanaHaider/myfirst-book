# Chat UI

A simple chat interface for interacting with the RAG backend using Next.js and TypeScript.

## Features

- Real-time chat interface
- Message history display
- Loading states with "Thinking..." indicator
- Error handling
- Auto-scroll to latest message
- Responsive design
- Accessibility support

## Prerequisites

- Node.js 18+
- Access to a running FastAPI backend with a `/chat` endpoint

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create a `.env.local` file in the root directory with the following content:
   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```
   Replace `http://localhost:8000` with your actual backend URL.

## Running the Application

1. Development mode:
   ```bash
   npm run dev
   ```

2. The application will be available at `http://localhost:3000`

## Environment Variables

- `NEXT_PUBLIC_API_BASE_URL`: The base URL for the FastAPI backend (defaults to 'http://localhost:8000')

## API Integration

The application communicates with the backend via the `/chat` endpoint:
- Request: `{"message": "User query"}`
- Response: `{"answer": "LLM generated response using Qdrant context"}`

## Architecture

- **Components**: Reusable UI components in the `components/` directory
- **Types**: TypeScript type definitions in the `types/` directory
- **API**: API service layer in the `lib/` directory
- **Pages**: Next.js App Router pages in the `app/` directory

## Key Components

- `ChatContainer`: Manages state and API calls
- `MessageList`: Displays chat messages with auto-scroll
- `ChatMessage`: Individual message display
- `InputArea`: Input field and send button with loading states
- `LoadingSpinner`: Loading indicator component