"""Conversión local y exportación de documentos a Markdown."""
from io import BytesIO
from pathlib import PurePosixPath
import re
from zipfile import ZIP_DEFLATED, ZipFile, BadZipFile
from pathlib import Path
from datetime import datetime
import json
import base64
import mimetypes

EXTENSIONES = ('pdf', 'docx', 'pptx', 'xlsx', 'xls', 'html', 'htm', 'txt', 'md', 'csv', 'json', 'xml')
LIMITE_BYTES = 50 * 1024 * 1024


def convertir(nombre: str, contenido: bytes, progreso=None, usar_ocr=True) -> str:
    extension = '.' + nombre.rsplit('.', 1)[-1].lower()
    if extension[1:] not in EXTENSIONES:
        raise ValueError('Este formato todavía no está disponible.')
    if not contenido:
        raise ValueError('El archivo está vacío.')
    if len(contenido) > LIMITE_BYTES:
        raise ValueError('El archivo supera el límite de 50 MB.')
    partes = {'.docx': 'word/document.xml', '.pptx': 'ppt/presentation.xml', '.xlsx': 'xl/workbook.xml'}
    if extension in partes:
        try:
            with ZipFile(BytesIO(contenido)) as documento:
                if partes[extension] not in documento.namelist():
                    raise ValueError('El contenido no corresponde al formato indicado por su extensión.')
        except BadZipFile as error:
            raise ValueError('El documento está dañado o no corresponde a su extensión.') from error
    if extension == '.pdf' and b'%PDF-' not in contenido[:1024]:
        raise ValueError('El archivo no contiene una cabecera PDF válida.')
    if extension == '.xls' and not contenido.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        raise ValueError('El archivo no corresponde a un libro XLS compatible. Prueba guardarlo como XLSX.')
    if extension == '.pdf':
        from ocr_local import extraer_pdf
        texto, _ = extraer_pdf(contenido, progreso, usar_ocr)
    elif extension in ('.txt', '.md'):
        if contenido.startswith((b'\xff\xfe', b'\xfe\xff')):
            texto = contenido.decode('utf-16')
        else:
            try:
                texto = contenido.decode('utf-8-sig')
            except UnicodeDecodeError:
                from charset_normalizer import from_bytes
                detectado = from_bytes(contenido).best()
                if detectado is None:
                    raise ValueError('No se pudo reconocer la codificación del texto.')
                texto = str(detectado)
    else:
        from markitdown import MarkItDown
        resultado = MarkItDown(enable_plugins=False).convert_stream(
            BytesIO(contenido), file_extension=extension
        )
        texto = resultado.text_content
    texto = texto.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not texto:
        raise ValueError('No se encontró texto. Si es un PDF escaneado, necesita OCR; esta versión no incluye OCR.')
    return texto + '\n'


def nombre_salida(nombre: str, usados: set[str]) -> str:
    base = PurePosixPath(nombre.replace('\\', '/')).stem
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', base).strip(' .')[:150] or 'documento'
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', base, re.I):
        base = '_' + base
    candidato = base + '.md'
    numero = 2
    while candidato.casefold() in usados:
        candidato = f'{base} ({numero}).md'
        numero += 1
    usados.add(candidato.casefold())
    return candidato


def crear_zip(resultados: list[dict]) -> bytes:
    salida = BytesIO()
    with ZipFile(salida, 'w', ZIP_DEFLATED) as archivo:
        for resultado in resultados:
            archivo.writestr(resultado['nombre'], resultado['texto'].encode('utf-8'))
            for ruta, contenido in resultado.get('recursos', {}).items():
                archivo.writestr(ruta, contenido)
    return salida.getvalue()


