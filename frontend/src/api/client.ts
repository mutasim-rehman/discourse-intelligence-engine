export type SourceType = 'raw_text' | 'file' | 'youtube'

export interface CommonRequestPayload {
  sourceType: SourceType
  rawText?: string
  fileName?: string
  youtubeUrl?: string
}

export interface CharacterSummary {
  id: string
  name: string
  description?: string
}

export interface CharacterArc {
  characterId: string
  arcId: string
  label: string
  startIndex: number
  endIndex: number
  confidence: number
  colorFamily?: string
}

/** Single point on a character arc timeline (from document_arcs.json). */
export interface DocumentArcPoint {
  document_id: string
  scene_id?: string | null
  turn_index?: number | null
  position: number
  metrics?: Record<string, unknown>
}

/** Notable event in an arc (pivot, turning point, etc.). */
export interface DocumentArcEvent {
  position: number
  label: string
  details?: Record<string, unknown>
}

/** Per-character arc from document_arcs.json. */
export interface DocumentCharacterArc {
  character_id: string
  display_name?: string | null
  points: DocumentArcPoint[]
  events: DocumentArcEvent[]
}

/** Relationship arc (pair of characters). */
export interface DocumentRelationshipArc {
  pair: [string, string]
  points: unknown[]
  events: DocumentArcEvent[]
}

/** Shape of document_arcs.json returned by the API. */
export interface DocumentArcsJson {
  characters: Record<string, DocumentCharacterArc>
  relationships?: Record<string, DocumentRelationshipArc>
}

export interface CharacterArcsResponse {
  characters: CharacterSummary[]
  arcs: CharacterArc[]
  documentArcsJson: DocumentArcsJson | unknown
  mermaidMmd: string | null
  originalText: string
  translatedText?: string | null
  originalTextLanguage?: string | null
  nativeIntentStronger?: boolean | null
  youtubeVideo?: YouTubeVideoMetadata | null
}

export type AnalysisFamily = 'assumption' | 'agenda' | 'fallacy'

export interface AnalysisSegment {
  startIndex: number
  endIndex: number
  text: string
  family: AnalysisFamily
  subfamily?: string
  confidence: number
}

export interface ColorLegendEntry {
  family: AnalysisFamily
  subfamily?: string
  color: string
}

export interface YouTubeVideoMetadata {
  videoId: string
  title?: string | null
  thumbnailUrl?: string | null
}

export interface DiscourseAnalysisResponse {
  segments: AnalysisSegment[]
  colorLegend: ColorLegendEntry[]
  mermaidMmd: string | null
  originalText: string
  translatedText?: string | null
  originalTextLanguage?: string | null
  nativeIntentStronger?: boolean | null
  youtubeVideo?: YouTubeVideoMetadata | null
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined
const GRADIO_SPACE = import.meta.env.VITE_GRADIO_SPACE as string | undefined
const HF_TOKEN = import.meta.env.VITE_HF_TOKEN as string | undefined

function getBaseUrl() {
  return API_BASE_URL ?? 'http://localhost:8000'
}

function useGradio() {
  return typeof GRADIO_SPACE === 'string' && GRADIO_SPACE.trim().length > 0
}

const DEFAULT_COLOR_LEGEND: ColorLegendEntry[] = [
  { family: 'assumption', subfamily: 'assumption', color: '#facc15' },
  { family: 'agenda', subfamily: undefined, color: '#38bdf8' },
  { family: 'fallacy', subfamily: undefined, color: '#fb7185' },
]

let gradioClient: Awaited<ReturnType<typeof import('@gradio/client').Client.connect>> | null = null

async function getGradioClient() {
  if (gradioClient) return gradioClient
  const { Client } = await import('@gradio/client')
  const options: Record<string, unknown> = {}
  if (typeof HF_TOKEN === 'string' && HF_TOKEN.trim()) {
    // `hf_token` is supported by @gradio/client at runtime but not yet in its TS types.
    ;(options as { hf_token?: string }).hf_token = HF_TOKEN.trim()
  }
  gradioClient = await Client.connect(GRADIO_SPACE!.trim(), options as any)
  return gradioClient
}

function toGradioPayload(payload: CommonRequestPayload) {
  const sourceType = payload.sourceType === 'youtube' ? 'YouTube' : 'Raw text'
  const rawText = payload.rawText ?? ''
  const youtubeUrl = payload.youtubeUrl ?? ''
  return { source_type: sourceType, raw_text: rawText, youtube_url: youtubeUrl }
}

async function handleJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text().catch(() => '')
    throw new Error(
      message || `API request failed with status ${response.status}`,
    )
  }
  return (await response.json()) as T
}

export async function analyzeCharacterArcs(
  payload: CommonRequestPayload,
): Promise<CharacterArcsResponse> {
  if (useGradio()) {
    const client = await getGradioClient()
    const result = await client.predict('/analyze_character_arcs', toGradioPayload(payload))
    const data = result?.data
    const [arcsPayload] = Array.isArray(data) ? data : []
    const json = (arcsPayload as Record<string, unknown>) ?? {}
    if (json.error && typeof json.error === 'string') {
      throw new Error(json.error)
    }
    if (!data || !Array.isArray(data) || data.length < 2) {
      throw new Error('Invalid response from Gradio API')
    }
    const characters = Object.entries((json.characters as Record<string, { display_name?: string }>) ?? {}).map(
      ([id, arc]) => ({ id, name: arc?.display_name ?? id, description: undefined }),
    )
    return {
      characters,
      arcs: [],
      documentArcsJson: json,
      mermaidMmd: (json.mermaidMmd as string) ?? null,
      originalText: (json.originalText as string) ?? '',
      translatedText: (json.translatedText as string | null) ?? null,
      originalTextLanguage: (json.originalTextLanguage as string | null) ?? null,
      nativeIntentStronger: null,
      youtubeVideo: null,
    }
  }

  const response = await fetch(`${getBaseUrl()}/api/character-arcs/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return handleJsonResponse<CharacterArcsResponse>(response)
}

export async function analyzeDiscourse(
  payload: CommonRequestPayload,
): Promise<DiscourseAnalysisResponse> {
  if (useGradio()) {
    const client = await getGradioClient()
    const result = await client.predict('/analyze_discourse', toGradioPayload(payload))
    const data = result?.data
    const [json] = Array.isArray(data) ? data : []
    const obj = (json as Record<string, unknown>) ?? {}
    if (obj.error && typeof obj.error === 'string') {
      throw new Error(obj.error)
    }
    if (!data || !Array.isArray(data) || data.length < 3) {
      throw new Error('Invalid response from Gradio API')
    }
    return {
      segments: (obj.segments as AnalysisSegment[]) ?? [],
      colorLegend: (obj.colorLegend as ColorLegendEntry[]) ?? DEFAULT_COLOR_LEGEND,
      mermaidMmd: (obj.mermaidMmd as string) ?? null,
      originalText: (obj.originalText as string) ?? '',
      translatedText: (obj.translatedText as string | null) ?? null,
      originalTextLanguage: (obj.originalTextLanguage as string | null) ?? null,
      nativeIntentStronger: (obj.nativeIntentStronger as boolean | null) ?? null,
      youtubeVideo: (obj.youtubeVideo as YouTubeVideoMetadata | null) ?? null,
    }
  }

  const response = await fetch(`${getBaseUrl()}/api/analysis/discourse`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return handleJsonResponse<DiscourseAnalysisResponse>(response)
}

