#!/bin/bash
# Script simple para obtener JSON de ChordTime desde terminal
# Uso: ./get_chords.sh "URL_YOUTUBE"

set -e

echo "🎹 ChordTime Terminal Client"
echo "=============================="

if [ $# -eq 0 ]; then
    echo "Uso: $0 \"URL_YOUTUBE\""
    echo ""
    echo "Ejemplo:"
    echo "  $0 \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\""
    echo ""
    exit 1
fi

URL="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="chordtime_${TIMESTAMP}.json"

echo "URL: $URL"
echo "Obteniendo JSON completo con BPM..."
echo ""

# Verificar que el servidor esté activo
if ! curl -s http://localhost:8193/api/status > /dev/null; then
    echo "❌ ERROR: Servidor ChordTime no responde"
    echo "   Ejecuta primero: cd /Volumes/DiscoExterno/ai-studio/chordtimev2 && python3 chordtime_server.py"
    exit 1
fi

echo "✅ Servidor activo"
echo "⬇️  Descargando y detectando acordes (puede tardar unos minutos)..."
echo ""

# Hacer la petición
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$URL\", \"format\": \"mp3\", \"quality\": \"best\", \"detect_chords\": true}" \
  http://localhost:8193/api/yt/download \
  | python3 -m json.tool > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ JSON guardado en: $OUTPUT_FILE"
    
    # Mostrar resumen
    echo ""
    echo "📊 RESUMEN DEL ARCHIVO:"
    echo "----------------------"
    
    # Extraer información con python
    python3 -c "
import json, sys
try:
    with open('$OUTPUT_FILE', 'r') as f:
        data = json.load(f)
    
    print(f'Duración: {data.get(\"duration\", \"N/A\")}s')
    print(f'BPM: {data.get(\"bpm\", \"N/A\")}')
    print(f'Método: {data.get(\"source\", \"N/A\")}')
    
    chords = data.get('chords', data.get('json', []))
    if isinstance(chords, list):
        print(f'Acordes detectados: {len(chords)}')
        if chords:
            print(f'Primer acorde: {chords[0].get(\"time\", \"?\")}s - {chords[0].get(\"chord\", \"?\")}')
    
    filename = data.get('filename', '')
    if filename:
        print(f'Archivo: {filename}')
        
except Exception as e:
    print(f'Error leyendo JSON: {e}')
    "
    
    echo ""
    echo "💡 Para ver el JSON completo:"
    echo "   cat $OUTPUT_FILE | head -50"
    echo "   (o abre el archivo en un editor)"
    
else
    echo "❌ Error al obtener el JSON"
    exit 1
fi