def convertir_documento(nombre, contenido, salida, progreso=None, usar_ocr=True):
    recursos, avisos = {}, []
    extension = Path(nombre).suffix.lower()
    if not contenido or len(contenido) > LIMITE_BYTES:
        raise ValueError('El archivo está vacío o supera el límite de 50 MB.')
    if extension == '.pdf':
        if b'%PDF-' not in contenido[:1024]:
            raise ValueError('El archivo no contiene una cabecera PDF válida.')
        from ocr_local import extraer_pdf
        texto, avisos = extraer_pdf(contenido, progreso, usar_ocr)
    elif extension == '.docx':
        import mammoth
        from markdownify import markdownify
        with ZipFile(BytesIO(contenido)) as archivo:
            if 'word/document.xml' not in archivo.namelist():
                raise ValueError('El documento Word está dañado.')

        def imagen(img):
            extension_imagen = mimetypes.guess_extension(img.content_type) or '.bin'
            ruta = f'imagenes/{Path(salida).stem}/imagen-{len(recursos) + 1:03d}{extension_imagen}'
            with img.open() as stream:
                recursos[ruta] = stream.read()
            return {'src': ruta}

        resultado = mammoth.convert_to_html(BytesIO(contenido), convert_image=mammoth.images.img_element(imagen))
        texto = markdownify(resultado.value, heading_style='ATX')
        if recursos:
            avisos.append(f'{len(recursos)} imagen(es) guardadas junto al Markdown.')
    else:
        texto = convertir(nombre, contenido, progreso, usar_ocr)
    # Algunos conversores entregan un marcador truncado en lugar de una imagen real.
    texto, omitidas = re.subn(r'!\[[^\]]*\]\(data:image/[^)]*\.\.\.[^)]*\)',
                             '*[Imagen no disponible en la conversión]*', texto)
    if omitidas:
        avisos.append(f'{omitidas} imagen(es) no pudieron recuperarse del archivo.')
    if not texto.strip():
        raise ValueError('No se encontró contenido legible en el documento.')
    return {'original': nombre, 'nombre': salida, 'texto': texto.strip() + '\n',
            'recursos': recursos, 'avisos': avisos}


def vista_previa(resultado):
    """Inserta solo imágenes recuperadas localmente; no carga imágenes remotas."""
    def reemplazar(match):
        alt, ruta = match.group(1), match.group(2)
        contenido = resultado.get('recursos', {}).get(ruta)
        if contenido:
            mime = mimetypes.guess_type(ruta)[0] or 'application/octet-stream'
            if mime in ('image/png', 'image/jpeg', 'image/gif', 'image/webp'):
                return f'![{alt}](data:{mime};base64,{base64.b64encode(contenido).decode()})'
        return f'*[Imagen: {alt or ruta}]*'
    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', reemplazar, resultado['texto'])


def sugerir_nombre_carpeta():
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


def validar_nombre_carpeta(nombre):
    reservados = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM', 'LPT') for n in range(1, 10)}
    if (not nombre or not nombre.strip() or len(nombre) > 120 or
            re.search(r'[<>:"/\\|?*\x00-\x1f]', nombre) or nombre.endswith((' ', '.')) or
            nombre.split('.')[0].upper() in reservados):
        raise ValueError('Escribe un nombre de carpeta válido (hasta 120 caracteres, sin / \\ : * ? " < > | ni punto o espacio al final).')
    return nombre


def guardar_carpeta(resultados, destino, errores=None, nombre_carpeta=None):
    """Crea una carpeta nueva y nunca sobrescribe documentos anteriores."""
    if not resultados:
        raise ValueError('No hay documentos convertidos para guardar.')
    base = Path(destino).expanduser().resolve()
    if not base.is_dir():
        raise ValueError('La carpeta de destino no existe. Selecciona una carpeta válida.')
    archivos = {}
    for resultado in resultados:
        if resultado['nombre'] in archivos:
            raise ValueError('Hay dos documentos con el mismo nombre de salida.')
        archivos[resultado['nombre']] = resultado['texto'].encode('utf-8')
        for nombre, contenido in resultado.get('recursos', {}).items():
            if nombre in archivos:
                raise ValueError('Se detectó un nombre de recurso repetido.')
            archivos[nombre] = contenido
    # Valida todas las rutas antes de escribir; los nombres proceden de documentos externos.
    for nombre in archivos:
        relativa = Path(nombre)
        if relativa.is_absolute() or '..' in relativa.parts or ':' in nombre:
            raise ValueError('Se detectó un nombre de archivo no válido.')
    nombre = validar_nombre_carpeta(sugerir_nombre_carpeta() if nombre_carpeta is None else nombre_carpeta)
    carpeta = base / nombre
    numero = 2
    while True:
        try:
            carpeta.mkdir()
            break
        except FileExistsError:
            carpeta = base / f'{nombre}_{numero}'
            numero += 1
    try:
        for nombre, contenido in archivos.items():
            ruta = carpeta / nombre
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(contenido)
        resumen = {'documentos': [{'origen': r['original'], 'markdown': r['nombre'],
                                  'avisos': r.get('avisos', [])} for r in resultados],
                   'no_convertidos': errores or []}
        (carpeta / '_resumen.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as error:
        raise OSError(f'No se terminó de guardar la carpeta {carpeta}. Revisa el espacio y los permisos. {error}') from error
    return str(carpeta)
