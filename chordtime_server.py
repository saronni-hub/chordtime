#!/usr/bin/env python3
"""ChordTime Server — MIDI + LRC + YouTube + Audio Chord Detection"""

import io
import json
import os
import re
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

CHORD_THRESHOLD = 0.5
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def write_id3_tags(mp3_path, title, artist=None):
    """Escribe ID3 tags a un archivo MP3."""
    if not MUTAGEN_AVAILABLE or not os.path.exists(mp3_path):
        return
    try:
        audio = MP3(mp3_path)
        if audio.tags is None:
            audio.add_tags()
        audio['TIT2'] = TIT2(encoding=3, text=title)
        if artist:
            audio['TPE1'] = TPE1(encoding=3, text=artist)
        audio.save()
        print(f"[ID3] Tags escritos: {title[:40]}", file=__import__('sys').stderr)
    except Exception as e:
        print(f"ID3 tag write error: {e}", file=__import__('sys').stderr)


def normalize_chord_name(chord):
    """
    Normaliza nombres de acordes a formato MIREX (triadas con sostenidos).
    Ejemplos: Dmin7 → Dm, Gmin9 → Gm, Edim → Edim, Amin7 → Am, F → F
    Bemoles: Db → C#, Bb → A#, Eb → D#, etc.
    """
    if not chord or chord in ('N', 'NC', 'N/A'):
        return chord

    # Quitar bajo (/X)
    chord = re.sub(r'/.*$', '', chord).strip()

    # Bemoles → sostenidos MIREX
    flat_to_sharp = {
        'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#',
        'db': 'C#', 'eb': 'D#', 'gb': 'F#', 'ab': 'G#', 'bb': 'A#',
    }
    for flat, sharp in flat_to_sharp.items():
        chord = chord.replace(flat, sharp)

    # Regex: nota + calidad + extensiones
    # Captura: C#min7, D:min9, Gbm, Aaug7, Fsus4, Edim, Bb7, etc.
    m = re.match(r'^([A-G]#?)[:\s]?([a-zA-Z]*?)(\d*)$', chord, re.IGNORECASE)
    if m:
        root = m.group(1).upper()
        quality = m.group(2).lower()
        ext = m.group(3)  # número de extensión (7, 9, 11, 13)

        # Combinar calidad + extensión para buscar
        full_quality = quality + ext if ext else quality

        # Mapeo a triada MIREX
        triad_map = {
            '': '', 'maj': '', 'major': '',
            'm': 'm', 'min': 'm', 'minor': 'm',
            'dim': 'dim', 'diminished': 'dim',
            'aug': 'aug', 'augmented': 'aug',
            'sus': 'sus4', 'sus4': 'sus4', 'sus2': 'sus2',
            # Extensiones → triada
            '7': '', '9': '', '11': '', '13': '', '6': '', '69': '', '5': '',
            'maj7': '', 'maj9': '', 'maj11': '', 'maj13': '',
            'm7': 'm', 'm9': 'm', 'm11': 'm', 'm13': 'm', 'm6': 'm', 'm69': 'm',
            'min7': 'm', 'min9': 'm', 'min11': 'm', 'min13': 'm', 'min6': 'm',
            'dim7': 'dim', 'hdim7': 'dim', 'dim9': 'dim',
            'aug7': 'aug', 'aug9': 'aug',
            'add9': '', 'add11': '', 'add13': '',
            'dom7': '', 'dom9': '',
        }

        suffix = triad_map.get(full_quality, None)
        if suffix is not None:
            return root + suffix

        # Fallback: si calidad conocida pero extensión no
        base_map = {'': '', 'maj': '', 'min': 'm', 'm': 'm', 'dim': 'dim', 'aug': 'aug', 'sus': 'sus4'}
        base = base_map.get(quality, None)
        if base is not None:
            return root + base

    # Ya está en formato simple o no reconocido
    return chord


