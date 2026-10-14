"""Extracción por página y OCR local con los idiomas instalados en Windows."""
import asyncio
from io import BytesIO


async def _reconocer(imagen):
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat, BitmapAlphaMode
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter
    motor = OcrEngine.try_create_from_language(Language('es-ES'))
    if motor is None:
        motor = OcrEngine.try_create_from_user_profile_languages()
    if motor is None:
        raise ValueError('Windows no tiene un idioma OCR instalado. Agrega español en Configuración > Hora e idioma.')
    limite = OcrEngine.max_image_dimension
    if max(imagen.size) > limite:
        imagen.thumbnail((limite, limite))
    rgba = imagen.convert('RGBA')
    escritor = DataWriter()
    bitmap = None
    try:
        escritor.write_bytes(rgba.tobytes())
        bitmap = SoftwareBitmap(BitmapPixelFormat.RGBA8, rgba.width, rgba.height, BitmapAlphaMode.IGNORE)
        bitmap.copy_from_buffer(escritor.detach_buffer())
        resultado = await motor.recognize_async(bitmap)
        return '\n'.join(linea.text for linea in resultado.lines)
    finally:
        if bitmap is not None:
            bitmap.close()
        escritor.close()
        rgba.close()


def extraer_pdf(contenido, progreso=None, usar_ocr=True):
    import pypdfium2 as pdfium
    documento = pdfium.PdfDocument(BytesIO(contenido))
    partes, paginas_ocr, vacias = [], [], []
    try:
        cantidad = len(documento)
        for indice in range(cantidad):
            pagina = documento[indice]
            try:
                texto_pagina = pagina.get_textpage()
                try:
                    texto = texto_pagina.get_text_range().strip()
                finally:
                    texto_pagina.close()
                # Las páginas escaneadas pueden tener solo un número de página en su capa de texto.
                if len(''.join(c for c in texto if c.isalpha())) < 20 and usar_ocr:
                    if progreso:
                        progreso(indice, cantidad, f'OCR · página {indice + 1} de {cantidad}')
                    bitmap = pagina.render(scale=2.5)
                    imagen = bitmap.to_pil()
                    try:
                        texto = asyncio.run(_reconocer(imagen)).strip()
                    finally:
                        imagen.close()
                        bitmap.close()
                    paginas_ocr.append(indice + 1)
                elif progreso:
                    progreso(indice, cantidad, f'Leyendo página {indice + 1} de {cantidad}')
                if texto:
                    partes.append(f'## Página {indice + 1}\n\n{texto}')
                else:
                    vacias.append(indice + 1)
                    partes.append(f'## Página {indice + 1}\n\n[No se detectó texto en esta página.]')
            finally:
                pagina.close()
        if len(vacias) == cantidad:
            raise ValueError('No se detectó texto en el PDF. Activa el OCR para documentos escaneados o revisa la calidad del archivo.')
        if progreso:
            progreso(cantidad, cantidad, 'PDF terminado')
        avisos = []
        if paginas_ocr:
            avisos.append(f'OCR local aplicado en {len(paginas_ocr)} página(s). Revisa nombres, cifras y tablas.')
        if vacias:
            avisos.append('Páginas sin texto reconocido: ' + ', '.join(map(str, vacias)))
        return '\n\n---\n\n'.join(partes) + '\n', avisos
    finally:
        documento.close()
