# Data Model: Next.js Chat UI

## Overview
Data structures and models for the Next.js chat UI application.

## Core Entities

### Message
The fundamental unit representing a chat message in the conversation.

```typescript
interface Message {
  id: string;           // Unique identifier for the message
  content: string;      // The actual message text content
  role: 'user' | 'assistant';  // The sender of the message (user or AI assistant)
  timestamp: Date;      // When the message was created/sent
}
```

**Validation Rules**:
- `id` must be a unique string (UUID recommended)
- `content` must be a non-empty string with maximum length of 1000 characters
- `role` must be either 'user' or 'assistant'
- `timestamp` must be a valid date/time value

### ChatState
Represents the current state of the chat interface.

```typescript
interface ChatState {
  messages: Message[];      // Array of all messages in the conversation
  isLoading: boolean;       // Whether the app is waiting for a response
  error: string | null;     // Any error message to display
  inputValue: string;       // Current value in the input field
}
```

### API Request/Response Models

#### Chat Request
```typescript
interface ChatRequest {
  message: string;          // The user's message to send to the backend
}
```

#### Chat Response
```typescript
interface ChatResponse {
  answer: string;           // The assistant's response from the backend
}
```

## State Transitions

### Message Flow
1. User types message → `inputValue` updates
2. User submits message → new `Message` with `role: 'user'` added to `messages`
3. API request initiated → `isLoading` becomes `true`, input disabled
4. API response received → new `Message` with `role: 'assistant'` added to `messages`
5. Response processed → `isLoading` becomes `false`, input enabled
6. Error occurs → `error` populated with error message

## Data Relationships

- Each `ChatState` contains multiple `Message` objects in the `messages` array
- Messages are ordered chronologically in the `messages` array
- The `isLoading` flag in `ChatState` is directly tied to API request lifecycle

## Validation Rules

### Message Content
- Minimum length: 1 character
- Maximum length: 1000 characters
- Must not contain only whitespace

### API Communication
- Requests must follow the `ChatRequest` format
- Responses must follow the `ChatResponse` format
- Error handling must be implemented for network failures