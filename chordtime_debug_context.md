# CHORDTIME V2 - DEBUG CONTEXT FOR OPENCODE

## PROJECT OVERVIEW
ChordTime V2 is a web-based chord detection system that:
1. Downloads audio from YouTube
2. Detects chords using:
   - ChordMini API (cloud-based, preferred)
   - Librosa (local fallback)
   - MIDI file parsing
3. Transposes chords (+/- 12 semitones)
4. Generates JSON output with chords, BPM, timing

## CURRENT STATE (April 21, 2026 - 18:32 GMT+2)

### WORKING:
- ✅ YouTube download (audio/video)
- ✅ Chord detection (both ChordMini and Librosa)
- ✅ Transpose functionality
- ✅ MIDI file processing (recently fixed - pretty_midi was missing)
- ✅ Basic web interface

### ISSUES IDENTIFIED:

#### 1. **90-SECOND PREVIEW VS FULL SONG BUG**
- **Problem:** System only analyzes 90 seconds, not full song
- **Root Cause:** Preview endpoint (`/api/yt/preview`) uses `--download-sections '*0-90'`
- **Expected:** Download endpoint (`/api/yt/download`) should analyze FULL audio
- **Status:** Partially fixed in server code but still not working

#### 2. **BPM NOT IN JSON OUTPUT**
- **Problem:** Downloaded JSON missing BPM field
- **Root Cause:** Download button saves `lastData.json` (chords only)
- **Fix Applied:** Updated download button to include BPM, duration, source
- **Status:** Fix may not be active due to browser cache

#### 3. **BEAT COLUMN EMPTY**
- **Problem:** "Beat" column shows "—" instead of beat numbers
- **Root Cause:** Beat calculation not implemented in frontend
- **Fix Applied:** Added beat calculation in `renderResults()`: `beat = time * bpm / 60.0`
- **Status:** Implemented but may need hard refresh

#### 4. **STATS NOT DISPLAYING**
- **Problem:** Statistics (Acordes, Duración, BPM, Método) not visible
- **Possible Causes:**
  - CSS hiding `.results` div
  - JavaScript error preventing `renderResults()` execution
  - Server not returning required fields (`bpm`, `source`)

#### 5. **DETECTION METHOD NOT VISIBLE**
- **Problem:** User can't see which detection method was used
- **Fix Applied:** Added "Método" field in HTML/JS
- **Status:** Implemented but may not be displaying

## SERVER CODE CHANGES MADE:

### 1. `chordtime_server.py`:
- Added BPM detection for audio files (librosa.beat.beat_track)
- Updated `detect_chords_via_api()` to return BPM
- Updated `detect_chords_from_audio()` to return BPM
- Modified download endpoint to ignore preview chords and always detect from full audio
- Added `json` field to MIDI response
- Added `bpm` field to all responses

### 2. `chordtime.html`:
- Added "Método" stat field
- Updated `renderResults()` to display detection method
- Added beat calculation in `renderResults()`
- Updated download button to include BPM, duration, source in JSON

## DEPENDENCIES INSTALLED:
- `mutagen` (for ID3 tags) - ✅ Installed
- `librosa` (for audio analysis) - ✅ Installed  
- `pretty_midi` (for MIDI processing) - ✅ Installed (was missing, caused 500 error)

## TEST RESULTS FROM USER:
1. **YouTube:** Downloads work, chord detection works (inaccurate), transpose works
2. **MIDI:** Now works after installing pretty_midi
3. **JSON Output:** Still only 90 seconds of chords, no BPM (as of latest test)

## BROWSER CACHE ISSUE:
User has tried private window and cache clearing, but changes may not be loading due to:
- Service worker caching
- Aggressive browser caching
- CDN-like behavior

## NEXT STEPS FOR OPENCODE:

### IMMEDIATE FIXES:
1. **Verify server is actually analyzing full audio:**
   - Add debug logging to `detect_chords_from_audio()` to log file path and actual duration
   - Check if downloaded file is actually full length

2. **Force browser cache clear:**
   - Add cache-busting query params to HTML/JS requests
   - Implement service worker unregister

3. **Complete JSON output fix:**
   - Ensure download endpoint returns complete data structure
   - Verify frontend displays download results (not just preview)

### LONGER TERM:
1. Add MP3 upload functionality (user requested)
2. Improve chord detection accuracy
3. Add batch processing
4. Add chord progression analysis

## FILES TO EXAMINE:
- `/Volumes/DiscoExterno/ai-studio/chordtimev2/chordtime_server.py`
- `/Volumes/DiscoExterno/ai-studio/chordtimev2/chordtime.html`
- Server logs: `/tmp/chordtime_final.log`
- User's test JSON: `Love_of_Lesbian_-_Ej_rcito_de_salvaci_n_Lyric_Vid---e087cba5-be6c-47e5-8b9a-21dec837f274.json`

## USER FRUSTRATION LEVEL: HIGH
After 2+ hours of debugging, user wants to hand off to OpenCode. Priority is delivering working solution with:
1. Full song analysis (not 90 seconds)
2. BPM in JSON output
3. Beat column populated
4. Stats visible

## SERVER IS RUNNING ON:
- Port: 8193
- URL: `http://localhost:8193/chordtimev2.html`
- Process: Managed via `ChordTime.command` launcher

---
**END OF CONTEXT - HANDING OFF TO OPENCODE**