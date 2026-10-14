"""JembaMD: cuatro vistas para convertir y guardar documentos."""
import hashlib
from pathlib import Path
import os
import streamlit as st
from conversor import EXTENSIONES, convertir_documento, crear_zip, nombre_salida, guardar_carpeta, vista_previa, sugerir_nombre_carpeta
from tema import aplicar_tema, cabecera, marca as mostrar_marca
import puente

RAIZ = Path(__file__).resolve().parents[1]
LOGO = RAIZ / 'assets' / 'jembamd-pixel.png'
st.set_page_config(page_title='JembaMD · Archivos a Markdown', page_icon=str(LOGO), layout='wide')
aplicar_tema()
ss = st.session_state
for clave, valor in {'paso': 0, 'generacion': 0, 'entradas': [], 'resultados': [], 'errores': [],
                     'procesado': False, 'revisado': False, 'guardada': '',
                     'destino': str(RAIZ / 'salidas'), 'ocr': True, 'nombre_carpeta': sugerir_nombre_carpeta()}.items():
    ss.setdefault(clave, valor)


def ir(paso):
    ss.paso = paso
    if paso == 2:
        ss.revisado = True
    st.rerun()


def limpiar():
    for clave, valor in {'paso': 0, 'entradas': [], 'resultados': [], 'errores': [],
                         'procesado': False, 'revisado': False, 'guardada': '', 'firma': None}.items():
        ss[clave] = valor
    ss.nombre_carpeta = sugerir_nombre_carpeta()
    ss.generacion += 1
    st.rerun()


def actualizar_archivos(clave):
    archivos = ss.get(clave) or []
    ss.entradas = [{'nombre': f.name, 'contenido': f.getvalue()} for f in archivos]
    ss.firma = tuple((f.name, hashlib.sha256(f.getbuffer()).hexdigest()) for f in archivos)
    ss.resultados, ss.errores = [], []
    ss.procesado, ss.revisado, ss.guardada = False, False, ''


def seccion(titulo, detalle=''):
    st.markdown(f'<div class="pixel-section"><strong>{titulo}</strong><span>{detalle}</span></div>', unsafe_allow_html=True)


with st.container(key='cabecera_app'):
    identidad, nuevo = st.columns([5, 1], vertical_alignment='center')
    with identidad:
        mostrar_marca()
    with nuevo:
        if st.button('✦ Nuevo lote', key='nuevo_lote', use_container_width=True):
            limpiar()

cabecera()
pasos = ['Cargar', 'Convertir', 'Revisar', 'Guardar']
terminados = [bool(ss.entradas), ss.procesado, ss.revisado, bool(ss.guardada)]
habilitados = [True, bool(ss.entradas), ss.procesado, ss.procesado and bool(ss.resultados)]
columnas = st.columns(4, gap='small')
for indice, (columna, etiqueta) in enumerate(zip(columnas, pasos)):
    prefijo = '✓' if terminados[indice] else f'{indice + 1:02d}'
    if columna.button(f'{prefijo}  {etiqueta}', key=f'paso_{indice}',
                       type='primary' if ss.paso == indice else 'secondary',
                       disabled=not habilitados[indice], use_container_width=True):
        ir(indice)

