---
id: 11
title: "Next.js Chat UI Specification"
stage: "spec"
date: "2025-12-20"
surface: "agent"
model: "Claude Sonnet 4.5"
feature: "1-nextjs-chat-ui"
branch: "1-nextjs-chat-ui"
user: "user"
command: "/sp.specify"
labels: ["frontend", "chat-ui", "nextjs", "specification"]
links:
  spec: "specs/1-nextjs-chat-ui/spec.md"
  ticket: null
  adr: null
  pr: null
files:
  - "specs/1-nextjs-chat-ui/spec.md"
  - "specs/1-nextjs-chat-ui/checklists/requirements.md"
  - "history/prompts/1-nextjs-chat-ui/11-nextjs-chat-ui-spec.spec.prompt.md"
tests: []
---

# Prompt History Record: Next.js Chat UI Specification

## User Prompt
```
This is the specification of  **simple chat UI using Next.js (App Router)** and integrate it with an **already existing FastAPI RAG backend** that uses **Qdrant as a vector database** and an **LLM for response generation**.

Your focus is **frontend implementation and integration only**.


### Project Context

- The frontend project root folder is named **`my-book`**
- Inside `my-book`, create a new folder named **`chat-ui`**
- Use **Next.js (App Router)** inside `chat-ui`
- A **FastAPI backend already exists and is running**

### Backend Characteristics (DO NOT REIMPLEMENT)

- Endpoint: **POST `/chat`**
- Input:
```json
{
  "message": "User query"
}
Output:

json
Copy code
{
  "answer": "LLM generated response using Qdrant context"
}
Backend responsibilities:

Accept user query

Retrieve contextual chunks from Qdrant

Combine query + context

Send to LLM

Return generated response

Do not modify or recreate backend logic

Chatbot Requirements
Simple chatbot UI with:

Input box

Send button

Chat message list (user + assistant)

User query flow:

UI → FastAPI /chat → UI

Frontend must not:

Call Qdrant directly

Call any LLM APIs

Import OpenAI / Gemini / Cohere SDKs

Contain any API keys

Communication happens only via FastAPI

Include:

Loading state ("Thinking…")

Disabled input/button while waiting

Basic error handling

UI must be:

Minimal

Clean

Beginner-friendly

No heavy styling libraries
```

## Assistant Response
Created a complete specification for the Next.js Chat UI integration feature, including:
- Feature overview and project context
- User scenarios and testing flows
- Functional and non-functional requirements
- Success criteria
- Assumptions and dependencies
- Clear scope definition

The specification was created in specs/1-nextjs-chat-ui/spec.md with a quality checklist in specs/1-nextjs-chat-ui/checklists/requirements.md.

## Outcome
Specification successfully created and ready for planning phase (/sp.plan).

## Evaluation
The specification meets all quality criteria with clear requirements, measurable success criteria, and well-defined scope boundaries.