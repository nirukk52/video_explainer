# Director Chat - Architecture Documentation

This document provides a detailed architecture overview of the Director Chat frontend, which serves as the web UI for the UGC Ad Factory (Shorts Factory) system.

## Overview

Director Chat is a **Next.js 16** application built on the [Vercel Chat SDK](https://chat-sdk.dev) that provides:
- AI-powered chat interface for creating short-form videos
- Integration with the Shorts Factory pipeline via MCP (Model Context Protocol)
- Human-in-the-loop approval gates for quality control
- Artifact management (scripts, documents, code)
- User authentication and chat history persistence

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DIRECTOR CHAT SYSTEM                               │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND                                     │
│                              (director-chat/)                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │   Chat Page      │  │   Auth Pages     │  │   API Routes     │              │
│  │  /chat/[id]      │  │  /login          │  │  /api/chat       │              │
│  │  / (home)        │  │  /register       │  │  /api/history    │              │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘              │
│           │                     │                     │                         │
│           └─────────────────────┼─────────────────────┘                         │
│                                 │                                               │
│  ┌──────────────────────────────┴────────────────────────────────────────────┐  │
│  │                          COMPONENTS LAYER                                 │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │   Chat      │  │  Artifact   │  │  Messages   │  │  Sidebar    │      │  │
│  │  │ Component   │  │  Panel      │  │  List       │  │  History    │      │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │  │
│  │         │                │                │                │              │  │
│  │  ┌──────┴────────────────┴────────────────┴────────────────┴──────┐      │  │
│  │  │                    SHARED UI COMPONENTS                        │      │  │
│  │  │  Button, Input, Dialog, Tooltip, Card, ScrollArea...          │      │  │
│  │  │              (shadcn/ui + Radix UI primitives)                 │      │  │
│  │  └────────────────────────────────────────────────────────────────┘      │  │
│  │                                                                           │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           LIB / SERVICES LAYER                            │  │
│  ├───────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │  │
│  │  │  lib/director/  │  │    lib/ai/      │  │    lib/db/      │           │  │
│  │  │  MCP Client     │  │  AI SDK Tools   │  │  Drizzle ORM    │           │  │
│  │  │  + Tools        │  │  + Prompts      │  │  + Queries      │           │  │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │  │
│  │           │                    │                    │                     │  │
│  └───────────┼────────────────────┼────────────────────┼─────────────────────┘  │
│              │                    │                    │                        │
└──────────────┼────────────────────┼────────────────────┼────────────────────────┘
               │                    │                    │
               ▼                    ▼                    ▼
┌──────────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐
│   director-mcp       │  │  Vercel AI       │  │   Neon Postgres              │
│   (HTTP :8001)       │  │  Gateway         │  │   (Serverless DB)            │
│                      │  │                  │  │                              │
│  - Factory tools     │  │  - xAI (Grok)    │  │  - User, Chat, Message       │
│  - Analysis skills   │  │  - OpenAI        │  │  - Document, Vote            │
│  - Eval/scoring      │  │  - Anthropic     │  │  - Suggestion, Stream        │
└──────────────────────┘  └──────────────────┘  └──────────────────────────────┘
```

## Core Functionalities

### 1. AI Chat Interface

The primary interface for interacting with the Shorts Factory pipeline.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            CHAT FLOW                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

User Message → Chat Component → API Route (/api/chat) → AI SDK streamText()
                                                              │
                                    ┌─────────────────────────┼───────────────┐
                                    │                         │               │
                                    ▼                         ▼               ▼
                              Built-in Tools          Director Tools     Response
                              - createDocument        - createShortsProject
                              - updateDocument        - viewScript
                              - getWeather            - approveGate
                              - requestSuggestions    - analyzeScriptHook
                                                      - ... (12 total)
```

**Key Features:**
- Real-time streaming responses via SSE
- Tool calling with human approval flow
- Multi-model support (xAI Grok, OpenAI, Anthropic)
- Message persistence to PostgreSQL
- Resumable streams (Redis-backed)

### 2. Director Tools (Shorts Factory Integration)

12 specialized tools for video production:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DIRECTOR TOOLS ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                        lib/director/ Module                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐    │
│  │       client.ts                 │    │       tools.ts                  │    │
│  │  (HTTP Client to MCP)           │    │  (AI SDK Tool Definitions)      │    │
│  ├─────────────────────────────────┤    ├─────────────────────────────────┤    │
│  │                                 │    │                                 │    │
│  │  callDirectorTool<T>(tool, p)   │◄───│  createShortsProject            │    │
│  │                                 │    │  getStatus                      │    │
│  │  // Factory API                 │    │  approveGate                    │    │
│  │  createProject()                │    │  rejectGate                     │    │
│  │  getProjectStatus()             │    │  viewScript                     │    │
│  │  approveStage()                 │    │  viewArtifacts                  │    │
│  │  rejectStage()                  │    │  checkRenderReady               │    │
│  │  getArtifacts()                 │    │                                 │    │
│  │  getScript()                    │    │  // Analysis                    │    │
│  │  getRenderManifest()            │    │  analyzeScriptHook              │    │
│  │                                 │    │  analyzeScriptBeats             │    │
│  │  // Analysis API                │    │  analyzeScriptRetention         │    │
│  │  analyzeHook()                  │    │                                 │    │
│  │  generateBeatSheet()            │    │  // Eval                        │    │
│  │  validateRetention()            │    │  scoreCompletedTemplate         │    │
│  │                                 │    │  findSimilarWinners             │    │
│  │  // Eval API                    │    │                                 │    │
│  │  scoreTemplate()                │    │  // Export                      │    │
│  │  getSimilarWinners()            │    │  directorTools = { ... }        │    │
│  │                                 │    │                                 │    │
│  └─────────────────────────────────┘    └─────────────────────────────────┘    │
│                 │                                        │                      │
│                 │                                        │                      │
│                 ▼                                        ▼                      │
│        HTTP POST to MCP                      Injected into AI SDK               │
│    /mcp/v1/tools/{tool_name}                 via route.ts                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │    director-mcp       │
                          │    (Python FastMCP)   │
                          │    Port 8001          │
                          └───────────────────────┘
```

**Tool Categories:**

| Category | Tools | Purpose |
|----------|-------|---------|
| **Factory** | createShortsProject, getStatus, approveGate, rejectGate, viewScript, viewArtifacts, checkRenderReady | Project lifecycle management |
| **Analysis** | analyzeScriptHook, analyzeScriptBeats, analyzeScriptRetention | Script quality analysis |
| **Eval** | scoreCompletedTemplate, findSimilarWinners | Template scoring and RAG |

### 3. Artifact System

Documents, code, and sheets can be created/edited inline.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ARTIFACT SYSTEM                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                           Artifact Types                                        │
├────────────────┬───────────────────┬──────────────────┬───────────────────────┤
│    text        │      code         │     image        │       sheet           │
│  (Markdown)    │    (Python)       │    (Generated)   │      (CSV)            │
├────────────────┴───────────────────┴──────────────────┴───────────────────────┤
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                      Artifact UI (Split View)                            │ │
│  ├─────────────────────────────────┬────────────────────────────────────────┤ │
│  │                                 │                                        │ │
│  │    Chat Messages Panel          │         Artifact Editor Panel          │ │
│  │    (Left side, 400px)           │         (Right side, remaining)        │ │
│  │                                 │                                        │ │
│  │  - ArtifactMessages             │  - TextEditor (ProseMirror)            │ │
│  │  - MultimodalInput              │  - CodeEditor (CodeMirror)             │ │
│  │                                 │  - SheetEditor (react-data-grid)       │ │
│  │                                 │  - ImageEditor (canvas)                │ │
│  │                                 │                                        │ │
│  │                                 │  + Version history                     │ │
│  │                                 │  + Diff view                           │ │
│  │                                 │  + Toolbar actions                     │ │
│  │                                 │                                        │ │
│  └─────────────────────────────────┴────────────────────────────────────────┘ │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘

Artifact Lifecycle:
1. AI calls createDocument tool → New artifact created in DB
2. User sees artifact panel slide in from the right
3. User can edit content directly
4. AI can call updateDocument to modify
5. Version history tracks all changes
```

### 4. Authentication System

NextAuth.js-based auth with regular users and guest mode.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                       │
│  │  /login     │     │ /register   │     │  Guest      │                       │
│  │  Page       │     │  Page       │     │  Login      │                       │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                       │
│         │                   │                   │                               │
│         └───────────────────┼───────────────────┘                               │
│                             │                                                   │
│                             ▼                                                   │
│                   ┌─────────────────────┐                                       │
│                   │     NextAuth.js     │                                       │
│                   │   (next-auth@beta)  │                                       │
│                   ├─────────────────────┤                                       │
│                   │                     │                                       │
│                   │  Providers:         │                                       │
│                   │  - Credentials      │──────▶ Password check (bcrypt-ts)     │
│                   │  - Guest            │──────▶ Auto-create guest user         │
│                   │                     │                                       │
│                   │  Callbacks:         │                                       │
│                   │  - jwt → add type   │                                       │
│                   │  - session → merge  │                                       │
│                   │                     │                                       │
│                   └──────────┬──────────┘                                       │
│                              │                                                  │
│                              ▼                                                  │
│                   ┌─────────────────────┐                                       │
│                   │   User Table (DB)   │                                       │
│                   │   - id (uuid)       │                                       │
│                   │   - email           │                                       │
│                   │   - password (hash) │                                       │
│                   └─────────────────────┘                                       │
│                                                                                 │
│  User Types:                                                                    │
│  - "regular": Full access, registered with email/password                       │
│  - "guest": Limited access, auto-created for quick trials                       │
│                                                                                 │
│  Entitlements (per user type):                                                  │
│  - maxMessagesPerDay: Rate limiting per 24h                                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 5. Database Layer

PostgreSQL (Neon Serverless) with Drizzle ORM.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐              │
│  │    User      │        │    Chat      │        │  Message_v2  │              │
│  ├──────────────┤        ├──────────────┤        ├──────────────┤              │
│  │ id (PK)      │◄───────│ userId (FK)  │        │ id (PK)      │              │
│  │ email        │        │ id (PK)      │◄───────│ chatId (FK)  │              │
│  │ password     │        │ title        │        │ role         │              │
│  └──────────────┘        │ createdAt    │        │ parts (JSON) │              │
│         │                │ visibility   │        │ attachments  │              │
│         │                └──────────────┘        │ createdAt    │              │
│         │                       │                └──────────────┘              │
│         │                       │                                               │
│         │                       │                ┌──────────────┐              │
│         │                       │                │   Vote_v2    │              │
│         │                       └───────────────▶├──────────────┤              │
│         │                                        │ chatId (FK)  │              │
│         │                                        │ messageId(FK)│              │
│         │                                        │ isUpvoted    │              │
│         │                                        └──────────────┘              │
│         │                                                                       │
│         │                ┌──────────────┐        ┌──────────────┐              │
│         │                │   Document   │        │  Suggestion  │              │
│         └───────────────▶├──────────────┤        ├──────────────┤              │
│                          │ id           │◄───────│ documentId   │              │
│                          │ userId (FK)  │        │ userId (FK)  │              │
│                          │ title        │        │ originalText │              │
│                          │ content      │        │ suggestedText│              │
│                          │ kind         │        │ isResolved   │              │
│                          │ createdAt    │        └──────────────┘              │
│                          └──────────────┘                                       │
│                                                                                 │
│  ┌──────────────┐                                                               │
│  │   Stream     │  (For resumable streaming)                                    │
│  ├──────────────┤                                                               │
│  │ id (PK)      │                                                               │
│  │ chatId (FK)  │                                                               │
│  │ createdAt    │                                                               │
│  └──────────────┘                                                               │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
director-chat/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Auth route group
│   │   ├── auth.ts               # NextAuth configuration
│   │   ├── auth.config.ts        # Auth options
│   │   ├── login/page.tsx        # Login page
│   │   ├── register/page.tsx     # Registration page
│   │   └── api/auth/             # Auth API routes
│   │
│   ├── (chat)/                   # Chat route group
│   │   ├── page.tsx              # Home page (new chat)
│   │   ├── layout.tsx            # Chat layout with sidebar
│   │   ├── actions.ts            # Server actions
│   │   ├── chat/[id]/page.tsx    # Individual chat page
│   │   └── api/                  # API routes
│   │       ├── chat/route.ts     # Chat streaming endpoint
│   │       ├── history/route.ts  # Chat history
│   │       ├── document/route.ts # Document CRUD
│   │       ├── vote/route.ts     # Message voting
│   │       └── suggestions/      # AI suggestions
│   │
│   ├── layout.tsx                # Root layout
│   └── globals.css               # Global styles
│
├── artifacts/                    # Artifact type definitions
│   ├── code/                     # Python code artifact
│   │   ├── client.tsx            # Client component
│   │   └── server.ts             # Server execution
│   ├── text/                     # Markdown text artifact
│   ├── image/                    # Image artifact
│   └── sheet/                    # Spreadsheet artifact
│
├── components/                   # React components
│   ├── chat.tsx                  # Main chat component
│   ├── messages.tsx              # Message list
│   ├── message.tsx               # Individual message
│   ├── artifact.tsx              # Artifact panel
│   ├── multimodal-input.tsx      # Input with attachments
│   ├── app-sidebar.tsx           # Navigation sidebar
│   ├── sidebar-history.tsx       # Chat history list
│   ├── ai-elements/              # AI-specific UI elements
│   │   ├── tool.tsx              # Tool invocation display
│   │   ├── reasoning.tsx         # Reasoning display
│   │   ├── loader.tsx            # Loading states
│   │   └── ...
│   ├── elements/                 # Message part elements
│   └── ui/                       # shadcn/ui components
│
├── hooks/                        # React hooks
│   ├── use-artifact.ts           # Artifact state management
│   ├── use-auto-resume.ts        # Stream resumption
│   ├── use-chat-visibility.ts    # Chat visibility toggle
│   ├── use-messages.tsx          # Message list with scroll
│   └── use-mobile.ts             # Mobile detection
│
├── lib/                          # Utilities and services
│   ├── director/                 # Shorts Factory integration
│   │   ├── client.ts             # HTTP client to MCP
│   │   ├── tools.ts              # AI SDK tool definitions
│   │   └── index.ts              # Module exports
│   │
│   ├── ai/                       # AI configuration
│   │   ├── prompts.ts            # System prompts
│   │   ├── providers.ts          # Model providers
│   │   ├── models.ts             # Available models
│   │   ├── entitlements.ts       # User rate limits
│   │   └── tools/                # Built-in tools
│   │       ├── create-document.ts
│   │       ├── update-document.ts
│   │       ├── get-weather.ts
│   │       └── request-suggestions.ts
│   │
│   ├── db/                       # Database layer
│   │   ├── schema.ts             # Drizzle schema
│   │   ├── queries.ts            # DB queries
│   │   ├── migrate.ts            # Migration runner
│   │   └── migrations/           # SQL migrations
│   │
│   ├── artifacts/                # Artifact utilities
│   ├── editor/                   # Editor configurations
│   ├── constants.ts              # App constants
│   ├── errors.ts                 # Error handling
│   ├── types.ts                  # TypeScript types
│   └── utils.ts                  # Utility functions
│
├── tests/                        # Playwright E2E tests
│   ├── e2e/
│   │   ├── auth.test.ts
│   │   ├── chat.test.ts
│   │   └── api.test.ts
│   └── fixtures.ts
│
├── public/                       # Static assets
├── package.json                  # Dependencies
├── drizzle.config.ts             # Drizzle configuration
├── next.config.ts                # Next.js configuration
└── tsconfig.json                 # TypeScript configuration
```

## Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    END-TO-END REQUEST FLOW                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

User types: "Create a 30-second short about DeepSeek pricing"
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. FRONTEND (components/chat.tsx)                                               │
│                                                                                 │
│    useChat() hook → sendMessage() → POST /api/chat                              │
│    { id, message: { role: "user", parts: [...] }, selectedChatModel }           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. API ROUTE (app/(chat)/api/chat/route.ts)                                     │
│                                                                                 │
│    - Authenticate user (auth())                                                 │
│    - Check rate limits                                                          │
│    - Save user message to DB                                                    │
│    - Call streamText() with:                                                    │
│      • model: getLanguageModel(selectedChatModel)                               │
│      • system: systemPrompt (regularPrompt + artifactsPrompt)                   │
│      • tools: { ...builtInTools, ...directorTools }                             │
│      • experimental_activeTools: ["createShortsProject", "viewScript", ...]     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. AI SDK + LLM (Vercel AI Gateway)                                             │
│                                                                                 │
│    LLM decides to call: createShortsProject({ topic, duration_seconds: 30 })    │
│                                │                                                │
│                                ▼                                                │
│    Tool executor (lib/director/tools.ts):                                       │
│    - Calls createProject() from client.ts                                       │
│    - HTTP POST to http://localhost:8001/mcp/v1/tools/factory_create_project     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. DIRECTOR MCP SERVER (director-mcp/src/server.py)                             │
│                                                                                 │
│    factory_create_project():                                                    │
│    - Creates ShortsFactoryProject                                               │
│    - Runs pipeline (generates script)                                           │
│    - Stops at script_approval gate                                              │
│    - Returns: { project_id, topic, status }                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. RESPONSE STREAM (back to frontend)                                           │
│                                                                                 │
│    LLM continues: "I've created project abc123. Here's the script..."           │
│    May call viewScript() to show details                                        │
│    May call analyzeScriptHook() for quality analysis                            │
│                                                                                 │
│    Stream → createUIMessageStreamResponse → SSE → Chat UI updates               │
│    Messages saved to DB on stream finish                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Technologies

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Framework** | Next.js 16 | React server components, App Router |
| **AI** | Vercel AI SDK 6.x | Streaming, tool calling, message parts |
| **UI** | shadcn/ui + Radix | Accessible component primitives |
| **Styling** | Tailwind CSS 4.x | Utility-first CSS |
| **Animation** | Framer Motion | Smooth transitions |
| **State** | SWR + Zustand | Data fetching + local state |
| **Database** | PostgreSQL (Neon) | Serverless Postgres |
| **ORM** | Drizzle | Type-safe SQL |
| **Auth** | NextAuth.js v5 | Credentials + guest auth |
| **Editor** | ProseMirror / CodeMirror | Rich text + code editing |
| **Testing** | Playwright | E2E tests |

## System Prompts

The AI assistant is configured with a Varun Mayya-style video creation persona:

```typescript
// lib/ai/prompts.ts
export const regularPrompt = `You are the Director Chat assistant for the Shorts Factory.
You help users create high-quality Varun Mayya-style short-form videos...

## Your Capabilities
1. createShortsProject - Create new video projects
2. viewScript - Review generated scripts  
3. approveGate - Approve pipeline stages
4. analyzeScriptHook - Analyze hook quality
... (12 tools total)

## Workflow
1. findSimilarWinners for inspiration
2. createShortsProject  
3. viewScript for review
4. approveGate to continue
5. scoreCompletedTemplate for evaluation
`;
```

## Running the System

```bash
# Terminal 1: Start director-mcp backend
cd director-mcp
python -m src.server --http --port 8001

# Terminal 2: Start Next.js frontend  
cd director-chat
pnpm install
pnpm db:migrate
pnpm dev

# Open http://localhost:3000
```

## Environment Variables

```bash
# .env.local
DATABASE_URL=postgres://...              # Neon Postgres connection
AUTH_SECRET=your-secret                  # NextAuth secret
DIRECTOR_MCP_URL=http://localhost:8001   # MCP server URL
AI_GATEWAY_API_KEY=...                   # Vercel AI Gateway (non-Vercel deploys)
REDIS_URL=...                            # Optional: resumable streams
```
