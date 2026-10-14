"""Recursos locales y presentación del tema pixel art."""
import base64
from pathlib import Path
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]


@st.cache_data(show_spinner=False)
def recurso(nombre):
    return base64.b64encode((RAIZ / 'assets' / nombre).read_bytes()).decode('ascii')


def aplicar_tema():
    css = (RAIZ / 'assets' / 'tema.css').read_text(encoding='utf-8')
    css = css.replace('__FUENTE__', recurso('PressStart2P-Regular.ttf'))
    css = css.replace('__PAISAJE__', recurso('noche-pixel.png'))
    st.markdown('<style>' + css + '</style>', unsafe_allow_html=True)


def marca():
    logo = recurso('jembamd-pixel.png')
    st.markdown(f'<div class="app-brand"><img src="data:image/png;base64,{logo}" alt="">JembaMD <small>PIXEL EDITION · LOCAL</small></div>', unsafe_allow_html=True)


def cabecera():
    st.markdown('''
    <section class="pixel-hero" aria-label="JembaMD, convertidor de documentos">
      <div class="pixel-hero-content">
        <h1>Archivos a <span>Markdown</span></h1>
        <p>Una carpeta con tus documentos. Todo en tu computador.</p>
      </div>
    </section>
    ''', unsafe_allow_html=True)
