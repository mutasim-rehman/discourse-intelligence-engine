import { ChangeEvent, useState } from 'react'

export type SourceType = 'raw_text' | 'file' | 'youtube'

export interface InputModeValue {
  sourceType: SourceType
  rawText?: string
  file?: File
  youtubeUrl?: string
}

interface InputModeSelectorProps {
  onChange: (value: InputModeValue | null, isValid: boolean) => void
}

export function InputModeSelector({ onChange }: InputModeSelectorProps) {
  const [mode, setMode] = useState<SourceType>('raw_text')
  const [rawText, setRawText] = useState('')
  const [file, setFile] = useState<File | undefined>()
  const [youtubeUrl, setYoutubeUrl] = useState('')

  const minTextLength = 40

  function isYoutubeUrl(value: string) {
    if (!value.trim()) return false
    try {
      const url = new URL(value)
      return (
        url.hostname.includes('youtube.com') ||
        url.hostname.includes('youtu.be')
      )
    } catch {
      return false
    }
  }

  function emitChange(
    nextMode: SourceType,
    nextRawText: string,
    nextFile: File | undefined,
    nextYoutubeUrl: string,
  ) {
    let value: InputModeValue | null = null
    let valid = false

    if (nextMode === 'raw_text') {
      value = { sourceType: 'raw_text', rawText: nextRawText.trim() }
      valid = (value.rawText?.length ?? 0) >= minTextLength
    } else if (nextMode === 'file') {
      if (nextFile) {
        value = { sourceType: 'file', file: nextFile }
        valid = true
      }
    } else if (nextMode === 'youtube') {
      value = { sourceType: 'youtube', youtubeUrl: nextYoutubeUrl.trim() }
      valid = isYoutubeUrl(nextYoutubeUrl)
    }

    onChange(value, valid)
  }

  function handleModeChange(nextMode: SourceType) {
    setMode(nextMode)
    emitChange(nextMode, rawText, file, youtubeUrl)
  }

  function handleTextChange(e: ChangeEvent<HTMLTextAreaElement>) {
    const next = e.target.value
    setRawText(next)
    emitChange(mode, next, file, youtubeUrl)
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const nextFile = e.target.files?.[0]
    if (nextFile && !nextFile.name.toLowerCase().endsWith('.txt')) {
      setFile(undefined)
      onChange(null, false)
      return
    }
    setFile(nextFile)
    emitChange(mode, rawText, nextFile, youtubeUrl)
  }

  function handleYoutubeChange(e: ChangeEvent<HTMLInputElement>) {
    const next = e.target.value
    setYoutubeUrl(next)
    emitChange(mode, rawText, file, next)
  }

  return (
    <div className="input-mode-root">
      <div className="input-mode-tabs">
        <button
          type="button"
          className={mode === 'raw_text' ? 'tab active' : 'tab'}
          onClick={() => handleModeChange('raw_text')}
        >
          Paste text
        </button>
        <button
          type="button"
          className={mode === 'file' ? 'tab active' : 'tab'}
          onClick={() => handleModeChange('file')}
        >
          Upload .txt file
        </button>
        <button
          type="button"
          className={mode === 'youtube' ? 'tab active' : 'tab'}
          onClick={() => handleModeChange('youtube')}
        >
          YouTube link
        </button>
      </div>

      <div className="input-mode-panel">
        {mode === 'raw_text' && (
          <div className="field-group">
            <label htmlFor="raw-text">Paste or type your text</label>
            <textarea
              id="raw-text"
              className="text-area"
              rows={10}
              value={rawText}
              onChange={handleTextChange}
              placeholder="Paste the discourse or narrative you want to analyze..."
            />
            <div className="field-help">
              Minimum {minTextLength} characters for a meaningful analysis.
            </div>
          </div>
        )}

        {mode === 'file' && (
          <div className="field-group">
            <label htmlFor="file-input">Upload a .txt file</label>
            <input
              id="file-input"
              type="file"
              accept=".txt,text/plain"
              onChange={handleFileChange}
            />
            <div className="field-help">
              Only plain text files are supported for now.
            </div>
          </div>
        )}

        {mode === 'youtube' && (
          <div className="field-group">
            <label htmlFor="youtube-url">YouTube URL</label>
            <input
              id="youtube-url"
              type="url"
              value={youtubeUrl}
              onChange={handleYoutubeChange}
              placeholder="https://www.youtube.com/watch?v=..."
            />
            <div className="field-help">
              We will rely on the backend to resolve and transcribe the video.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

