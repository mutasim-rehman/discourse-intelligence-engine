## Discourse Intelligence Engine V7 – Multi-Language Engine

V7 introduces dual-layer multi-language support: a **Translation Bridge** that feeds English text to the V1–V6 engines, and a **Native Layer** for cultural/authority signals when the original is non-English.

---

### 1. Design Principle

V1–V6 remain English-only. The Translation Bridge sits in front and produces the English stream; the Native Layer runs in parallel when translation is used.

---

### 2. Architecture

```text
Input (YouTube / Raw Text / File)
    ↓
V7 Translation Bridge
  ├── Language Detection (langdetect)
  ├── Translation to English (YouTube: transcript.translate; Text/File: googletrans)
  └── Native Layer (native_signals.py) when original ≠ English
    ↓
V1–V6 Pipeline (unchanged)
    ↓
Response (originalText, translatedText, originalTextLanguage, nativeIntentStronger)
```

---

### 3. Components

#### 3.1 Translation Bridge

- **YouTube**: Uses `youtube-transcript-api` `list()` + `translate("en").fetch()` to obtain English transcript. If English transcript exists, uses it directly.
- **Text/File**: Uses `prepare_text_for_analysis()` (langdetect + googletrans) to detect and translate non-English input.
- **Schema**: API responses include `translatedText`, `originalTextLanguage`, `nativeIntentStronger`.

#### 3.2 Native Layer

- **native_signals.py**: Lightweight heuristics for Japanese, Korean, Chinese (honorifics, formal markers).
- **nativeIntentStronger**: Set when native signals indicate more authoritative/aggressive tone than the English translation suggests.
- **Frontend**: Displays "Analyzed from English translation of {lang}" and "Original tone stronger than translation" badge when applicable.

#### 3.3 Display Logic

- Main annotated text uses `translatedText ?? originalText` (English when translation was used).
- Collapsible "Original (language)" section shows source text when translation was used.
- Segments and arc indices align with the displayed (translated) text.

---

### 4. Dependencies

- **Optional** (`pip install .[translate]`): `langdetect`, `googletrans` for text/file translation.
- Without them: English input works; non-English text/file is passed through without translation.

---

### 5. Usage

**API**:

The `/api/analysis/discourse` and `/api/character-arcs/analyze` endpoints automatically apply V7 translation when input is non-English.

**CLI**:

- `discourse-engine analyze --youtube URL` uses V7 translation for non-English captions.
- `discourse-engine analyze "text"` or `discourse-engine analyze file.txt` uses V7 translation for non-English text/files.

---

### 6. Future: Vocal Stress Sync (V8 Design)

This section describes the planned **Vocal Stress Sync** feature: mapping audio pitch and stress from the original YouTube audio to translated text spans.

#### 6.1 Goal

When a non-English YouTube video is analyzed, the engine translates captions to English for fallacy/logic analysis. **Vocal Stress Sync** maps the speaker's audio pitch, volume, and stress from the original recording to the corresponding English text spans, so that stress highlights (e.g., emphasis, anger, uncertainty) appear on the correct words in the UI.

#### 6.2 Current State (V7)

- `fetch_transcript_with_translation()` returns `timestamped_segments`: `[{ start, end, originalText, translatedText }]` per snippet.
- `DialogueTurn` has optional `acoustic_features` (unused).
- Frontend has no audio playback or stress overlays.

#### 6.3 Planned Approach (V8)

1. **Audio Extraction**: Use `yt-dlp` to extract audio from the YouTube video (WAV or MP3).
2. **Pitch / Energy Analysis**: Use `librosa` to compute pitch (F0) and energy (RMS) per short frame (e.g., 10 ms).
3. **Alignment**: Map transcript timestamps to audio frames; approximate word-level positions within snippets.
4. **Stress Mapping**: Heuristics (pitch rise + energy rise → higher stress) to produce per-snippet or per-word `stressLevel: float`.
5. **Schema Extensions**: Add optional `stressLevel?: number` to `AnalysisSegment` and `TimestampedSegment`.
6. **Frontend**: Optional stress overlay (background color or underline intensity based on `stressLevel`).

#### 6.4 Dependencies (V8)

| Package           | Purpose                   |
|-------------------|---------------------------|
| `yt-dlp`          | Extract audio from YouTube|
| `librosa`         | Pitch/energy analysis     |
| (optional) `parselmouth` | Praat-based F0    |

#### 6.5 Risks and Limitations

- YouTube terms of service may restrict automated download; consider using official APIs where applicable.
- Auto-generated captions can have misaligned timestamps; manual captions are more reliable.
- Cross-language word alignment (original ↔ translated) is approximate; stress is mapped at snippet level initially.