def transpose_chord(chord, semitones):
    """
    Transpone un acorde matemáticamente por semitones.
    Devuelve el nuevo nombre del acorde.
    Ejemplo: transpose_chord('Am', 5) → 'Dm'
    """
    if not chord or chord in ('N', 'NC', 'N/A'):
        return chord

    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    flat_to_sharp = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#',
                     'db':'C#', 'eb':'D#', 'gb':'F#', 'ab':'G#', 'bb':'A#'}

    # Extraer bajo (/X) si existe
    bass = None
    m_bass = re.search(r'/(.+)$', chord)
    if m_bass:
        bass_note = m_bass.group(1).upper()
        # Normalizar bemol del bajo
        for flat, sharp in flat_to_sharp.items():
            if bass_note == flat:
                bass_note = sharp
                break
        try:
            bass_idx = NOTES.index(bass_note)
            bass_new_idx = (bass_idx + semitones) % 12
            bass = NOTES[bass_new_idx]
        except ValueError:
            bass = None
        chord = chord[:m_bass.start()]  # quitar el /bajo de la chord

    # Extraer raíz y calidad
    m = re.match(r'^([A-G]#?)(.*)$', chord, re.IGNORECASE)
    if not m:
        return chord

    root = m.group(1).upper()
    quality = m.group(2)

    # Normalizar bemoles en raíz
    for flat, sharp in flat_to_sharp.items():
        if root == flat:
            root = sharp
            break

    try:
        root_idx = NOTES.index(root)
    except ValueError:
        return chord

    new_idx = (root_idx + semitones) % 12
    new_root = NOTES[new_idx]

    # Normalizar el sufijo de calidad a triada
    q = quality.lower()
    triad_map = {
        '': '', 'maj': '', 'major': '',
        'm': 'm', 'min': 'm', 'minor': 'm',
        'dim': 'dim', 'diminished': 'dim',
        'aug': 'aug', 'augmented': 'aug',
        'sus4': 'sus4', 'sus2': 'sus2',
        '7': '', 'maj7': '', 'm7': 'm', 'min7': 'm',
        'dim7': 'dim', 'hdim7': 'dim', 'aug7': 'aug',
        '9': '', '11': '', '13': '', '6': '', '69': '',
        'm9': 'm', 'm11': 'm', 'm13': 'm', 'm6': 'm',
        'maj9': '', 'maj11': '', 'maj13': '',
        'add9': '', 'add11': '', 'add13': '',
        'dom7': '', 'dom9': '', 'sus': 'sus4',
    }
    triad_suffix = triad_map.get(q, triad_map.get(q.rstrip('0123456789'), ''))

    result = normalize_chord_name(new_root + triad_suffix)
    if bass:
        result += '/' + bass
    return result


def note_name_from_number(n):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return notes[n % 12]


def classify_chord(notes_pitch):
    if not notes_pitch:
        return None
    unique = sorted(set(notes_pitch))
    intervals = [(p - unique[0]) % 12 for p in unique]
    if intervals == [0, 4, 7]:       return note_name_from_number(unique[0])
    if intervals == [0, 3, 7]:       return note_name_from_number(unique[0]) + 'm'
    if intervals == [0, 3, 6]:        return note_name_from_number(unique[0]) + 'dim'
    if intervals == [0, 4, 8]:        return note_name_from_number(unique[0]) + 'aug'
    if intervals == [0, 5, 7]:        return note_name_from_number(unique[0]) + 'sus4'
    if intervals == [0, 7]:           return note_name_from_number(unique[0]) + '5'
    if intervals == [0, 4, 7, 11]:    return note_name_from_number(unique[0]) + 'maj7'
    if intervals == [0, 4, 7, 10]:    return note_name_from_number(unique[0]) + '7'
    if intervals == [0, 3, 7, 10]:   return note_name_from_number(unique[0]) + 'm7'
    if intervals == [0, 4, 7, 8]:     return note_name_from_number(unique[0]) + 'add9'
    root = note_name_from_number(unique[0])
    n = len(unique)
    if n == 1:   return root
    elif n == 2: return root + '5'
    elif n == 3: return root + 'm' if intervals == [0, 3, 7] else root
    else:        return root


def extract_chords_from_midi(midi_data):
    import pretty_midi
    midi = pretty_midi.PrettyMIDI(io.BytesIO(midi_data))
    duration = midi.get_end_time()

    # ── Tempo map ───────────────────────────────────────────────
    # pretty_midi returns parallel arrays: change times (s) and BPM values
    tempo_times, tempos = midi.get_tempo_changes()

    # Build a clean tempo_map list: [{time, bpm}, ...]
    tempo_map = [
        {'time': round(float(t), 3), 'bpm': round(float(b), 2)}
        for t, b in zip(tempo_times, tempos)
    ]
    # Fallback: if no tempo events, default to 120
    if not tempo_map:
        tempo_map = [{'time': 0.0, 'bpm': 120.0}]

    # Use first BPM as the "global" BPM summary
    avg_bpm = tempo_map[0]['bpm'] if len(tempo_map) == 1 else round(midi.estimate_tempo(), 2)

    def get_bpm_at(time_s):
        """Return the BPM that is active at time_s."""
        bpm_now = tempo_map[0]['bpm']
        for entry in tempo_map:
            if entry['time'] <= time_s:
                bpm_now = entry['bpm']
            else:
                break
        return bpm_now

    def cumulative_beats_at(time_s):
        """
        Integrate beats across all tempo segments up to time_s.
        Returns the total beat count (float) from the start.
        """
        total_beats = 0.0
        seg_times = [e['time'] for e in tempo_map] + [time_s]
        seg_bpms  = [e['bpm']  for e in tempo_map]
        for i, seg_bpm in enumerate(seg_bpms):
            seg_start = seg_times[i]
            seg_end   = min(seg_times[i + 1], time_s)
            if seg_end <= seg_start:
                continue
            total_beats += (seg_end - seg_start) * seg_bpm / 60.0
            if seg_end >= time_s:
                break
        return total_beats

    # ── Note grouping → chords ────────────────────────────────
    all_notes = []
    for instrument in midi.instruments:
        if instrument.is_drum:
            continue
        for note in instrument.notes:
            if note.velocity > CHORD_THRESHOLD * 127:
                all_notes.append(note)
    all_notes.sort(key=lambda n: n.start)
    if not all_notes:
        raise ValueError("No se encontraron notas en el MIDI")

    window = 0.1
    chunks = []
    i = 0
    while i < len(all_notes):
        t = all_notes[i].start
        chunk_notes = [n for n in all_notes if abs(n.start - t) < window]
        pitch = [n.pitch for n in chunk_notes]
        chord = classify_chord(pitch)
        if chord:
            chunks.append({'time': t, 'chord': chord})
        i += len(chunk_notes)

    result = []
    last_chord = None
    for c in chunks:
        if c['chord'] != last_chord:
            result.append(c)
            last_chord = c['chord']

    # Annotate each chord with beat (using local BPM) and the BPM active at that moment
    for c in result:
        local_bpm = get_bpm_at(c['time'])
        beats = cumulative_beats_at(c['time'])
        c['beat'] = f"beat {int(beats) + 1}"
        c['beat_number'] = round(beats + 1, 2)
        c['bpm_at'] = round(local_bpm, 2)

    return result, duration, avg_bpm, tempo_map


