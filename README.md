# Dictonoto (En desarrollo)

Aplicación de escritorio para **transcribir en tiempo real** el audio de
clases, conferencias y reuniones, y organizar las notas con IA usando tu propia API key.

## Funcionalidades

### IA configurable (LLM)
- Todos los ajustes se guardan en `config/settings.json`.
- Compatible con cualquier API estilo OpenAI.
- La IA **solo se usa para formatear/organizar** el texto; el
  reconocimiento de voz es **100 % local**.

### Transcripción en tiempo real (local)
- **Reconocimiento local** de voz con **faster-whisper** (sin conexión,
  ejecutado en **CPU** para evitar dependencias CUDA).
- **Transcripción en vivo**: el texto bruto de la hoja izquierda se
  actualiza mientras hablas. Se dispara de dos formas:
  - por *pausa de silencio* (cerrar una frase), y
  - por *fragmento máximo* (si hablas sin pausar, se envía un bloque
    parcial para mantener el texto fresco).
- **Medidor de sonido en vivo (VU meter)**: una barra en la barra de
  acciones muestra el nivel de ruido captado por el micrófono durante la
  grabación (verde = bajo, naranja = medio, rojo = alto).
- **Entrada de audio configurable**: elige qué micrófono usar desde los
  ajustes (se detectan automáticamente los dispositivos del sistema).
- **Transcripción completa**: toma toda la nota original (y el capítulo)
  y la reorganiza en sectores, añadiendo detalles omitidos.

### Sectores de la transcripción
Cada capítulo organiza la información en 4 sectores:
1. **Resumen** — síntesis global (solo aparece tras la transcripción completa).
2. **Datos importantes** — fechas, tareas, avisos y cifras clave.
3. **Glosario** — los términos y conceptos abordados.
4. **Cuerpo** — todo lo mencionado, en orden de mención.

### Capítulos y Libros
- **Capítulo**: cada transcripción es un capítulo. Al inicio son 2 hojas
  en blanco con el botón de grabar y los sectores:
  - *Hoja 1*: texto bruto (sin limpiar), en vivo.
  - *Hoja 2*: texto transcrito (editable por el usuario).
  - Las dos hojas se muestran una a la par de la otra.
- **Libro**: conjunto de capítulos. Tiene **nombre, color y descripción**.
- Los formularios de creación/edición (libros, capítulos y ajustes) son
  **páginas inline**; los diálogos modales quedan reservados **solo para
  alertas** (p. ej. confirmación de borrado).

## 🗂 Estructura del proyecto

```
config/           Configuración (IA y grabación) en settings.json
core/             Servicios: IA, biblioteca, grabación, transcripción
data/books/       Persistencia de libros en JSON
models/           Modelos Book y Chapter
ui/components/    Widgets reutilizables (biblioteca, capítulo, sectores)
ui/views/         Páginas inline (libros, capítulos, ajustes IA)
ui/dialogs/       Diálogos (reservados solo para alertas)
main.py           Punto de entrada
app.py            Controlador principal (ventana)
```

## Instalación y ejecución

```bash
# 1. Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python main.py
```

Para una verificación de arquitectura sin abrir la ventana:

```bash
python main.py --test
```

## Configuración de la IA

1. Abre la app y pulsa **⚙ Ajustes** (página de configuración).
2. Introduce el **enlace**, el **modelo** y la **API key**.
3. Ajusta la **temperatura** y el **prompt** si lo deseas.
4. En la misma página puedes:
   - elegir la **entrada de audio (micrófono)**,
   - cambiar el **tiempo de pausa** de la transcripción en vivo,
   - ajustar la **duración máxima del fragmento**,
   - activar o desactivar la **transcripción automática**, y
   - elegir el **modelo Whisper** local (tiny/base/small/medium).
5. Pulsa **Probar conexión** para validar la API antes de guardar.

## Uso

1. Crea un **Libro** (formulario inline) con nombre, color y descripción.
2. Dentro del libro, crea un **Capítulo** y ponle título.
3. Pulsa **● Grabar** y habla. La hoja *Texto bruto* se irá actualizando
   en vivo; tras una pausa (o un fragmento largo) el bloque se integra al
   sector *Cuerpo* formateado por la IA.
4. Al terminar, pulsa **■ Detener**.
5. Pulsa **⟳ Transcripción completa** para reorganizar toda la nota en
   los 4 sectores.
6. El texto de la hoja transcrita (y los sectores) es **editable** y se
   guarda con el botón **Guardar**.

