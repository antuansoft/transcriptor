# 🎬 Subtitle Generator — Whisper Local

Herramienta local basada en [OpenAI Whisper](https://github.com/openai/whisper) que genera subtítulos en formato `.srt` **en inglés** a partir de archivos de audio o vídeo (películas, series, reuniones, etc.).

El archivo `.srt` se guarda junto al vídeo con su mismo nombre, de modo que reproductores como VLC o MPC-HC lo cargan automáticamente. El programa **no modifica ni regraba el vídeo**.

Es un programa independiente: tiene su propio script, sus propios requisitos y no depende de ningún otro módulo del repositorio.

---

## Requisitos previos

| Requisito | Versión | Notas |
|---|---|---|
| Python | 3.10 – 3.12 | Ver instrucciones abajo |
| Git | cualquiera | [git-scm.com](https://git-scm.com/) |
| FFmpeg | cualquiera | Ver instrucciones abajo (incluye `ffprobe`) |
| GPU NVIDIA (opcional) | — | Sin GPU funciona en CPU, bastante más lento |

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
cd transcriptor/subtitle-generator
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
ffprobe -version
```

---

## Uso

Hay dos formas de indicar qué archivos procesar. Se pueden procesar **varios archivos en una misma ejecución**: el modelo se carga una sola vez y se van procesando en orden.

### Opción A: por línea de comandos

```bash
python subtitle_generator.py "C:\peliculas\pelicula.mkv"
python subtitle_generator.py pelicula1.mkv pelicula2.mp4 episodio.avi
```

### Opción B: editando el script

Rellena la lista `AUDIO_PATHS` al inicio de `subtitle_generator.py` y ejecuta sin argumentos:

```python
AUDIO_PATHS = [
    r"C:\peliculas\pelicula1.mkv",
    r"C:\peliculas\pelicula2.mp4",
]
```

```bash
python subtitle_generator.py
```

Si se pasan archivos por línea de comandos, sustituyen a la lista `AUDIO_PATHS`.

### Resultado

El subtítulo se genera en la **misma carpeta que el archivo original**, con el mismo nombre:

```
pelicula.mkv
pelicula.srt   ← subtítulos en inglés
```

Si ya existe un `.srt` con ese nombre, se sobrescribe (el programa lo avisa).

---

## Opciones disponibles

| Opción | Descripción | Por defecto |
|---|---|---|
| `archivos` | Uno o varios archivos a procesar | `AUDIO_PATHS` del script |
| `-m`, `--model` | Modelo de Whisper: `tiny`, `base`, `small`, `medium`, `large` | `medium` |
| `--device` | Fuerza `cuda` o `cpu` | `cuda` si está disponible, si no `cpu` |
| `-o`, `--output-dir` | Carpeta donde guardar los `.srt` | Misma carpeta que cada archivo |
| `--max-chars` | Caracteres máximos por línea de subtítulo | `42` |
| `--max-lines` | Líneas máximas por subtítulo | `2` |
| `--word-timestamps` | Usa tiempos por palabra para cortes más precisos (algo más lento) | desactivado |
| `-h`, `--help` | Muestra la ayuda | — |

Ejemplos:

```bash
# Modelo más preciso y subtítulos guardados en otra carpeta
python subtitle_generator.py pelicula.mkv -m large -o C:\subtitulos

# Forzar CPU y cortes precisos por palabra
python subtitle_generator.py pelicula.mkv --device cpu --word-timestamps

# Líneas más cortas
python subtitle_generator.py pelicula.mkv --max-chars 32
```

Las constantes `MODELO`, `IDIOMA`, `MAX_CHARS` y `MAX_LINEAS` al inicio del script definen los valores por defecto.

> El idioma es siempre **inglés** (`IDIOMA = "en"`). Si el audio está en otro idioma, el resultado no será fiable.

---

## Modelos disponibles

| Modelo | Tamaño | Velocidad (GPU) | Precisión | VRAM mínima |
|---|---|---|---|---|
| `tiny` | 75 MB | muy rápido | ⭐⭐ | 1 GB |
| `base` | 142 MB | rápido | ⭐⭐⭐ | 1 GB |
| `small` | 461 MB | moderado | ⭐⭐⭐⭐ | 2 GB |
| `medium` | 1.5 GB | lento | ⭐⭐⭐⭐⭐ | 5 GB |
| `large` | 2.9 GB | muy lento | ⭐⭐⭐⭐⭐⭐ | 10 GB |

> Para películas, `large` suele dar mejor resultado con música y ruido de fondo, a costa de tardar más. Una película de 2 horas con `medium` en GPU tarda del orden de 20 minutos; en CPU, bastante más.

---

## Formatos soportados

**Audio:** `.mp3` `.wav` `.m4a` `.ogg` `.flac` `.aac` `.wma` `.opus`

**Vídeo:** `.mp4` `.mkv` `.avi` `.mov` `.webm` `.wmv` `.m4v`

---

## Estructura del proyecto

```
subtitle-generator/
├── venv/                    # Entorno virtual (no subir al repo)
├── subtitle_generator.py    # Script principal
├── requirements.txt         # Dependencias Python
└── README.md                # Este archivo
```

---

## Ejemplo de salida en terminal

```
============================================================
🎬  SUBTITLE GENERATOR - Whisper
============================================================

  Dispositivo : CUDA
  Modelo      : medium
  Idioma      : en
  Archivos    : 1

  Cargando modelo 'medium'...
  ✅ Modelo cargado

============================================================
📁 [1/1] pelicula.mkv
============================================================

  Archivo     : pelicula.mkv
  Duración    : 2h 3m 10s

  Iniciando transcripción...
  Guardando archivo...
  🎬 SRT guardado en: C:\peliculas\pelicula.srt

------------------------------------------------------------
  Duración audio    : 2h 3m 10s
  Tiempo real       : 21m 5s
  Velocidad         : 5.8x tiempo real
  Subtítulos        : 1480
  SRT → C:\peliculas\pelicula.srt
------------------------------------------------------------
```

---

## Cómo se generan los subtítulos

- Whisper transcribe el audio en bloques con su tiempo de inicio y fin.
- Los bloques largos se parten en subtítulos de como máximo `--max-lines` líneas de `--max-chars` caracteres. Los tiempos se reparten proporcionalmente al texto, o según el tiempo real de cada palabra con `--word-timestamps`.
- Se evitan solapes entre subtítulos consecutivos.
- Se desactiva `condition_on_previous_text` para reducir repeticiones y textos inventados en archivos largos.

---

## Limitaciones

- Solo transcribe en el mismo idioma del audio, **inglés**. No traduce de un idioma a otro.
- La música, los efectos, los susurros o las voces superpuestas reducen la precisión.
- En tramos largos sin voz Whisper puede inventar texto. Conviene revisar el resultado.
- No distingue entre hablantes ni indica nombres de personajes.
- Si el vídeo no contiene voz, el programa avisa y no genera el `.srt`.

---

## Consideraciones de seguridad

- El audio se procesa **100% en local**, no se envía a ningún servidor externo
- Los `.srt` se guardan por defecto junto al archivo original
- No incluyas archivos de audio o vídeo con información sensible en el repositorio (están excluidos por `.gitignore`, igual que los `.srt`)

---

## Solución de problemas

**`python` no se reconoce en Windows**
→ Dos pasos: (1) Desactiva los alias en "Manage app execution aliases" → pon `python.exe` y `python3.exe` en Off. (2) Si sigue sin funcionar, añade manualmente al PATH las rutas `...\Python311` y `...\Python311\Scripts` como se describe en la sección de instalación de Python.

**`CUDA out of memory`**
→ Usa un modelo más pequeño (`-m small`) o fuerza CPU con `--device cpu`

**FFmpeg no encontrado**
→ Reinstala con `winget install ffmpeg` y abre una terminal nueva. Whisper necesita `ffmpeg` y el programa usa `ffprobe` para mostrar la duración.

**Los subtítulos salen desfasados o muy largos**
→ Prueba con `--word-timestamps` y reduce `--max-chars`

**Aparecen frases repetidas o inventadas**
→ Usa un modelo mayor (`-m large`) y revisa los tramos sin diálogo

**El modelo tarda mucho en arrancar la primera vez**
→ Normal, Whisper descarga el modelo (~460MB para `small`, ~1.5GB para `medium`). Las siguientes ejecuciones arrancan instantáneamente.
