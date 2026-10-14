import ast
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from zipfile import ZipFile

source = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(source / 'src'))
os.chdir(source)
for path in list((source / 'src').glob('*.py')) + list((source / 'empaquetado').glob('*.py')):
    text = path.read_text(encoding='utf-8-sig')
    ast.parse(text, filename=path.name)
    for number, line in enumerate(text.splitlines(), 1):
        if re.search(r'[A-Za-z]:[\\/]Users[\\/]|D:[\\/]|[\w.+-]+@[\w.-]+\.[a-z]{2,}', line, re.I):
            print(f'REVISAR {path.name}:{number}')
entorno = tempfile.TemporaryDirectory(prefix='JembaMD-test-')
print('OK: sintaxis; verificaciones con documentos ficticios')

from conversor import convertir_documento, guardar_carpeta, crear_zip, nombre_salida
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont
results = []
used = set()
def convertir(name, data, expected, ocr=False):
    result = convertir_documento(name, data, nombre_salida(name, used), usar_ocr=ocr)
    assert expected.casefold() in result['texto'].casefold(), result['texto']
    results.append(result)
    print('OK: conversion ' + Path(name).suffix)
    return result

convertir('ejemplo.txt', 'Documento ficticio de prueba. Texto con acentos: conversión.'.encode(), 'conversión')
convertir('ejemplo.html', b'<html><body><h1>Documento ficticio</h1><p>Texto de prueba.</p></body></html>', 'Documento ficticio')
convertir('ejemplo.csv', b'Concepto,Monto\nPrueba,1000\n', 'Prueba')
wb = Workbook()
wb.active.append(['Concepto', 'Monto'])
wb.active.append(['Ficticio', 1000])
buffer = BytesIO()
wb.save(buffer)
convertir('ejemplo.xlsx', buffer.getvalue(), 'Ficticio')

buffer = BytesIO()
with ZipFile(buffer, 'w') as z:
    z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr('_rels/.rels', '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/document.xml', '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Documento ficticio para verificar Word.</w:t></w:r></w:p></w:body></w:document>')
convertir('ejemplo.docx', buffer.getvalue(), 'verificar Word')

stream = b'BT /F1 18 Tf 50 700 Td (Documento ficticio para verificar PDF con texto.) Tj ET'
objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>', b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
pdf = b'%PDF-1.4\n'
offsets = [0]
for index, obj in enumerate(objects, 1):
    offsets.append(len(pdf))
    pdf += str(index).encode() + b' 0 obj\n' + obj + b'\nendobj\n'
xref = len(pdf)
pdf += b'xref\n0 6\n0000000000 65535 f \n' + b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])
pdf += b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + str(xref).encode() + b'\n%%EOF'
convertir('texto.pdf', pdf, 'verificar PDF')

img = Image.new('RGB', (1400, 250), 'white')
draw = ImageDraw.Draw(img)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 45)
draw.text((40, 70), 'Documento ficticio para prueba de OCR local', fill='black', font=font)
buffer = BytesIO()
img.save(buffer, format='PDF', resolution=150)
ocr = convertir('escaneado.pdf', buffer.getvalue(), 'Documento ficticio', ocr=True)
assert any('OCR' in warning for warning in ocr['avisos'])
print('OK: OCR real de PDF generado con imagen ficticia')

destination = Path(entorno.name) / 'salidas'
destination.mkdir()
first = Path(guardar_carpeta(results, destination, nombre_carpeta='Prueba'))
second = Path(guardar_carpeta(results, destination, nombre_carpeta='Prueba'))
assert first != second
assert len(json.loads((first / '_resumen.json').read_text())['documentos']) == len(results)
with ZipFile(BytesIO(crear_zip(results))) as z:
    assert len(z.namelist()) == len(results)
print('OK: exportacion Markdown, resumen, ZIP y proteccion contra sobrescritura')

entorno.cleanup()