LRC_RE = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)')
def parse_lrc(lrc_text):
    entries = []
    for line in lrc_text.splitlines():
        m = LRC_RE.match(line.strip())
        if m:
            mins, secs, hundredths, text = int(m.group(1)), int(m.group(2)), int(m.group(3).ljust(3,'0')[:3]), m.group(4).strip()
            entries.append({'time': round(mins*60 + secs + hundredths/1000.0, 3), 'text': text})
    entries.sort(key=lambda x: x['time'])
    return entries


def merge_chords_and_lyrics(chords, lyrics):
    # Usar tiempos EXACTOS de acordes (no redondear)
    events = [{'time': c['time'], 'chord': c['chord'], 'lyric': None} for c in chords]
    events += [{'time': l['time'], 'chord': None, 'lyric': l['text']} for l in lyrics]
    events.sort(key=lambda x: x['time'])
    
    merged, last_chord = [], None
    for e in events:
        if e['chord']:
            merged.append({'time': e['time'], 'chord': e['chord'], 'lyric': e['lyric']})
            last_chord = e['chord']
        elif e['lyric']:
            merged.append({'time': e['time'], 'chord': last_chord, 'lyric': e['lyric']})
    
    # Eliminar duplicados consecutivos del mismo acorde
    if merged:
        unique = [merged[0]]
        for i in range(1, len(merged)):
            if merged[i]['chord'] != merged[i-1]['chord'] or merged[i]['lyric'] != merged[i-1]['lyric']:
                unique.append(merged[i])
        merged = unique
    
    return merged


# ── AUDIO CHORD DETECTION ────────────────────────────────
# Sólo triadas básicas: mayor y menor para cada nota
CHORD_TEMPLATES = {
    'N':   [0,0,0,0,0,0,0,0,0,0,0,0],
    # Major triads
    'C':   [1,0,0,0,1,0,0,1,0,0,0,0],
    'C#':  [0,1,0,0,0,1,0,0,1,0,0,0],
    'D':   [0,0,1,0,0,0,1,0,0,1,0,0],
    'D#':  [0,0,0,1,0,0,0,1,0,0,1,0],
    'E':   [0,0,0,0,1,0,0,0,1,0,0,1],
    'F':   [1,0,0,0,0,1,0,0,0,1,0,0],
    'F#':  [0,1,0,0,0,0,1,0,0,0,1,0],
    'G':   [0,0,1,0,0,0,0,1,0,0,0,1],
    'G#':  [0,0,0,1,0,0,0,0,1,0,0,1],
    'A':   [1,0,0,0,1,0,0,0,0,1,0,0],
    'A#':  [0,1,0,0,0,1,0,0,0,0,1,0],
    'B':   [0,0,1,0,0,0,1,0,0,0,0,1],
    # Minor triads
    'Cm':  [1,0,0,1,0,0,0,1,0,0,0,0],
    'C#m': [0,1,0,0,1,0,0,0,1,0,0,0],
    'Dm':  [0,0,1,0,0,1,0,0,0,1,0,0],
    'D#m': [0,0,0,1,0,0,1,0,0,0,1,0],
    'Em':  [0,0,0,0,1,0,0,1,0,0,0,1],
    'Fm':  [1,0,0,0,0,1,0,0,1,0,0,0],
    'F#m': [0,1,0,0,0,0,1,0,0,1,0,0],
    'Gm':  [0,0,1,0,0,0,0,1,0,0,1,0],
    'G#m': [0,0,0,1,0,0,0,0,1,0,0,1],
    'Am':  [1,0,0,0,1,0,0,0,0,1,0,0],
    'A#m': [0,1,0,0,0,1,0,0,0,0,1,0],
    'Bm':  [0,0,1,0,0,0,1,0,0,0,0,1],
    # Dominant 7th (adds b7)
    'C7':  [1,0,0,0,1,0,0,1,0,0,1,0],
    'G7':  [0,0,1,0,0,0,0,1,0,0,1,1],
    'D7':  [0,0,1,0,0,0,1,0,0,1,0,1],
    'A7':  [1,0,0,0,1,0,0,0,1,0,1,0],
    'E7':  [0,0,1,0,0,1,0,0,0,1,0,1],
    'B7':  [0,1,0,0,0,1,0,1,0,0,0,1],
    'F7':  [1,0,1,0,0,1,0,0,0,1,0,0],
    'F#7': [0,1,0,1,0,0,1,0,0,0,1,0],
    # Diminished
    'Bdim':[0,0,1,0,0,0,1,0,0,0,0,1],
    'Edim':[0,0,0,0,1,0,0,0,1,0,0,1],
    # Sus4
    'Gsus4':[0,0,1,0,0,1,0,1,0,0,0,1],
    'Dsus4':[0,0,1,0,0,1,0,0,0,1,0,0],
    'Asus4':[1,0,0,0,0,1,0,0,0,1,0,0],
}

