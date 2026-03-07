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
  youtubeVideo?: YouTubeVideoMetadata | null
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined

function getBaseUrl() {
  return API_BASE_URL ?? 'http://localhost:8000'
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
  const response = await fetch(`${getBaseUrl()}/api/analysis/discourse`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return handleJsonResponse<DiscourseAnalysisResponse>(response)
}

