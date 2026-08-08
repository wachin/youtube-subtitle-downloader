# Proyecto: interfaz gráfica PyQt6 completa para descargar subtítulos de YouTube mediante yt-dlp

Quiero que desarrolles una aplicación de escritorio completa, profesional y mantenible escrita en **Python 3 + PyQt6**, destinada principalmente a Linux Debian, Ubuntu, MX Linux y derivados.

La aplicación debe utilizar **yt-dlp** como motor para consultar y descargar subtítulos de YouTube.

El objetivo es que un usuario que no conoce la línea de comandos pueda pegar la URL de un video de YouTube, consultar los subtítulos disponibles, seleccionar uno o varios idiomas y descargarlos fácilmente.

Quiero que el proyecto tenga calidad suficiente para poder publicarlo como software libre en GitHub y eventualmente empaquetarlo para Debian.

---

> **Estado del proyecto**
>
> Cada parte numerada de este documento dispone de una casilla de verificación `[ ]` en su encabezado.
> Durante el proceso de construcción del programa, cada parte completada se marcará como `[x]`.
> Las casillas del resumen de implementación de la sección 63 también se marcarán conforme se avance.

---

## [ ] 1. Filosofía del proyecto

No quiero simplemente una pequeña ventana que ejecute un comando.

Quiero una aplicación de escritorio bien diseñada, modular, robusta y ampliable.

Debe:

* utilizar PyQt6;
* utilizar yt-dlp como backend;
* tener arquitectura modular;
* no congelar la interfaz durante las operaciones;
* manejar correctamente errores;
* mostrar información clara al usuario;
* estar preparada para internacionalización;
* guardar preferencias;
* permitir descargar varios subtítulos;
* permitir convertirlos a diferentes formatos;
* permitir obtener texto limpio a partir de los subtítulos;
* funcionar correctamente con subtítulos manuales y automáticos.

Evita dependencias innecesarias.

Siempre que sea razonable, utiliza Python y Qt en lugar de añadir bibliotecas externas.

---

# [ ] 2. Flujo principal

La interfaz principal debe ser extremadamente sencilla de entender.

En la parte superior:

```text
URL del video de YouTube:
[ https://www.youtube.com/watch?v=...................... ] [Analizar]
```

El usuario:

1. pega una URL;
2. pulsa **Analizar**;
3. el programa consulta yt-dlp;
4. obtiene información del video;
5. muestra los subtítulos disponibles;
6. el usuario selecciona uno o varios;
7. elige formato y opciones;
8. pulsa **Descargar**.

También debe ser posible pegar la URL y presionar Enter.

---

# [ ] 3. Información del video

Después de analizar la URL mostrar, cuando yt-dlp proporcione los datos:

* miniatura;
* título;
* nombre del canal;
* duración;
* ID del video;
* URL;
* fecha de publicación si está disponible.

La miniatura debe cargarse sin bloquear la GUI.

Si no puede obtenerse la imagen, la aplicación debe seguir funcionando normalmente.

---

# [ ] 4. Lista de subtítulos

Esta es una de las partes más importantes.

No quiero que se analice la salida textual de:

```bash
yt-dlp --list-subs URL
```

mediante expresiones regulares si puede evitarse.

Utiliza preferentemente la API Python de yt-dlp o su información JSON estructurada.

Debes distinguir claramente entre:

## Subtítulos proporcionados por el creador

Correspondientes a:

```text
subtitles
```

de yt-dlp.

## Subtítulos automáticos

Correspondientes a:

```text
automatic_captions
```

de yt-dlp.

La GUI debería presentar pestañas como:

```text
[Todos] [Subtítulos] [Automáticos]
```

o una organización equivalente claramente comprensible.

---

# [ ] 5. Tabla de idiomas

Utilizar una tabla `QTableView` o un componente adecuado.

Columnas sugeridas:

```text
☑
Idioma
Código
Tipo
Formatos disponibles
```

Ejemplo:

```text
☐ Spanish (Original)    es-orig    Automático    SRT, VTT, TTML, JSON3
☐ Spanish               es         Automático    SRT, VTT, TTML, JSON3
☐ English               en         Automático    SRT, VTT, TTML, JSON3
```

No asumir que los códigos de idioma siempre son solamente de dos letras.

Debe soportar correctamente códigos como:

