import { ChangeEvent, useRef, useState } from 'react'

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
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

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

  function loadTextFile(nextFile: File) {
    if (!nextFile.name.toLowerCase().endsWith('.txt')) {
      setFile(undefined)
      onChange(null, false)
      return
    }
    setFile(nextFile)
    const reader = new FileReader()
    reader.onload = () => {
      const contents = (reader.result as string) ?? ''
      const value: InputModeValue = { sourceType: 'raw_text', rawText: contents }
      onChange(value, contents.trim().length >= minTextLength)
    }
    reader.onerror = () => {
      setFile(undefined)
      onChange(null, false)
    }
    reader.readAsText(nextFile, 'utf-8')
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const nextFile = e.target.files?.[0]
    if (!nextFile) {
      setFile(undefined)
      emitChange(mode, rawText, undefined, youtubeUrl)
      return
    }
    loadTextFile(nextFile)
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
            <label>Upload a .txt file</label>
            <div
              className={isDragging ? 'dropzone dragging' : 'dropzone'}
              role="button"
              tabIndex={0}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
              }}
              onDragEnter={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault()
                setIsDragging(false)
                const dropped = e.dataTransfer.files?.[0]
                if (dropped) loadTextFile(dropped)
              }}
            >
              <div className="dropzone-title">
                Drag and drop your file here
              </div>
              <div className="dropzone-sub">
                or click to choose a <span className="mono">.txt</span> file
              </div>
              {file && (
                <div className="dropzone-file">
                  Loaded: <strong>{file.name}</strong>
                </div>
              )}
            </div>

            <input
              ref={fileInputRef}
              id="file-input"
              type="file"
              accept=".txt,text/plain"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />

            <div className="field-help">
              File contents are read in your browser and sent as text for analysis.
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

