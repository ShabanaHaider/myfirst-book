# Feature Specification: Next.js Chat UI Integration

## Overview
Create a simple chat UI using Next.js (App Router) that integrates with an existing FastAPI RAG backend. The backend uses Qdrant as a vector database and an LLM for response generation. This feature focuses on frontend implementation and integration only.

## Project Context
- Frontend project root folder: `my-book`
- Create new folder: `chat-ui` inside `my-book`
- Use Next.js (App Router) inside `chat-ui`
- FastAPI backend already exists and is running

## Backend Characteristics (DO NOT REIMPLEMENT)
- Endpoint: POST `/chat`
- Input: `{"message": "User query"}`
- Output: `{"answer": "LLM generated response using Qdrant context"}`
- Backend responsibilities: Accept user query, retrieve contextual chunks from Qdrant, combine query + context, send to LLM, return generated response

## User Scenarios & Testing
1. User opens the chat UI and sees a clean, minimal interface
2. User types a query in the input box and clicks Send
3. UI shows loading state ("Thinking...") while waiting for response
4. UI displays the response from the backend
5. User can continue the conversation with follow-up queries
6. If an error occurs, user sees a friendly error message

## Functional Requirements
1. **Chat Interface**: The UI must provide a simple chat interface with input box, send button, and chat message list showing both user and assistant messages
2. **Backend Integration**: The UI must communicate with the FastAPI backend only via the `/chat` endpoint
3. **Loading States**: The UI must show a loading state ("Thinking...") while waiting for backend response
4. **Input Disabling**: Input box and send button must be disabled while waiting for response
5. **Error Handling**: The UI must provide basic error handling with user-friendly messages
6. **No Direct Database Access**: The frontend must not call Qdrant directly or any LLM APIs
7. **No API Keys**: The frontend must not contain any API keys or sensitive credentials
8. **Minimal Styling**: The UI must be clean and beginner-friendly without heavy styling libraries

## Non-Functional Requirements
1. The UI should load quickly and respond to user interactions in a timely manner
2. The UI should be accessible and usable on common screen sizes
3. The UI should gracefully handle network errors or backend unavailability

## Success Criteria
1. Users can successfully send queries to the backend and receive responses
2. The loading state is clearly visible during backend processing
3. The UI provides feedback during error conditions
4. The interface remains responsive and user-friendly throughout the interaction
5. The UI successfully integrates with the existing FastAPI backend without requiring backend changes

## Assumptions
1. The FastAPI backend is already running and accessible
2. The `/chat` endpoint is properly configured and functional
3. Network connectivity exists between the frontend and backend
4. The backend handles all security and authentication requirements

## Dependencies
1. Existing FastAPI RAG backend with Qdrant integration
2. Next.js development environment
3. Node.js runtime environment

## Scope
### In Scope
- Next.js chat UI implementation
- Integration with existing FastAPI backend
- User interface design and user experience
- Loading states and error handling

### Out of Scope
- Backend implementation (FastAPI, Qdrant, LLM)
- Database schema changes
- Authentication implementation
- Advanced styling beyond minimal requirements