```text
es
es-orig
pt-BR
pt-PT
zh-Hans
zh-Hant
en-US
```

y otros que yt-dlp pueda devolver.

---

# [ ] 6. Selección de subtítulos

Permitir:

* seleccionar un subtítulo;
* seleccionar varios;
* seleccionar todos;
* deseleccionar todos;
* seleccionar únicamente subtítulos manuales;
* seleccionar únicamente automáticos.

Añadir búsqueda/filtro por idioma.

Por ejemplo:

```text
Buscar idioma:
[ español________________ ]
```

La búsqueda debería aceptar:

```text
Spanish
Español
es
es-orig
```

en la medida en que los datos disponibles lo permitan.

---

# [ ] 7. Distinguir idioma original

Cuando yt-dlp devuelva algo como:

```text
es-orig    Spanish (Original)
es         Spanish
```

mostrarlo claramente.

No asumir que `-orig` siempre significa español.

Puede ser cualquier idioma.

Destacar visualmente el idioma original mediante una pequeña etiqueta:

```text
Original
```

sin hacer difícil la lectura de la tabla.

---

# [ ] 8. Formato de descarga

Permitir elegir:

```text
SRT
VTT
TTML
JSON3
Formato original
```

Si un determinado formato no está disponible para un subtítulo, manejarlo correctamente.

El programa debe comprobar qué formatos proporciona yt-dlp.

No debe asumir que todos los videos tienen exactamente los mismos formatos.

---

# [ ] 9. Texto limpio TXT

Añadir una opción muy importante:

```text
☑ Crear también archivo TXT limpio
```

El archivo TXT debe contener únicamente lo hablado, sin:

* números de secuencia SRT;
* timestamps;
* etiquetas HTML;
* etiquetas VTT;
* metadata;
* códigos internos.

Ejemplo de SRT:

```text
1
00:00:01,000 --> 00:00:04,000
Hola, bienvenidos a este video.

2
00:00:03,500 --> 00:00:07,000
bienvenidos a este video. Hoy vamos
```

El TXT NO debería terminar como:

```text
Hola, bienvenidos a este video.
bienvenidos a este video. Hoy vamos
```

Debe intentar eliminar correctamente las repeticiones provocadas por los subtítulos automáticos incrementales de YouTube.

Resultado deseado:

```text
Hola, bienvenidos a este video. Hoy vamos...
```

Implementa esta funcionalidad en un módulo independiente para que posteriormente pueda mejorarse.

---

# [ ] 10. Modos para TXT

Añadir varias posibilidades:

```text
Texto continuo
Párrafos
Una línea por subtítulo
```

Por ejemplo:

### Texto continuo

```text
Hola a todos. Bienvenidos al canal. Hoy vamos a aprender...
```

### Párrafos

Intentar crear bloques legibles.

### Una línea por subtítulo

Mantener una estructura cercana al subtítulo original, pero sin timestamps.

---

# [ ] 11. Carpeta de destino

Permitir elegir la carpeta de descarga mediante:

```text
Guardar en:
[/home/usuario/Videos/Subtitulos____________] [Examinar...]
```

Recordar la última carpeta utilizada.

Por defecto se puede utilizar una carpeta apropiada del usuario.

Nunca codificar `/home/nombreusuario`.

Utilizar APIs de Qt/Python para encontrar las carpetas del usuario.

---

# [ ] 12. Nombre del archivo

Permitir elegir una plantilla.

Por ejemplo:

```text
%(title)s [%(id)s].%(language)s.%(ext)s
```

También ofrecer presets amigables:

```text
Título - idioma
Título [ID] - idioma
ID - idioma
```

Sanear nombres de archivo correctamente.

---

# [ ] 13. Vista previa

Añadir un botón:

```text
Vista previa
```

Después de obtener o descargar el subtítulo debe permitir abrir una ventana donde se pueda leer.

La ventana debe contener:

* editor de texto de solo lectura;
* búsqueda;
* siguiente coincidencia;
* anterior coincidencia;
* copiar;
* seleccionar todo;
* guardar como;
* información del idioma.

---

# [ ] 14. Descarga múltiple

Si selecciono:

```text
es-orig
es
en
```

el programa debe poder descargar los tres en una sola operación.

Mostrar progreso individual.

Ejemplo:

```text
Spanish (Original)       Completado
Spanish                  Completado
English                  Descargando...
```

---

# [ ] 15. Barra de progreso

