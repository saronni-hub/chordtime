#!/usr/bin/env python3
import subprocess
import sys
import os

# Cambiar al directorio correcto
os.chdir("/Volumes/DiscoExterno/ai-studio")

# Ejecutar chordtime_server.py
print("Intentando arrancar chordtime_server.py...")
try:
    result = subprocess.run(
        [sys.executable, "chordtime_server.py"],
        capture_output=True,
        text=True,
        timeout=10
    )
    print("Salida:", result.stdout)
    if result.stderr:
        print("Errores:", result.stderr)
    print("Código de salida:", result.returncode)
except Exception as e:
    print("Error al ejecutar:", e)