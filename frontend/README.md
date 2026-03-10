# Discourse Intelligence Engine Frontend

This `frontend` project is a standalone React + TypeScript + Vite app for the Discourse Intelligence Engine. It is designed to be deployed independently from the backend and communicates with it over HTTP APIs.

The UI exposes two main analysis modes:

- **Character Arc Explorer** – per-character analysis of narrative arcs, backed by `document_arcs.json` and a Mermaid (`.mmd`) diagram.
- **Discourse Assumption Analyzer** – highlights hidden assumptions, hidden agendas, and logical fallacies with color/opacity encodings and a Mermaid diagram.

## Getting started

```bash
cd frontend
npm install
npm run dev
```

Then open the printed local URL (typically `http://localhost:5173`) in your browser.

## API configuration

The frontend can talk to either:

- a **local FastAPI backend** (Render / your own server), or
- the **Hugging Face Space** (Gradio app) that wraps the same engine.

Both are controlled with Vite environment variables.

### Option A – Local FastAPI backend

Configure `VITE_API_BASE_URL` to point at your HTTP API:

- **Local development**: create a `.env` file in the `frontend` directory:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

- **Production**: set `VITE_API_BASE_URL` in your hosting provider&apos;s environment variables (Netlify, Vercel, etc.) to the public URL of your backend.

If `VITE_GRADIO_SPACE` is **not** set (see below), the frontend will use this base URL and call the FastAPI endpoints directly.

### Option B – Hugging Face backend (Gradio Space)

To use the deployed Hugging Face Space as the backend (instead of your own server), set:

```bash
VITE_GRADIO_SPACE=mutasim-rehman/discourse
```

When this variable is set, `src/api/client.ts` will:

- connect to the Space via `@gradio/client`, and
- call the Gradio functions:
  - `/_toggle_inputs`
  - `/analyze_discourse`
  - `/analyze_character_arcs`

For **private Spaces**, also set an access token:

```bash
VITE_HF_TOKEN=hf_xxx_your_token_here
```

Recommended token scopes:

- Inference → **Make calls to Inference Providers**
- (Optional, for private Spaces) Repositories → **Read access to contents of selected repos** for the Space repo.

If `VITE_GRADIO_SPACE` is set, `VITE_API_BASE_URL` is ignored and all analysis requests go through Hugging Face.

### Expected endpoints

The frontend currently uses two POST endpoints:

- `POST /api/character-arcs/analyze`
- `POST /api/analysis/discourse`

These are defined in `src/api/client.ts` with TypeScript request/response types. The backend should accept a JSON payload with:

- `sourceType`: `'raw_text' | 'file' | 'youtube'`
- `rawText?`: original text when `sourceType === 'raw_text'`
- `fileName?`: name of an uploaded `.txt` file when `sourceType === 'file'`
- `youtubeUrl?`: YouTube URL when `sourceType === 'youtube'`

and respond with structured results including the original text, highlight segments, and Mermaid (`.mmd`) strings.

## Feature overview

- **Shared input flow** (`src/components/InputModeSelector.tsx`):
  - Paste text
  - Upload `.txt` file
  - YouTube URL

- **Discourse Assumption Analyzer** (`src/features/analysis/AssumptionAnalyzerPage.tsx`):
  - Calls `analyzeDiscourse` from `src/api/client.ts`.
  - Renders annotated text using `ColoredTextView` with:
    - distinct colors per family (assumption, agenda, fallacy)
    - opacity mapped to confidence.
  - Shows a Mermaid diagram via `DiagramView`.

- **Character Arc Explorer** (`src/features/characterArcs/CharacterArcExplorerPage.tsx`):
  - Calls `analyzeCharacterArcs` from `src/api/client.ts`.
  - Shows a sidebar of characters and per-character highlighted arcs in the text.
  - Allows downloading the returned `document_arcs.json` blob.
  - Renders the returned Mermaid diagram.

Routing is configured in `src/App.tsx` using `react-router-dom`:

- `/` – landing page to choose between the two modes.
- `/character-arcs` – Character Arc Explorer.
- `/assumption-analysis` – Discourse Assumption Analyzer.