with st.container(height=380, border=True, key='panel_principal'):
    if ss.paso == 0:
        seccion('01 / CARGAR', 'Elige los documentos de este lote')
        clave = f'archivos_{ss.generacion}'
        with st.container(key='carga_lista' if ss.entradas else 'carga_vacia'):
            st.file_uploader('Agrega uno o varios archivos', type=list(EXTENSIONES),
                accept_multiple_files=True, max_upload_size=50, key=clave,
                label_visibility='collapsed', on_change=actualizar_archivos, args=(clave,))
        total = sum(len(f['contenido']) for f in ss.entradas)
        if ss.entradas:
            resumen, accion = st.columns([2, 1], vertical_alignment='center')
            with resumen:
                st.markdown(f'<div class="pixel-summary"><strong>{len(ss.entradas):02d} ARCHIVOS LISTOS</strong>'
                            f'<span>{total / 1024 / 1024:.1f} MB / 200 MB · Tu lote está preparado</span></div>', unsafe_allow_html=True)
            with accion:
                if st.button('Continuar a Convertir →', type='primary', use_container_width=True,
                             disabled=total > 200 * 1024 * 1024):
                    ir(1)
            if total > 200 * 1024 * 1024:
                st.error('El lote supera los 200 MB. Crea un lote más pequeño.')
            st.caption('Tus .md e imágenes se guardarán juntos en una carpeta con el nombre que elijas.')
        else:
            st.markdown('<div class="pixel-hint"><span>✦ ARRASTRA TUS DOCUMENTOS AQUÍ</span>'
                        '<span>50 MB por archivo · 200 MB por lote · OCR local para PDF</span></div>', unsafe_allow_html=True)

    elif ss.paso == 1:
        seccion('02 / CONVERTIR', f'{len(ss.entradas)} archivo(s) preparados')
        st.checkbox('Reconocer texto de PDF escaneados (OCR local)', key='ocr')
        st.caption('El OCR se aplica solo a las páginas sin texto legible. Puede tardar más; no requiere internet.')
        if ss.procesado:
            st.success(f'Lote procesado: {len(ss.resultados)} convertido(s), {len(ss.errores)} con problemas.')
        if st.button('Convertir archivos' if not ss.procesado else 'Volver a convertir', type='primary'):
            resultados, errores, usados = [], [], set()
            barra = st.progress(0, text='Preparando el lote…')
            estado = st.empty()
            for indice, archivo in enumerate(ss.entradas):
                nombre = archivo['nombre']
                estado.info(f'Archivo {indice + 1} de {len(ss.entradas)} · {nombre}')
                def avance(pagina, cantidad, detalle):
                    fraccion = (indice + pagina / max(cantidad, 1)) / len(ss.entradas)
                    barra.progress(min(fraccion, 1.0), text=detalle)
                try:
                    salida = nombre_salida(nombre, usados)
                    resultados.append(convertir_documento(nombre, archivo['contenido'], salida, avance, ss.ocr))
                except Exception as error:
                    errores.append({'nombre': nombre, 'detalle': str(error)[:2000] or type(error).__name__})
                barra.progress((indice + 1) / len(ss.entradas), text=f'{indice + 1} de {len(ss.entradas)} archivos procesados')
            ss.resultados, ss.errores = resultados, errores
            ss.procesado, ss.guardada = True, ''
            ir(2)
        if ss.procesado and st.button('Ver resultados →'):
            ir(2)

    elif ss.paso == 2:
        seccion('03 / REVISAR', f'{len(ss.resultados)} convertido(s) · {len(ss.errores)} con problemas')
        if ss.errores:
            with st.expander(f'Ver {len(ss.errores)} archivo(s) que no se pudieron convertir', expanded=not bool(ss.resultados)):
                for error in ss.errores:
                    st.error(error['nombre'])
                    st.text(error['detalle'])
        if ss.resultados:
            lista, vista = st.columns([1, 2.5], gap='medium')
            with lista:
                elegido = st.selectbox('Documento', range(len(ss.resultados)),
                    format_func=lambda i: ss.resultados[i]['nombre'], key='documento')
                resultado = ss.resultados[elegido]
                st.caption(f'{len(resultado["texto"]):,} caracteres')
                for aviso in resultado.get('avisos', []):
                    st.caption(aviso)
                if st.button('Continuar a Guardar →', type='primary'):
                    ir(3)
            with vista:
                legible, codigo = st.tabs(['Vista legible', 'Código Markdown'])
                with legible:
                    with st.container(height=250, border=True, key='vista_legible'):
                        st.markdown(vista_previa(resultado)[:250_000], unsafe_allow_html=False)
                with codigo:
                    with st.container(height=250, border=True):
                        st.code(resultado['texto'][:100_000], language='markdown', wrap_lines=True)
                st.caption('La vista previa puede estar limitada. Los archivos guardados contienen el texto completo.')
        else:
            st.warning('No hubo resultados. Vuelve a Convertir y revisa los errores o activa OCR para los PDF escaneados.')

    elif ss.paso == 3:
        seccion('04 / GUARDAR', f'{len(ss.resultados)} archivo(s) Markdown')
        izquierda, derecha = st.columns([2, 1], gap='medium')
        with izquierda:
            if not ss.guardada:
                if ss.get('destino_elegido'):
                    ss.destino = ss.pop('destino_elegido')
                st.text_input('Nombre de la nueva carpeta', key='nombre_carpeta', max_chars=120)
                st.text_input('Guardar dentro de', key='destino')
            if not ss.guardada and puente.disponible() and st.button('Elegir carpeta…'):
                try:
                    seleccion = puente.llamar('elegir_carpeta')['carpeta']
                    if seleccion:
                        ss.destino_elegido = seleccion
                        st.rerun()
                except Exception as error:
                    st.error(str(error))
            if not ss.guardada:
                st.caption('Puedes cambiar el nombre sugerido. Si ya existe, se añade un número.')
            if not ss.guardada and st.button('Guardar carpeta con los .md', type='primary'):
                try:
                    if Path(ss.destino) == RAIZ / 'salidas':
                        Path(ss.destino).mkdir(exist_ok=True)
                    ss.guardada = guardar_carpeta(ss.resultados, ss.destino, ss.errores, nombre_carpeta=ss.nombre_carpeta)
                    st.rerun()
                except Exception as error:
                    st.error(str(error))
            if ss.guardada:
                st.success('Carpeta creada. Aquí están tus archivos .md:')
                st.code(ss.guardada, language=None, wrap_lines=True)
                if st.button('Abrir carpeta con los .md'):
                    try:
                        if puente.disponible():
                            puente.llamar('abrir_carpeta', carpeta=ss.guardada)
                        else:
                            os.startfile(ss.guardada)
                    except Exception as error:
                        st.error(str(error))
        with derecha:
            st.markdown('**Qué recibirás**')
            st.write('Un .md por documento, la carpeta de imágenes cuando corresponda y un resumen con avisos y errores.')
            st.caption('El ZIP queda disponible como alternativa.')
            st.download_button('Descargar ZIP (opcional)', crear_zip(ss.resultados), file_name='JembaMD_documentos.zip',
                               mime='application/zip', on_click='ignore')

st.markdown(f'<div class="pixel-footer"><span>PASO {ss.paso + 1} DE 4 · {pasos[ss.paso].upper()}</span><span>Local · Sin modificar tus originales</span></div>', unsafe_allow_html=True)