Mostrar:

* progreso general;
* estado actual;
* archivo que se está procesando.

Aunque la descarga de subtítulos normalmente sea muy rápida, quiero una arquitectura preparada para operaciones más largas.

---

# [ ] 16. No congelar la GUI

REQUISITO IMPORTANTE.

Nunca ejecutar operaciones pesadas de yt-dlp en el hilo principal de Qt.

Utilizar correctamente:

* `QThread`;
* worker objects;
* signals/slots;

o una solución equivalente adecuada en PyQt6.

La interfaz debe permanecer responsiva mientras yt-dlp:

* analiza videos;
* obtiene metadata;
* descarga subtítulos;
* descarga miniaturas.

---

# [ ] 17. Cancelar operaciones

Añadir botón:

```text
Cancelar
```

cuando haya una operación en progreso.

La cancelación debe implementarse de manera segura.

No utilizar `terminate()` de `QThread` como mecanismo normal de cancelación.

Implementar una bandera/token de cancelación y hacer que los workers finalicen limpiamente.

---

# [ ] 18. Registro de actividad

Añadir un panel desplegable:

```text
Detalles / Registro
```

donde aparezcan mensajes como:

```text
Analizando URL...
Video encontrado.
143 subtítulos automáticos encontrados.
2 subtítulos manuales encontrados.
Descargando es-orig...
Guardado en ...
```

También mostrar mensajes relevantes de yt-dlp.

Permitir:

* copiar registro;
* limpiar registro.

---

# [ ] 19. Manejo de errores

Crear mensajes amigables para problemas como:

* URL inválida;
* video inexistente;
* video privado;
* video eliminado;
* restricción por edad;
* necesidad de autenticación;
* YouTube solicita iniciar sesión;
* error de red;
* conexión interrumpida;
* yt-dlp no instalado;
* yt-dlp demasiado antiguo;
* subtítulo ya no disponible;
* error escribiendo en disco;
* permisos insuficientes;
* carpeta inexistente.

No mostrar únicamente traceback Python al usuario.

Guardar información técnica en el log.

---

# [ ] 20. Cookies de navegador

Preparar soporte opcional para:

```bash
--cookies-from-browser
```

La GUI podría incluir:

```text
Configuración
  → YouTube
      Cookies del navegador:
      [Ninguna ▼]
      Firefox
      Chromium
      Chrome
      Brave
```

Esto puede ser necesario para determinados videos.

No debe estar activado por defecto.

No copiar ni manipular cookies manualmente.

Usar las capacidades de yt-dlp.

---

# [ ] 21. Archivo cookies.txt

Opcionalmente permitir:

```text
Archivo de cookies:
[ cookies.txt ] [Examinar...]
```

Nunca mostrar el contenido de las cookies.

Tratarlo como información sensible.

---

# [ ] 22. Configuración de yt-dlp

La aplicación debe detectar si `yt-dlp` está disponible.

Mostrar en:

```text
Ayuda → Información del sistema
```

datos como:

```text
Python:
PyQt6:
yt-dlp:
FFmpeg:
Sistema operativo:
```

Ejemplo:

```text
Python 3.13
PyQt6 6.x
yt-dlp 2026.xx.xx
FFmpeg 7.x
Debian GNU/Linux
```

---

# [ ] 23. API Python de yt-dlp

Siempre que sea razonable, preferir:

```python
from yt_dlp import YoutubeDL
```

frente a ejecutar y analizar cadenas producidas por el ejecutable.

La información del video debe obtenerse de forma estructurada mediante algo equivalente a:

```python
with YoutubeDL(options) as ydl:
    info = ydl.extract_info(url, download=False)
```

Investiga y utiliza correctamente las APIs actuales de yt-dlp.

No dependas de detalles privados de yt-dlp innecesariamente.

---

# [ ] 24. Compatibilidad con actualizaciones

yt-dlp cambia con cierta frecuencia.

Por eso:

* aislar toda interacción con yt-dlp en un módulo backend;
* no mezclar llamadas a yt-dlp con widgets Qt;
* crear una capa de servicios.

Por ejemplo:

```text
services/
    ytdlp_service.py
```

Debe ser posible adaptar el proyecto a cambios futuros de yt-dlp modificando principalmente este módulo.

---

# [ ] 25. Arquitectura

Quiero una estructura aproximada como:

