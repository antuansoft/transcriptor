# 🎙️ Transcriptor de Audio — Whisper Local

Herramienta de transcripción de audio local basada en [OpenAI Whisper](https://github.com/openai/whisper). Procesa archivos de audio/vídeo y genera transcripciones en formato Word (`.docx`) y JSON con timestamps.

---

## Requisitos previos

Antes de clonar el repositorio, asegúrate de tener instalado en tu sistema:

| Requisito | Versión | Notas |
|---|---|---|
| Python | 3.10 – 3.12 | Ver instrucciones abajo |
| Git | cualquiera | [git-scm.com](https://git-scm.com/) |
| FFmpeg | cualquiera | Ver instrucciones abajo |
| GPU NVIDIA (opcional) | — | Sin GPU funciona en CPU, más lento |

---

### Instalar Python

#### Windows

1. Ve a [python.org/downloads](https://www.python.org/downloads/) y descarga la versión **3.10.x** o **3.11.x**
   > ⚠️ Evita Python 3.12 si tienes problemas de compatibilidad con Whisper

2. Ejecuta el instalador y **antes de darle a Install**, marca obligatoriamente:
   - ☑️ **Add Python to PATH**

3. Completa la instalación con las opciones por defecto

4. Verifica en una terminal nueva:
   ```bash
   python --version
   ```

5. Si el comando no se reconoce, desactiva el alias de la Microsoft Store:
   - Busca **"Manage app execution aliases"** en el menú inicio
   - Pon en **Off** tanto `python.exe` como `python3.exe`
   - Abre una terminal nueva y vuelve a probar

6. Si sigue sin funcionar, añade Python al PATH manualmente:
   - Busca `sysdm.cpl` en el menú inicio → **Variables de entorno**
   - En **Variables del sistema** selecciona **Path** → **Editar** → **New**
   - Añade estas dos rutas (ajusta el usuario):
     ```
     C:\Users\TU_USUARIO\AppData\Local\Programs\Python\Python311
     C:\Users\TU_USUARIO\AppData\Local\Programs\Python\Python311\Scripts
     ```
   - Acepta todo y abre una terminal nueva

#### macOS

```bash
brew install python@3.11
```

#### Linux

```bash
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip
```

---

### Instalar FFmpeg

**Windows (recomendado):**
```bash
winget install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### Drivers CUDA (solo si tienes GPU NVIDIA)

1. Ejecuta `nvidia-smi` en la terminal para ver tu versión de CUDA
2. Descarga los drivers desde [developer.nvidia.com/cuda-downloads](https://developer.nvidia.com/cuda-downloads)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd transcriptor
```

### 2. Crear el entorno virtual

```bash
python -m venv venv
```

Activarlo:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

> Deberás activar el entorno virtual cada vez que abras una terminal nueva.

### 3. Instalar PyTorch

Elige el comando según tu hardware:

**Con GPU NVIDIA (CUDA 12.x):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

**Con GPU NVIDIA (CUDA 11.x):**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Sin GPU (solo CPU):**
```bash
pip install torch torchvision torchaudio
```

> Para saber qué versión de CUDA tienes: ejecuta `nvidia-smi` y mira la esquina superior derecha.

### 4. Instalar el resto de dependencias

```bash
pip install -r requirements.txt
```

### 5. Verificar la instalación

```bash
python -c "import torch; print('CUDA disponible:', torch.cuda.is_available())"
```

---

## Uso

### 1. Configura el archivo a transcribir

Edita `transcriptor.py` y cambia estas dos líneas al inicio del bloque `__main__`:

```python
AUDIO_PATH = r"C:\ruta\a\tu\archivo.mp4"   # Ruta completa al archivo de audio
MODELO     = "medium"                        # tiny | base | small | medium | large
```

### 2. Ejecutar

```bash
python transcriptor.py
```

### 3. Resultados

Los archivos de salida se generan en la **misma carpeta que el audio**:

```
📄 nombre_archivo_transcript.docx   ← transcripción completa en Word
📋 nombre_archivo_transcript.json   ← transcripción con timestamps por segmento
```

---

## Modelos disponibles

| Modelo | Tamaño | Velocidad (GPU) | Precisión | VRAM mínima |
|---|---|---|---|---|
| `tiny` | 75 MB | muy rápido | ⭐⭐ | 1 GB |
| `base` | 142 MB | rápido | ⭐⭐⭐ | 1 GB |
| `small` | 461 MB | moderado | ⭐⭐⭐⭐ | 2 GB |
| `medium` | 1.5 GB | lento | ⭐⭐⭐⭐⭐ | 5 GB |
| `large` | 2.9 GB | muy lento | ⭐⭐⭐⭐⭐⭐ | 10 GB |

> Recomendado para reuniones en español/inglés mezclado: **`medium`**

---

## Formatos de audio soportados

`.mp3` `.wav` `.m4a` `.ogg` `.flac` `.mp4`

---

## Estructura del proyecto

```
transcriptor/
├── venv/                  # Entorno virtual (no subir al repo)
├── transcriptor.py        # Script principal
├── requirements.txt       # Dependencias Python
├── .gitignore             # Excluye venv, modelos y archivos sensibles
└── README.md              # Este archivo
```

---

## Ejemplo de salida en terminal

```
============================================================
🎙️  TRANSCRIPTOR DE AUDIO - Whisper
============================================================

  Dispositivo : CUDA
  Modelo      : medium
  Archivo     : reunion-equipo.mp4

  Analizando archivo de audio...
  Duración audio   : 45m 12s
  ⏱️  Tiempo estimado : ~7m 32s

  Cargando modelo 'medium'...
  ✅ Modelo cargado

  Iniciando transcripción...
  ⠙ Procesando audio...
  ✅ Audio procesado.

  Guardando archivos...
  📄 Word guardado en: ...
  📋 JSON guardado en: ...

============================================================
✅  TRANSCRIPCIÓN COMPLETADA
============================================================
  Duración audio    : 45m 12s
  Tiempo estimado   : ~7m 32s
  Tiempo real       : 8m 14s
  Velocidad         : 5.5x tiempo real
============================================================
```

---

## Consideraciones de seguridad

- El audio se procesa **100% en local**, no se envía a ningún servidor externo
- Los archivos de transcripción se guardan en la misma carpeta que el audio original
- No incluyas archivos de audio con información sensible en el repositorio (están excluidos por `.gitignore`)

---

## Solución de problemas

**`python` no se reconoce en Windows**
→ Dos pasos: (1) Desactiva los alias en "Manage app execution aliases" → pon `python.exe` y `python3.exe` en Off. (2) Si sigue sin funcionar, añade manualmente al PATH las rutas `...\Python311` y `...\Python311\Scripts` como se describe en la sección de instalación de Python.

**`CUDA out of memory`**
→ Usa un modelo más pequeño (`small`) o fuerza CPU: cambia `device=device` por `device="cpu"` en la línea `load_model`

**FFmpeg no encontrado**
→ Reinstala con `winget install ffmpeg` y abre una terminal nueva

**El modelo tarda mucho en arrancar la primera vez**
→ Normal, Whisper descarga el modelo (~460MB para `small`, ~1.5GB para `medium`). Las siguientes ejecuciones arrancan instantáneamente.