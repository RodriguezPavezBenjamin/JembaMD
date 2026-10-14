# JembaMD

Convierte documentos a Markdown desde una interfaz local en español.

## Inicio

Haz doble clic en el acceso directo **JembaMD** del escritorio o en **JembaMD.vbs** dentro de esta carpeta. La app se abre en su propia ventana, sin consola ni pestañas del navegador. Al cerrar la ventana se detiene su servidor local. Si vuelves a abrirla cuando ya está funcionando, enfoca la ventana existente.

**iniciar.bat** prepara o repara el entorno Python y también abre la ventana propia. La instalación de dependencias necesita internet. El acceso directo usa el entorno ya instalado.

Si no hay Python disponible, instala Python 3.12 desde https://www.python.org/downloads/ y vuelve a intentarlo. El inicio también puede aprovechar el Python incluido en Codex si está requerido para la ventana de escritorio.

La ventana usa Microsoft Edge WebView2, requerido para la ventana de escritorio. El contenido se procesa en el computador.

El inicio omite el formulario de bienvenida de Streamlit: no necesitas ingresar un correo.

## Uso

1. **Cargar:** arrastra uno o varios archivos y pulsa Continuar.
2. **Convertir:** inicia el proceso. Verás el avance por archivo y página; el OCR local está activado de forma predeterminada.
3. **Revisar:** elige un documento y alterna entre Vista legible y Código Markdown. Los errores aparecen con su explicación.
4. **Guardar:** elige una carpeta y pulsa Guardar carpeta con los .md. El nombre sugerido contiene solo fecha y hora y puedes editarlo antes de guardar. Usa Abrir carpeta para verla en el Explorador.

El menú superior muestra el paso actual y los pasos completados. Puedes retroceder sin perder los archivos. Nuevo lote, arriba a la derecha, limpia la sesión y permite empezar de nuevo. El ZIP es una alternativa opcional.

La ventana normal tiene un tamaño fijo de 1180 × 820 píxeles lógicos. Los cuatro pasos usan el mismo panel, que aprovecha el alto disponible con márgenes uniformes.

Admite PDF con texto o escaneados, DOCX, PPTX, XLSX, XLS, HTML, HTM, TXT, MD, CSV, JSON y XML. Límite: 50 MB por archivo y 200 MB por lote. Los nombres repetidos se numeran para que cada documento tenga su propio .md.

La conversión se realiza localmente, sin servicios de IA ni claves de API. Los originales no se modifican. La app mantiene archivos y resultados en memoria durante la sesión. Las carpetas se guardan en el destino que elijas; el destino inicial es la subcarpeta salidas de JembaMD. Cada entrega incluye los .md, imágenes recuperadas de Word y _resumen.json con avisos y errores. Nunca se sobrescribe una entrega anterior.

## Límites

- El OCR de Windows usa español si está instalado. Los idiomas disponibles dependen de la instalación de Windows. No requiere internet. Las cifras, nombres y tablas reconocidas deben revisarse.
- Markdown conserva texto y estructura básica. Las imágenes incrustadas de Word se guardan con rutas relativas junto al Markdown. El diseño exacto, las fórmulas y las tablas complejas pueden no conservarse. El OCR de PDF extrae texto por páginas, no reconstruye el diseño original.
- Algunos PDF pueden extraer texto parcial o desordenado. Revisa la vista previa.
- Los formatos antiguos DOC y PPT no están incluidos: guárdalos como DOCX y PPTX primero.
- Si un documento falla, los otros siguen convirtiéndose.

## Compartir con amigos

Envía `para_compartir/JembaMD-Windows-x64.zip`. Incluye `JembaMD.exe`, Python y las dependencias. Deben extraer todo el ZIP y abrir el ejecutable; no deben moverlo separado de las carpetas. Edición para Windows 10/11 x64, con WebView2 y un idioma OCR de Windows para PDF escaneados. Dentro del ZIP está `LEEME.txt` con las instrucciones. El paquete excluye documentos, salidas y registros de uso.

La construcción está en `empaquetado/crear_portable.py` y usa el Python base y las dependencias del entorno local. Primero crea una carpeta nueva, permite probarla y luego `--zip` comprime solo los archivos distribuibles. El iniciador se compila desde `empaquetado/Launcher.cs` con el compilador de .NET Framework de Windows.

## Código

Código principal: src/app.py. Conversión y exportación: src/conversor.py. OCR de PDF: src/ocr_local.py. Ventana y servidor: src/escritorio.py. Selector de carpetas: src/puente.py y src/puente_servidor.py (canal local autenticado por instancia). Dependencias: requirements.txt. Tema pixel art: src/tema.py y assets/tema.css. Logo activo: assets/jembamd-pixel.png. Icono de Windows: assets/jembamd-pixel.ico. Fondo ilustrado: assets/noche-pixel.png. Los recursos anteriores se conservan. Prompts y atribuciones: assets/pixel-origen.md.

Para iniciar manualmente desde esta carpeta en PowerShell:

```powershell
.\.venv\Scripts\python.exe src/escritorio.py
```

Para usar la versión de navegador: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts/iniciar.ps1 -Navegador`.

Si hay un problema de inicio, revisa `.logs/escritorio.log` y `.logs/servidor.log`. Las descargas de la ventana usan el diálogo de guardado de Windows.

Herramientas: [Streamlit](https://docs.streamlit.io/), [MarkItDown](https://github.com/microsoft/markitdown) y [pywebview](https://pywebview.flowrl.com/guide/usage.html).