```text
youtube-subtitle-downloader/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── src/
│   └── youtube_subtitle_downloader/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       │
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── preview_dialog.py
│       │   ├── settings_dialog.py
│       │   └── about_dialog.py
│       │
│       ├── models/
│       │   ├── subtitle.py
│       │   └── video.py
│       │
│       ├── services/
│       │   ├── ytdlp_service.py
│       │   ├── subtitle_service.py
│       │   └── settings_service.py
│       │
│       ├── workers/
│       │   ├── video_info_worker.py
│       │   └── download_worker.py
│       │
│       ├── utils/
│       │   ├── paths.py
│       │   ├── filenames.py
│       │   └── logging.py
│       │
│       ├── resources/
│       │   ├── icons/
│       │   └── translations/
│       │
│       └── i18n/
│
├── tests/
│   ├── test_subtitle_parser.py
│   ├── test_filename.py
│   └── ...
│
├── packaging/
│   └── debian/
│
└── docs/
```

Puedes mejorar esta estructura si tienes una razón técnica clara.

---

# [ ] 26. MVC/MVVM

Separar claramente:

* presentación;
* modelos;
* lógica;
* acceso a yt-dlp.

No colocar toda la aplicación dentro de `main.py`.

No crear un archivo de miles de líneas.

---

# [ ] 27. Configuración persistente

Utilizar `QSettings`.

Guardar:

* geometría de ventana;
* posición;
* carpeta de salida;
* formato preferido;
* opciones TXT;
* navegador para cookies;
* plantilla de nombres;
* preferencias generales.

Usar correctamente organización y nombre de aplicación.

---

# [ ] 28. Historial

Añadir historial opcional de videos procesados.

Por cada elemento:

```text
Fecha
Título
URL
Idiomas descargados
Carpeta
```

Debe poder:

* volver a abrir la URL;
* abrir carpeta;
* copiar URL;
* eliminar una entrada;
* borrar todo el historial.

Permitir desactivar el historial desde Configuración → Privacidad.

---

# [ ] 29. Drag & Drop

Permitir arrastrar hacia la ventana texto que contenga una URL de YouTube.

Si se detecta una URL válida, colocarla automáticamente en el campo.

---

# [ ] 30. Portapapeles

Añadir botón:

```text
Pegar URL
```

Si el portapapeles contiene una URL válida de YouTube, pegarla.

Opcionalmente ofrecer:

```text
Analizar automáticamente después de pegar
```

en Configuración.

---

# [ ] 31. URLs soportadas

No asumir únicamente:

```text
youtube.com/watch?v=
```

Permitir que yt-dlp reconozca formas como:

```text
https://youtu.be/...
https://www.youtube.com/watch?v=...
https://youtube.com/shorts/...
```

y otras URLs de YouTube que yt-dlp soporte.

La validación local debe ser permisiva.

La validación definitiva debe hacerla yt-dlp.

---

# [ ] 32. Playlists

Preparar arquitectura para playlists.

Inicialmente se puede mostrar una advertencia:

```text
Esta URL pertenece a una lista de reproducción.

○ Analizar solo este video
○ Analizar toda la lista
```

Si implementar playlists no complica excesivamente el MVP, implementarlo.

Para una lista:

```text
Video | Canal | Duración | Subtítulos
```

y permitir seleccionar videos.

Sin embargo, la funcionalidad de un video individual tiene prioridad.

---

# [ ] 33. Tema

La aplicación debe respetar el tema Qt/escritorio del sistema.

No imponer una paleta propia.

Debe funcionar correctamente con:

* tema claro;
* tema oscuro.

No utilizar colores codificados que hagan ilegible el programa bajo determinados temas.

---

# [ ] 34. Iconos

Preferir iconos del tema del sistema mediante:

```python
QIcon.fromTheme()
```

cuando existan.

Proporcionar fallback únicamente cuando sea necesario.

---

# [ ] 35. Accesibilidad

Añadir:

* tooltips;
* shortcuts;
* textos accesibles;
* orden lógico de tabulación;
* soporte de teclado.

Shortcuts sugeridos:

```text
Ctrl+L       URL
Ctrl+V       Pegar URL
Ctrl+D       Descargar
Ctrl+F       Buscar
Ctrl+,       Configuración
Ctrl+Q       Salir
F1           Ayuda
```