def apply_pitch_shift(audio_path, n_semitones, sr=22050):
    """
    Aplica pitch shift de n_semitones al archivo de audio.
    Devuelve la ruta al archivo temporal con el audio desplazado.
    """
    import tempfile
    import librosa
    import soundfile as sf
    
    if n_semitones == 0:
        return audio_path
    
    print(f"[PitchShift] {n_semitones:+d} semitonos → {audio_path}", file=__import__('sys').stderr)
    y, orig_sr = librosa.load(audio_path, sr=sr, mono=False)
    y_shifted = librosa.effects.pitch_shift(y, sr=orig_sr, n_steps=n_semitones)
    
    fd, tmp_path = tempfile.mkstemp(suffix='.mp3')
    os.close(fd)
    sf.write(tmp_path, y_shifted.T, orig_sr, format='MP3')
    print(f"[PitchShift] Guardado en: {tmp_path}", file=__import__('sys').stderr)
    return tmp_path

def detect_chords_via_api(audio_path):
    """
    Detecta acordes enviando el audio a la API de ChordMini (chordmini.me).
    rate limit: 2/min. Sin API key, solo formato multipart/form-data.
    """
    import requests
    import librosa
    import numpy as np
    
    with open(audio_path, 'rb') as f:
        files = {'file': (os.path.basename(audio_path), f, 'audio/mpeg')}
        resp = requests.post('https://www.chordmini.me/api/recognize-chords',
                             files=files, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    if not data.get('success'):
        raise RuntimeError(data.get('error', 'ChordMini error'))
    
    # Detect BPM from audio file
    try:
        y, sr = librosa.load(audio_path, sr=22050)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if len(tempo) > 0 else 0.0
    except:
        bpm = 0.0
    
    return [
        {'time': round(c['start'], 3), 'chord': normalize_chord_name(c['chord']), 'confidence': c.get('confidence', 1)}
        for c in data.get('chords', [])
    ], data.get('duration', 0), bpm


CHORDMINI_URL = os.environ.get('CHORDMINI_URL', 'http://localhost:8080')


def detect_chords_via_local_chordmini(audio_path):
    """
    Detecta acordes enviando el audio al contenedor ChordMiniApp local (puerto 8080).
    Usa Chord-CNN-LSTM que es el modelo que funciona en el contenedor.
    """
    import requests
    
    with open(audio_path, 'rb') as f:
        files = {'file': (os.path.basename(audio_path), f, 'audio/mpeg')}
        resp = requests.post(f'{CHORDMINI_URL}/api/recognize-chords',
                             files=files, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    if not data.get('success'):
        raise RuntimeError(data.get('error', 'ChordMiniApp error'))
    
    duration = data.get('duration', 0)
    bpm = 0.0
    
    return [
        {'time': round(c['start'], 3), 'chord': normalize_chord_name(c['chord']), 'confidence': c.get('confidence', 1)}
        for c in data.get('chords', [])
    ], duration, bpm


def detect_chords_from_audio(audio_path, sr=22050, hop_length=512):
    """
    Beat-synchronous chord detection with HPSS and madmom beat tracking.
    Uses madmom for beat detection, then chroma template matching on beat-aligned windows.
    """
    import numpy as np
    import librosa
    from librosa import effects

    print(f"[Audio] Loading: {audio_path}", file=__import__('sys').stderr)

    file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
    print(f"[Audio] File size: {file_size} bytes", file=__import__('sys').stderr)

    y_stereo, sr = librosa.load(audio_path, sr=sr, mono=False)
    duration = librosa.get_duration(y=y_stereo, sr=sr)
    print(f"[Audio] Duration: {duration:.2f}s, beat-synchronous detection", file=__import__('sys').stderr)
    print(f"[Audio] Audio shape: {y_stereo.shape}, sample rate: {sr}", file=__import__('sys').stderr)

    y_mono = librosa.to_mono(y_stereo) if y_stereo.ndim > 1 else y_stereo

    # Detect beats using madmom (much better than librosa's beat_track)
    beats = None
    bpm = 0.0
    try:
        from madmom.features.beats import RNNBeatProcessor, DBNBeatTrackingProcessor
        beat_proc = RNNBeatProcessor()
        act = beat_proc(audio_path)
        tracker = DBNBeatTrackingProcessor(fps=100)
        beats = tracker(act)
        if len(beats) > 1:
            intervals = np.diff(beats)
            median_interval = np.median(intervals)
            bpm = 60.0 / median_interval if median_interval > 0 else 120.0
        print(f"[Audio] Madmom beats: {len(beats)}, BPM: {bpm:.1f}", file=__import__('sys').stderr)
    except Exception as e:
        print(f"[Audio] Madmom failed: {e}, falling back to librosa beat_track", file=__import__('sys').stderr)
        try:
            tempo, _ = librosa.beat.beat_track(y=y_mono, sr=sr)
            bpm = float(tempo[0]) if len(tempo) > 0 else 0.0
        except:
            bpm = 0.0

    # HPSS on mono
    H, P = effects.hpss(y_mono)

    # High-resolution chroma from harmonic component
    chroma = librosa.feature.chroma_cqt(y=H, sr=sr, hop_length=hop_length, n_octaves=6)
    chroma = np.maximum(chroma, 0)

    # L2 normalize
    norms = np.linalg.norm(chroma, axis=0, keepdims=True)
    chroma = np.where(norms > 1e-6, chroma / norms, 0)

    # Median smoothing to reduce noise
    try:
        from scipy.ndimage import median_filter
        chroma = median_filter(chroma, size=(1, 3))
    except ImportError:
        pass

    n_frames = chroma.shape[1]

    TEMPLATE_MATRIX = np.array([CHORD_TEMPLATES[c] for c in CHORD_TEMPLATES], dtype=np.float32)
    CHORD_NAMES = list(CHORD_TEMPLATES.keys())

    # If we have beats, use beat-synchronous windows; otherwise use fixed windows
    if beats is not None and len(beats) > 2:
        # Beat-synchronous: evaluate at each beat
        beat_times = beats
        window_s = 0.5  # half a beat window
    else:
        # Fallback: fixed grid
        beat_times = np.arange(0, duration, 0.5)
        window_s = 1.0

    chords = []
    last_chord = None

    for i, beat_time in enumerate(beat_times):
        # Convert beat time to frame
        start_frame = librosa.time_to_frames(beat_time, sr=sr, hop_length=hop_length)
        end_frame = librosa.time_to_frames(beat_time + window_s, sr=sr, hop_length=hop_length)
        end_frame = min(end_frame, n_frames)

        if start_frame >= n_frames:
            break

        segment = chroma[:, start_frame:end_frame].mean(axis=1)
        sim = TEMPLATE_MATRIX @ segment
        best_idx = np.argmax(sim)
        best_score = sim[best_idx]

        chord = CHORD_NAMES[best_idx] if best_score >= 0.30 else 'N'
        time_s = beat_time

        # Post-process: remove very short chords (< 0.3s)
        if chord != last_chord:
            if chord != 'N':
                chords.append({'time': round(time_s, 3), 'chord': chord, 'confidence': round(float(best_score), 3)})
            last_chord = chord
        elif chord == 'N':
            last_chord = None

    # Merge consecutive duplicates
    if chords:
        merged = [chords[0]]
        for c in chords[1:]:
            if c['chord'] == merged[-1]['chord']:
                continue
            merged.append(c)
        chords = merged

    return chords, duration, bpm


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # Serve HTML - old (original)
        if parsed.path in ('/', '/chordtime.html', '/chordtimev2.html'):
            path = '/app/chordtime.html'
            if os.path.exists(path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                with open(path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
            return

        # Serve HTML - new v2
        if parsed.path in ('/chordtimev2.html',):
            path = '/app/chordtime.html'
            if os.path.exists(path):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                with open(path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404)
            return

        # API status endpoint
        if parsed.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            status = {
                'status': 'ok',
                'version': '2.0',
                'timestamp': __import__('time').time(),
                'download_dir': DOWNLOAD_DIR,
                'mutagen_available': MUTAGEN_AVAILABLE
            }
            self.wfile.write(json.dumps(status).encode())
            return

        # Download audio file
        if parsed.path.startswith('/api/yt/file/'):
            raw_filename = parsed.path[len('/api/yt/file/'):]
            # URL-decode (e.g. %2B → +, %20 → space)
            filename = unquote(raw_filename)
            safe_path = os.path.normpath(os.path.join(DOWNLOAD_DIR, filename))
            if not safe_path.startswith(DOWNLOAD_DIR):
                self.send_error(403); return
            if not os.path.exists(safe_path):
                # Try raw filename (not URL-decoded)
                safe_path_raw = os.path.normpath(os.path.join(DOWNLOAD_DIR, raw_filename))
                if os.path.exists(safe_path_raw):
                    safe_path = safe_path_raw
                    filename = raw_filename
                else:
                    self.send_error(404); return
            size = os.path.getsize(safe_path)
            try:
                with open(safe_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/mpeg')
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', size)
                    self.end_headers()
                    try:
                        self.wfile.write(f.read())
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass  # client disconnected
            except Exception:
                pass
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        # ── MIDI + LRC ─────────────────────────────────────
        if parsed.path == '/api/chordtime':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                raw_body = self.rfile.read(content_length)
                midi_data, lrc_data = None, None
                lrc_offset = 0.0

                if 'multipart/form-data' in (self.headers.get('Content-Type') or ''):
                    # Parse multipart/form-data without cgi module (Python 3.14 removed it)
                    content_type = self.headers.get('Content-Type', '')
                    boundary = content_type.split('boundary=')[-1].strip('"').encode()
                    raw = raw_body
                    parts = raw.split(b'--' + boundary)
                    midi_data, lrc_data = None, None
                    for part in parts:
                        if b'name="midi"' in part:
                            header_end = part.find(b'\r\n\r\n')
                            if header_end > 0:
                                midi_data = part[header_end+4:]
                                if midi_data.endswith(b'\r\n'):
                                    midi_data = midi_data[:-2]
                        elif b'name="lrc"' in part:
                            header_end = part.find(b'\r\n\r\n')
                            if header_end > 0:
                                lrc_data = part[header_end+4:].decode('utf-8', errors='replace')
                                if lrc_data.endswith('\r\n'):
                                    lrc_data = lrc_data[:-2]
                        elif b'name="lrc_offset"' in part:
                            header_end = part.find(b'\r\n\r\n')
                            if header_end > 0:
                                try:
                                    lrc_offset = float(part[header_end+4:].decode().strip())
                                except:
                                    lrc_offset = 0.0
                else:
                    midi_data = raw_body

                if not midi_data:
                    raise ValueError("No se encontró archivo MIDI")

                chords, duration, bpm, tempo_map = extract_chords_from_midi(midi_data)
                response = {
                    'chords': chords,
                    'duration': round(duration, 3),
                    'bpm': round(bpm, 1),
                    'tempo_map': tempo_map,
                    'source': 'midi',
                    'json': [{
                        'time': c['time'],
                        'chord': c['chord'],
                        'beat': c.get('beat_number'),
                        'bpm_at': c.get('bpm_at')
                    } for c in chords]
                }

                if lrc_data:
                    lyrics = parse_lrc(lrc_data)
                    # Apply lrc_offset: shift each lyric timestamp
                    if lrc_offset != 0:
                        lyrics = [{'time': max(0, l['time'] + lrc_offset), 'text': l['text']} for l in lyrics]
                    merged = merge_chords_and_lyrics(chords, lyrics)
                    response['merged'] = merged
                    response['lyrics_count'] = len(lyrics)

                # Apply offset to results if provided
                try:
                    offset = float(dict(parse_qsl(raw_body.decode())).get('offset', 0))
                except:
                    # If multipart, get from field
                    offset = 0.0 # Will implement later if needed, mostly for JSON
                
                response['json'] = [{'time': m['time'], 'chord': m['chord'], 'lyric': m.get('lyric')} for m in (merged if lrc_data else chords)]

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())

            except ValueError as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # ── YOUTUBE SEARCH ──────────────────────────────
        if parsed.path == '/api/yt/search':
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                query = body.get('query', '').strip()
                if not query:
                    raise ValueError("Falta búsqueda")
                result = subprocess.run(
                    ['yt-dlp', '--flat-playlist', '--dump-json', '--no-playlist',
                     '--extractor-args', 'youtube:player_client=web_safari',
                     '--js-runtimes', 'deno',
                     '--force-ipv4',
                     '--', f'ytsearch5:{query}'],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    raise Exception(result.stderr.strip()[-300:])
                lines = result.stdout.strip().splitlines()
                videos = []
                for line in lines:
                    try:
                        d = json.loads(line)
                        videos.append({
                            'id': d.get('id'),
                            'title': d.get('title', 'Sin título'),
                            'uploader': d.get('uploader') or d.get('channel', ''),
                            'duration': d.get('duration') or 0,
                            'url': d.get('webpage_url', f"https://youtu.be/{d.get('id')}")
                        })
                    except:
                        pass
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'videos': videos}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # ── YOUTUBE INFO ─────────────────────────────────
        if parsed.path == '/api/yt/info':
            # Handle OPTIONS preflight for CORS
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                url = body.get('url')
                if not url:
                    raise ValueError("Falta URL")

                result = subprocess.run(
                    ['yt-dlp', '--dump-json', '--no-playlist', '--flat-playlist',
                     '--extractor-args', 'youtube:player_client=web_safari',
                     '--js-runtimes', 'deno',
                     '--force-ipv4', url],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    raise Exception(result.stderr.strip()[-300:])
                data = json.loads(result.stdout.strip().splitlines()[0])
                dur = data.get('duration') or 0
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'id': data.get('id'),
                    'title': data.get('title', 'Sin título'),
                    'uploader': data.get('uploader') or data.get('channel', ''),
                    'duration': f"{int(dur//60)}:{int(dur%60):02d}",
                    'duration_s': dur,
                    'webpage_url': data.get('webpage_url', url),
                }).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # ── CHORD PREVIEW (YouTube → detect without full download) ──
        if parsed.path == '/api/yt/preview':
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                url = body.get('url')
                semitones = int(body.get('transpose', 0))
                detect = body.get('detect', True)

                if not url:
                    raise ValueError("Falta URL")

                # Get video info
                title_cmd = ['yt-dlp', '--dump-json', '--no-playlist', '--flat-playlist',
                             '--extractor-args', 'youtube:player_client=web_safari',
                             '--js-runtimes', 'deno',
                             '--force-ipv4', url]
                title_result = subprocess.run(title_cmd, capture_output=True, text=True, timeout=30)
                raw_title = 'audio'
                video_artist = None
                dur = 0
                if title_result.returncode == 0:
                    try:
                        info = json.loads(title_result.stdout.strip().splitlines()[0])
                        raw_title = info.get('title', 'audio')
                        video_artist = info.get('artist') or info.get('uploader') or info.get('creator')
                        dur = info.get('duration') or 0
                    except:
                        pass

                if not detect:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'title': raw_title,
                        'artist': video_artist,
                        'duration': f"{int(dur//60)}:{int(dur%60):02d}",
                        'chords': [], 'chord_count': 0
                    }).encode())
                    return

                # Download only first 90 seconds for preview
                tmp_path = f"/tmp/yt_preview_{hash(url) & 0xffffff}.mp3"
                try:
                    cmd = ['yt-dlp', '-x', '--audio-format', 'mp3',
                           '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                           '--no-check-certificates',
                           '--no-playlist',
                           '--force-ipv4',
                           '--no-warnings',
                           '-R', '3',
                           '--download-sections', '*0-90',
                           '-o', tmp_path, url]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if result.returncode != 0:
                        raise Exception(result.stderr.strip()[-300:])

                    # Try ChordMiniApp local first (Chord-CNN-LSTM model), fall back to local librosa
                    det_source = 'preview'
                    try:
                        chords, det_dur, bpm = detect_chords_via_local_chordmini(tmp_path)
                        det_source = 'chordmini_local'
                        print(f"[Preview] ChordMiniApp local: {len(chords)} chords, bpm={bpm:.1f}", file=__import__('sys').stderr)
                    except Exception as api_err:
                        print(f"[Preview] ChordMiniApp failed ({api_err}), using local Librosa", file=__import__('sys').stderr)
                        chords, det_dur, bpm = detect_chords_from_audio(tmp_path)

                    # Apply mathematical transpose to chord names (NOT to audio)
                    if semitones != 0:
                        transposed = []
                        for c in chords:
                            new_chord = transpose_chord(c['chord'], semitones)
                            transposed.append({'time': c['time'], 'chord': new_chord})
                        chords = transposed

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'title': raw_title,
                        'artist': video_artist,
                        'duration': f"{int(dur//60)}:{int(dur%60):02d}",
                        'chords': [{'time': round(c['time'],3), 'chord': c['chord']} for c in chords],
                        'chord_count': len(chords),
                        'source': det_source,
                        'transpose': semitones,
                        'bpm': round(bpm, 1),
                        'original_detected': True  # tells frontend these were detected from original audio
                    }, indent=2).encode())
                finally:
                    # Clean up temp files
                    for p in [tmp_path, tmp_path.replace('.mp3', '.webm'), tmp_path.replace('.mp3', '.m4a')]:
                        if os.path.exists(p):
                            try: os.remove(p)
                            except: pass
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        # ── YOUTUBE DOWNLOAD ───────────────────────────────
        if parsed.path == '/api/yt/download':
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                url = body.get('url')
                fmt = body.get('format', 'mp3')
                quality = body.get('quality', 'best')
                detect = body.get('detect_chords', False)

                if not url:
                    raise ValueError("Falta URL")

                # Get video title first for filename
                title_cmd = ['yt-dlp', '--dump-json', '--no-playlist', '--flat-playlist',
                             '--extractor-args', 'youtube:player_client=web_safari',
                             '--js-runtimes', 'deno',
                             '--force-ipv4', url]
                title_result = subprocess.run(title_cmd, capture_output=True, text=True, timeout=30)
                video_title = 'audio'
                raw_title = 'audio'
                video_artist = None
                if title_result.returncode == 0:
                    try:
                        info = json.loads(title_result.stdout.strip().splitlines()[0])
                        raw_title = info.get('title', 'audio')
                        video_artist = info.get('artist') or info.get('uploader') or info.get('creator')
                        # Clean title for filesystem
                        video_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', raw_title).strip()[:80]
                    except:
                        pass

                safe_name = re.sub(r'[^\w\-_.]', '_', video_title)
                out_base = os.path.join(DOWNLOAD_DIR, safe_name)

                if fmt == 'mp3':
                    output_tmpl = out_base + '.%(ext)s'
                    cmd = ['yt-dlp', '-x', '--audio-format', 'mp3',
                           '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                           '--no-check-certificates',
                           '--no-playlist',
                           '--force-ipv4',
                           '-o', output_tmpl, url]
                else:
                    output_tmpl = out_base + '.%(ext)s'
                    cmd = ['yt-dlp',
                           '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                           '--no-check-certificates',
                           '--no-playlist',
                           '--force-ipv4',
                           '-o', output_tmpl, url]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise Exception(result.stderr.strip()[-500:])

                # Find downloaded file
                downloaded = None
                print(f"[Download] Looking for files with base: {out_base}", file=__import__('sys').stderr)
                for candidate in [out_base + '.mp3', out_base + '.mp4', out_base + '.webm', out_base + '.m4a']:
                    if os.path.exists(candidate):
                        downloaded = candidate
                        file_size = os.path.getsize(candidate) if os.path.exists(candidate) else 0
                        print(f"[Download] Found: {candidate} ({file_size} bytes)", file=__import__('sys').stderr)
                        break
                if not downloaded:
                    files = sorted([f for f in os.listdir(DOWNLOAD_DIR) if safe_name in f], reverse=True)
                    if files:
                        downloaded = os.path.join(DOWNLOAD_DIR, files[0])

                if not downloaded:
                    raise Exception("No se encontró el archivo descargado")

                filename = os.path.basename(downloaded)
                response = {'filename': filename, 'path': downloaded}

                # Apply pitch shift if transpose requested
                semitones = int(body.get('transpose', 0))
                if semitones != 0:
                    shifted_tmp = apply_pitch_shift(downloaded, semitones)
                    base, ext = os.path.splitext(downloaded)
                    shifted_filename = f"{base}_transpose{'+' if semitones > 0 else ''}{semitones}{ext}"
                    import shutil
                    shutil.move(shifted_tmp, shifted_filename)
                    downloaded = shifted_filename
                    filename = os.path.basename(shifted_filename)
                    response['filename'] = filename
                    response['path'] = downloaded
                    response['transpose'] = semitones
                    print(f"[Transpose] Audio guardado: {filename}", file=__import__('sys').stderr)

                # Write ID3 tags to MP3
                if downloaded.endswith('.mp3'):
                    write_id3_tags(downloaded, raw_title, video_artist)

                # Always detect chords from FULL audio when downloading
                # (preview chords are only 90 seconds, we need full song)
                if detect:
                    try:
                        print(f"[Detect] Running analysis on: {downloaded}", file=__import__('sys').stderr)
                        # Try ChordMiniApp local first (Chord-CNN-LSTM model), fall back to local librosa
                        try:
                            chords, dur, bpm = detect_chords_via_local_chordmini(downloaded)
                            print(f"[Detect] ChordMiniApp local success. Dur: {dur:.2f}s, BPM: {bpm:.1f}", file=__import__('sys').stderr)
                            response['chords'] = chords
                            response['duration'] = dur
                            response['bpm'] = round(bpm, 1)
                            response['source'] = 'chordmini_local'
                            response['json'] = [{'time': c['time'], 'chord': c['chord']} for c in chords]
                            response['chord_count'] = len(chords)
                        except Exception as api_err:
                            # Fallback to local librosa detection
                            warn = f"ChordMiniApp unavailable: {api_err}, falling back to local"
                            print(f"[Detect] {warn}", file=__import__('sys').stderr)
                            response['chord_warn'] = warn
                            chords, dur, bpm = detect_chords_from_audio(downloaded)
                            print(f"[Detect] Librosa success. Dur: {dur:.2f}s, BPM: {bpm:.1f}", file=__import__('sys').stderr)
                            response['chords'] = chords
                            response['duration'] = round(dur, 3)
                            response['bpm'] = round(bpm, 1)
                            response['source'] = 'audio'
                            response['json'] = [{'time': c['time'], 'chord': c['chord']} for c in chords]
                            response['chord_count'] = len(chords)
                    except Exception as e:
                        print(f"[Detect] Error: {e}", file=__import__('sys').stderr)
                        response['chord_error'] = str(e)
                else:
                    # No chord detection requested, just return file info
                    response['filename'] = filename
                    response['path'] = downloaded
                    response['duration'] = round(sum(1 for _ in open(downloaded, 'rb')) / (44100 * 2), 1) if os.path.exists(downloaded) else 0

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return

        self.send_error(404)

    def log_message(self, format, *args):
        pass


def main():
    port = 8193
    print(f"🎹 ChordTime Server → http://localhost:{port}/chordtime.html")
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()


if __name__ == '__main__':
    main()
