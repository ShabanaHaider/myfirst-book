# Chatbot Integration Guide

## Overview

Your RAG (Retrieval-Augmented Generation) chatbot is now fully integrated and working! The system consists of:
- **Backend API**: FastAPI server with RAG capabilities (Port 8001)
- **Frontend UI**: Next.js chat interface (Port 3000)
- **Vector Database**: Qdrant with 48 indexed documents
- **LLM**: Google Gemini 2.5 Flash

## Quick Start

### 1. Start the Backend API

```bash
cd backend
python run_server.py
```

The backend will start on: `http://localhost:8001`

### 2. Start the Frontend Chat UI

```bash
cd my-book/chat-ui
npm run dev
```

The frontend will start on: `http://localhost:3000`

### 3. Access the Chatbot

Open your browser and go to: **http://localhost:3000**

You'll see a clean chat interface where you can ask questions about your documentation!

## Architecture

```
┌─────────────────┐
│   Frontend UI   │  (Next.js on port 3000)
│  localhost:3000 │
└────────┬────────┘
         │ HTTP POST /chat
         │ {"message": "user question"}
         ▼
┌─────────────────┐
│  Backend API    │  (FastAPI on port 8001)
│  localhost:8001 │
└────────┬────────┘
         │
    ┌────┴──────┐
    │           │
    ▼           ▼
┌─────────┐ ┌──────────┐
│ Qdrant  │ │  Gemini  │
│  Vector │ │   LLM    │
│Database │ │  2.5     │
└─────────┘ └──────────┘
```

## API Endpoints

### Backend Endpoints (Port 8001)

1. **Chat Endpoint** - Simple chat interface
   - URL: `POST /chat`
   - Request: `{"message": "your question"}`
   - Response: `{"answer": "AI response"}`

2. **Query Endpoint** - Detailed query with sources
   - URL: `POST /api/v1/query`
   - Request: `{"query": "your question", "top_k": 5}`
   - Response: Includes answer, sources, confidence, response time

3. **Health Check**
   - URL: `GET /api/v1/health`
   - Response: Service health status

4. **Query Stats**
   - URL: `GET /api/v1/query/stats`
   - Response: Collection statistics (48 documents indexed)

5. **API Documentation**
   - URL: `GET /api/v1/docs`
   - Interactive Swagger UI documentation

## Configuration Files

### Backend Configuration (backend/.env)
```env
COHERE_API_KEY=<your-cohere-key>
QDRANT_URL=<your-qdrant-url>
QDRANT_API_KEY=<your-qdrant-key>
GEMINI_API_KEY=<your-gemini-key>
LLM_MODEL_NAME=gemini-2.5-flash
DOCS_DIRECTORY=my-book/docs/
```

### Frontend Configuration (my-book/chat-ui/.env.local)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

## Features

### Current Features ✅
- Real-time chat interface
- Context-aware responses using RAG
- Automatic source attribution
- Error handling and loading states
- Auto-scroll to latest messages
- Responsive design with Tailwind CSS
- Accessibility features (ARIA labels, roles)

### What the Chatbot Can Do
- Answer questions about your documentation (48 documents)
- Provide contextual information about humanoid robotics
- Reference specific sources in its responses
- Handle follow-up questions
- Maintain conversation context

## Example Queries

Try asking:
- "What is a humanoid robot?"
- "What are the core principles of humanoid robotics?"
- "How does AI-powered perception work in robots?"
- "What are the ethical guidelines for humanoid robots?"
- "What are the positive applications of humanoid robots?"

## Technical Stack

### Backend
- **Framework**: FastAPI (Python)
- **Embeddings**: Cohere embed-multilingual-v2.0 (768 dimensions)
- **Vector DB**: Qdrant Cloud
- **LLM**: Google Gemini 2.5 Flash
- **Dependencies**: See `backend/requirements.txt`

### Frontend
- **Framework**: Next.js 14 (React)
- **Styling**: Tailwind CSS
- **Language**: TypeScript
- **Components**: Modular React components
- **Dependencies**: See `my-book/chat-ui/package.json`

## Component Structure

### Frontend Components
```
my-book/chat-ui/
├── app/
│   ├── page.tsx           # Main chat page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/
│   ├── ChatContainer.tsx  # Main chat container
│   ├── MessageList.tsx    # Message display list
│   ├── ChatMessage.tsx    # Individual message
│   ├── InputArea.tsx      # Message input
│   └── LoadingSpinner.tsx # Loading indicator
├── lib/
│   └── api.ts            # API client
└── types/
    └── chat.ts           # TypeScript types
```

### Backend Structure
```
backend/
├── src/
│   ├── api/              # API endpoints
│   ├── services/         # Business logic
│   ├── models/           # Data models
│   ├── clients/          # External clients
│   └── config/           # Configuration
├── run_server.py         # Server entry point
└── .env                  # Environment variables
```

## Troubleshooting

### Backend won't start
- Check if port 8001 is available
- Verify all API keys in `backend/.env`
- Ensure Python dependencies are installed: `pip install -r requirements.txt`

### Frontend won't connect to backend
- Verify backend is running on port 8001
- Check `my-book/chat-ui/.env.local` has correct URL
- Ensure CORS is enabled (already configured in backend)

### API key errors
- **Gemini 403 error**: API key leaked or invalid - generate new key
- **Cohere errors**: Check COHERE_API_KEY in .env
- **Qdrant errors**: Verify QDRANT_URL and QDRANT_API_KEY

### No responses or empty responses
- Check if documents are ingested: `GET /api/v1/query/stats`
- Should show 48 documents
- If empty, run ingestion: `cd backend && python run_ingestion.py`

## Performance

- **Document Collection**: 48 documents indexed
- **Embedding Model**: 768-dimensional vectors
- **Average Response Time**: 3-5 seconds (first query may be slower)
- **Similarity Threshold**: 0.7 (configurable)
- **Top-K Retrieval**: 5 documents (configurable)

## Security Notes

- ⚠️ Never commit `.env` files to git (already in .gitignore)
- ⚠️ API keys are sensitive - keep them secure
- ⚠️ Backend uses `override=True` to prevent system env var conflicts
- ✅ CORS is properly configured for localhost development

## Next Steps

### Enhancements You Could Add
1. **Conversation History**: Store chat history in database
2. **User Authentication**: Add user login/signup
3. **Multiple Chat Sessions**: Support multiple conversation threads
4. **Feedback System**: Allow users to rate responses
5. **Export Chat**: Download conversation as PDF/text
6. **Voice Input**: Add speech-to-text capability
7. **Code Highlighting**: Better formatting for code snippets
8. **File Upload**: Allow users to upload documents for querying
9. **Analytics Dashboard**: Track usage and popular queries
10. **Mobile App**: Create React Native or Flutter version

## Support

If you encounter issues:
1. Check both server logs (backend and frontend terminals)
2. Verify API endpoints with curl or Postman
3. Check browser console for frontend errors
4. Review API documentation at `http://localhost:8001/api/v1/docs`

## Status

✅ Backend API: Running on port 8001
✅ Frontend UI: Running on port 3000
✅ Vector Database: 48 documents indexed
✅ LLM Integration: Gemini 2.5 Flash working
✅ Full Integration: Tested and verified

**Your chatbot is production-ready!** 🎉