No interceptar `Ctrl+V` globalmente de manera que impida pegar normalmente en otros campos.

---

# [ ] 36. Internacionalización

El **idioma principal de la aplicación es el inglés**.

La aplicación se desarrolla primero por completo en inglés.

Una vez terminada y funcional, se añade la traducción a otros idiomas mediante internacionalización con **Qt Linguist**.

La primera traducción será al **español**.

Soporte multiidioma desde el principio mediante:

```text
Qt Linguist
QTranslator
.tr
.ts
.qm
```

Todos los textos visibles deben utilizar `tr()` o el mecanismo apropiado desde el principio, de modo que añadir traducciones después resulte sencillo.

Idiomas iniciales:

```text
English (idioma principal)
Español (primera traducción)
```

La arquitectura debe permitir añadir fácilmente:

```text
Português
Français
Deutsch
Italiano
etc.
```

El idioma por defecto es el **inglés**; mientras no exista traducción a otro idioma, la aplicación se muestra siempre en inglés.

Permitir cambiar el idioma desde:

```text
Configuración → General → Idioma
```

---

# [ ] 37. Ventana principal

Diseñar una ventana limpia.

Propuesta:

```text
┌──────────────────────────────────────────────────────────────┐
│ Archivo    Herramientas    Ayuda                             │
├──────────────────────────────────────────────────────────────┤
│ URL: [_______________________________________] [Analizar]    │
├──────────────────────────────────────────────────────────────┤
│ [miniatura]  Título del video                                │
│              Canal                                           │
│              12:35                                           │
├──────────────────────────────────────────────────────────────┤
│ Buscar idioma: [________________________]                    │
│                                                              │
│ [Todos] [Subtítulos] [Automáticos]                           │
│                                                              │
│ ☑ │ Idioma              │ Código │ Tipo       │ Formatos    │
│ ──┼─────────────────────┼────────┼────────────┼──────────── │
│ ☐ │ Spanish (Original)  │es-orig │Automático  │SRT,VTT,... │
│ ☐ │ Spanish             │es      │Automático  │SRT,VTT,... │
│ ☐ │ English             │en      │Automático  │SRT,VTT,... │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Formato: [SRT ▼]                                             │
│ ☑ Crear TXT limpio                                           │
│ Guardar en: [____________________________] [Examinar]         │
│                                                              │
│                 [Cancelar] [Descargar seleccionados]         │
├──────────────────────────────────────────────────────────────┤
│ Estado: Listo                                                │
│ [████████████████████████████████████████████████████]       │
└──────────────────────────────────────────────────────────────┘
```

Es solamente una guía. Mejora el diseño cuando sea conveniente.

---

# [ ] 38. Barra de estado

Mostrar mensajes como:

```text
Listo
Analizando video...
152 idiomas encontrados
Descargando Spanish (Original)...
Descarga completada
```

---

# [ ] 39. Menús

## Archivo

```text
Nueva URL
Abrir carpeta de descargas
Historial
Salir
```

## Herramientas

```text
Configuración
Comprobar yt-dlp
```

## Ayuda

```text
Ayuda
Información del sistema
Acerca de
```

---

# [ ] 40. Actualización de yt-dlp

No implementar actualizaciones automáticas destructivas.

Mostrar la versión instalada.

Opcionalmente permitir comprobar si existe una versión nueva.

Debe tenerse en cuenta que yt-dlp podría haberse instalado mediante:

* apt;
* pip;
* pipx;
* paquete de distribución.

Por tanto, no ejecutar automáticamente:

```bash
pip install -U yt-dlp
```

porque podría romper paquetes administrados por Debian.

En su lugar explicar al usuario cómo actualizar según su instalación.

---

# [ ] 41. Debian

Diseñar el proyecto pensando en futuras políticas Debian.

Evitar:

* descargar código ejecutable en runtime;
* modificar paquetes del sistema;
* ejecutar sudo;
* modificar `/usr`;
* instalar dependencias automáticamente.

Las dependencias deben declararse correctamente.

---

# [ ] 42. Instalación para desarrollo

Documentar al menos:

```bash
sudo apt install python3 python3-pyqt6 python3-pip ffmpeg
```

Verificar los nombres actuales de los paquetes en Debian.

Para entorno virtual proporcionar instrucciones apropiadas.

---

# [ ] 43. pyproject.toml

Utilizar un `pyproject.toml` moderno.

