# CHORDTIME V2 - RESUMEN EJECUTIVO PARA ANTIGRAVITY

## 📋 ESTADO ACTUAL (21 Abril 2026, 20:18 GMT+2)

### **PROBLEMAS CRÍTICOS:**
1. **JSON sin BPM** - Usuario obtiene solo array de acordes, no objeto completo
2. **Confusión Preview vs Download** - Preview (90s) vs Download (completo)
3. **Cache del navegador** - JavaScript no se actualiza, funciones faltan
4. **Error de sintaxis** - Usuario pone URLs en consola JavaScript
5. **Frustración del usuario** - 2+ horas debugging sin solución clara

### **SOLUCIONES IMPLEMENTADAS:**
1. **Scripts de terminal** en `/scripts/` para obtener JSON completo
2. **Correcciones en servidor** - BPM incluido en respuestas
3. **Documentación organizada** en carpeta del proyecto
4. **Función `getCompleteChordData()`** en frontend (pero cache la bloquea)

### **ARQUITECTURA:**
```
chordtime_server.py (Python HTTP server, port 8193)
├── /api/yt/download → JSON completo con BPM
├── /api/yt/preview → Solo 90s, sin BPM completo
└── /api/status → Verificación

chordtime.html (Frontend)
├── Preview (90s) vs Download (completo)
├── lastData almacena resultados
└── Botones para descargar/copiar JSON
```

### **PROBLEMAS DE DISEÑO IDENTIFICADOS:**
1. **Dualidad Preview/Download** confunde al usuario
2. **`lastData` inconsistente** - depende del endpoint usado
3. **Cache agresivo** - cambios no se propagan
4. **Manejo de errores pobre** - mensajes no claros
5. **API design** - diferentes estructuras para preview/download

## 🎯 TAREAS PARA ANTIGRAVITY:

### **1. REVISIÓN ARQUITECTÓNICA**
- ¿Debe haber solo un endpoint (no preview/download separados)?
- ¿Cómo manejar cache del navegador efectivamente?
- ¿Estructura de datos unificada?

### **2. DISEÑO DE API**
- Endpoint único con parámetro `full=true/false`
- Respuesta consistente siempre (misma estructura)
- Metadata incluida siempre (BPM, duration, source)

### **3. FRONTEND SIMPLIFICADO**
- Eliminar confusión preview/download
- Una sola acción: "Procesar canción"
- Opciones: calidad, detectar acordes, formato

### **4. MANEJO DE CACHE**
- Versionado de assets (query params)
- Service worker para cache control
- Hard refresh instructions claras

### **5. EXPERIENCIA DE USUARIO**
- Progreso claro durante procesamiento
- Resultados visibles inmediatamente
- JSON descargable con un clic (siempre completo)

## 📊 DATOS TÉCNICOS:

### **Servidor funciona:**
```bash
curl http://localhost:8193/api/status
# {"status": "ok", "version": "2.0", ...}
```

### **Scripts funcionan:**
```bash
cd /Volumes/DiscoExterno/ai-studio/chordtimev2/scripts
python3 chordtime_direct.py "URL"
# JSON completo con BPM
```

### **Problema principal:**
Usuario no puede obtener JSON con BPM desde interfaz web debido a cache y confusión entre preview/download.

## 🚀 OBJETIVO FINAL:
**ChordTime V3** con:
1. Interfaz simple (una acción)
2. JSON siempre completo (con BPM)
3. Sin confusión preview/download
4. Cache manejado automáticamente
5. Documentación clara

---
**TRANSFERIDO A ANTIGRAVITY:** 21 Abril 2026, 20:20 GMT+2
**PRIORIDAD:** ALTA - Usuario frustrado necesita solución estable