Definir:

* metadata;
* dependencias;
* entry point;
* versión;
* licencia;
* autores genéricos/placeholders cuando corresponda.

Debe poder instalarse con un comando equivalente a:

```bash
pip install .
```

y ejecutarse con algo similar a:

```bash
youtube-subtitle-downloader
```

---

# [ ] 44. Licencia

Preparar el proyecto como software libre.

Utilizar inicialmente:

```text
GPL-3.0-or-later
```

salvo que exista una incompatibilidad técnica que debas comunicar.

Crear archivo:

```text
LICENSE
```

---

# [ ] 45. README.md

Crear un README profesional incluyendo:

* descripción;
* características;
* captura de pantalla mediante placeholder inicialmente;
* requisitos;
* instalación;
* uso;
* formatos;
* subtítulos automáticos;
* texto limpio;
* privacidad;
* cookies;
* solución de problemas;
* desarrollo;
* traducciones;
* empaquetado;
* licencia.

Explicar claramente que la aplicación utiliza yt-dlp.

---

# [ ] 46. Privacidad

La aplicación debe funcionar localmente.

Explicar que:

* las URLs se envían a los servidores requeridos por YouTube/yt-dlp para consultar el contenido;
* los archivos se guardan localmente;
* la aplicación no debe incorporar telemetría propia;
* el historial puede desactivarse.

---

# [ ] 47. Logs

Guardar logs técnicos utilizando el módulo estándar `logging`.

Usar una ruta apropiada bajo las carpetas de datos/cache del usuario.

Implementar rotación o limitar el crecimiento.

No registrar cookies.

No registrar datos sensibles innecesariamente.

---

# [ ] 48. Pruebas

Implementar pruebas para la lógica que pueda probarse sin GUI.

Especialmente:

* procesamiento SRT;
* procesamiento VTT;
* eliminación de repeticiones;
* generación TXT;
* nombres de archivo;
* detección de idiomas;
* clasificación manual/automático.

No realizar llamadas reales a YouTube durante las pruebas unitarias.

Usar mocks/fixtures.

---

# [ ] 49. Dataset de prueba para subtítulos automáticos

Crear fixtures pequeños que reproduzcan el problema de frases solapadas de YouTube.

Ejemplo conceptual:

```text
Hola
Hola amigos
Hola amigos bienvenidos
amigos bienvenidos al canal
```

El algoritmo debe generar algo parecido a:

```text
Hola amigos bienvenidos al canal
```

sin repetir innecesariamente las palabras.

No hacer el algoritmo demasiado agresivo, ya que podría eliminar repeticiones legítimas del hablante.

Añadir pruebas para estos casos.

---

# [ ] 50. Seguridad

No construir comandos shell concatenando directamente URLs suministradas por el usuario.

Si se necesita `subprocess`, utilizar argumentos como lista y `shell=False`.

Preferiblemente utilizar directamente la API Python de yt-dlp.

Sanear nombres de archivos.

No permitir path traversal mediante títulos de YouTube.

---

# [ ] 51. Operaciones al terminar

Después de descargar mostrar:

```text
Descarga completada.

3 subtítulos descargados.

[Ver archivos]
[Abrir carpeta]
[Cerrar]
```

No abrir archivos automáticamente salvo que el usuario lo configure.

---

# [ ] 52. Notificaciones

Opcionalmente emitir una notificación del escritorio cuando finalice una descarga y la ventana no esté activa.

Implementar esto únicamente si puede hacerse correctamente sin añadir dependencias pesadas.

---

# [ ] 53. CLI opcional

Como la lógica debe estar separada, considerar proporcionar además una pequeña CLI:

```bash
youtube-subtitle-downloader-cli URL --lang es-orig --format srt
```

pero la GUI es la prioridad.

---

# [ ] 54. Calidad de código

Aplicar:

* type hints;
* dataclasses cuando sean apropiadas;
* docstrings útiles;
* nombres descriptivos;
* separación de responsabilidades;
* manejo explícito de excepciones.

Evitar:

```python
except Exception:
    pass
```

y otros patrones que silencien errores.

---

# [ ] 55. Estilo

Preparar configuración para herramientas como:

```text
black
ruff
pytest
mypy
```

cuando sea razonable.

No obligar al usuario final a instalarlas.

Son dependencias de desarrollo.

---

# [ ] 56. Primera ejecución

Si falta yt-dlp, mostrar algo como:

```text
No se encontró yt-dlp.

Esta aplicación utiliza yt-dlp para comunicarse con YouTube.

En Debian/Ubuntu puede instalarlo mediante el gestor de paquetes
de su distribución o siguiendo la documentación oficial de yt-dlp.
```

No instalarlo automáticamente.

---

# [ ] 57. FFmpeg

Los subtítulos pueden descargarse directamente en determinados formatos, así que FFmpeg no debe ser requisito absoluto si no hace falta.

Detectarlo independientemente.

Explicar qué funcionalidades requieren FFmpeg si alguna característica realmente lo necesita.

---

# [ ] 58. Casos reales que debe soportar

Debes comprobar conceptualmente este caso real.

Una ejecución de:

```bash
yt-dlp --list-subs "https://www.youtube.com/watch?v=W2nxqwzsy3A"
```

puede mostrar:

```text
Available automatic captions
...
es-orig   Spanish (Original)   vtt, srt, ttml, srv3, srv2, srv1, json3
es        Spanish              vtt, srt, ttml, srv3, srv2, srv1, json3
...
```

y terminar con:

```text
W2nxqwzsy3A has no subtitles
```

Esto NO significa que no existan subtítulos utilizables.

Significa que no existen subtítulos manuales, mientras que sí existen `automatic_captions`.

La aplicación debe interpretar correctamente esta situación y mostrar los subtítulos automáticos.

Nunca debe mostrar erróneamente:

```text
No existen subtítulos
```

si `automatic_captions` contiene elementos.

---

# [ ] 59. Prioridad del idioma original

Cuando exista algo equivalente a:

```text
es-orig
```

puede colocarse al principio de la lista o marcarse como:

```text
Original
```

pero no seleccionarlo automáticamente si el usuario ha configurado otra preferencia.

En Configuración se puede añadir:

```text
Idioma preferido:
Automático según sistema
Español
English
...
```

---

# [ ] 60. Exportación avanzada

Preparar arquitectura para que en una versión posterior puedan añadirse:

```text
Markdown
HTML
DOCX
PDF
```

No es obligatorio implementar DOCX/PDF ahora.

Sí quiero desde la primera versión:

```text
SRT
VTT
TTML
JSON3
TXT limpio
```

si los datos originales necesarios están disponibles.

---

# [ ] 61. Copiar transcripción

Añadir una acción:

```text
Copiar texto limpio al portapapeles
```

desde la ventana de vista previa.

Esto resulta especialmente útil para pegar posteriormente una transcripción en una aplicación de IA o editor de textos.

---

# [ ] 62. Resumen de objetivos

La aplicación final debe permitir este flujo:

```text
Pegar URL
      ↓
Analizar con yt-dlp
      ↓
Obtener metadata
      ↓
Subtítulos manuales
      +
Subtítulos automáticos
      ↓
Mostrar idiomas
      ↓
Elegir uno o varios
      ↓
Elegir SRT/VTT/etc.
      ↓
Descargar
      ↓
Opcional:
crear TXT limpio
      ↓
Vista previa / copiar / abrir carpeta
```

---

# [ ] 63. Forma de trabajar

No intentes escribir toda la aplicación en un único archivo.

Primero:

- [ ] 1. inspecciona el entorno y versiones disponibles;
- [ ] 2. diseña la arquitectura;
- [ ] 3. crea la estructura del proyecto;
- [ ] 4. implementa los modelos;
- [ ] 5. implementa el servicio yt-dlp;
- [ ] 6. implementa workers;
- [ ] 7. crea la GUI;
- [ ] 8. implementa procesamiento de subtítulos;
- [ ] 9. crea tests;
- [ ] 10. crea documentación;
- [ ] 11. ejecuta tests;
- [ ] 12. ejecuta una prueba básica de la aplicación;
- [ ] 13. corrige errores encontrados.

Si encuentras una decisión importante que no esté especificada, elige la alternativa que produzca una aplicación mantenible y explica la decisión en la documentación.

No elimines funcionalidades simplemente para reducir el trabajo.

Si alguna característica requiere implementarse por fases, deja primero una base funcional sólida y documenta claramente la característica pendiente mediante issues/TODOs específicos.

El resultado debe ser un proyecto real, ejecutable y mantenible, no solamente un prototipo visual.

