"""Construye una distribución con una lista explícita de archivos públicos."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from zipfile import ZipFile, ZIP_DEFLATED

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / 'para_compartir'
APP = SALIDA / 'JembaMD-Windows-x64'
BASE = Path(sys.base_prefix)
SITE = RAIZ / '.venv' / 'Lib' / 'site-packages'
PUBLICOS = ['src/app.py', 'src/conversor.py', 'src/escritorio.py', 'src/ocr_local.py',
            'src/puente.py', 'src/puente_servidor.py', 'src/tema.py', 'requirements.txt']
ASSETS = ['jembamd-pixel.png', 'jembamd-pixel.ico', 'noche-pixel.png',
          'PressStart2P-Regular.ttf', 'PressStart2P-OFL.txt', 'pixel-origen.md', 'tema.css']


def construir():
    if APP.exists():
        raise RuntimeError(f'La salida ya existe: {APP}. Usa una carpeta nueva para otra compilación.')
    APP.mkdir(parents=True)
    for nombre in PUBLICOS:
        (APP / nombre).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RAIZ / nombre, APP / nombre)
    (APP / 'assets').mkdir()
    for nombre in ASSETS:
        shutil.copy2(RAIZ / 'assets' / nombre, APP / 'assets' / nombre)
    (APP / '.streamlit').mkdir()
    shutil.copy2(RAIZ / '.streamlit' / 'config.toml', APP / '.streamlit' / 'config.toml')
    runtime = APP / 'runtime'
    runtime.mkdir()
    for nombre in ['python.exe', 'pythonw.exe', 'python3.dll', 'python312.dll',
                   'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt']:
        shutil.copy2(BASE / nombre, runtime / nombre)
    ignorar = shutil.ignore_patterns('__pycache__', '*.pyc', 'site-packages')
    shutil.copytree(BASE / 'Lib', runtime / 'Lib', ignore=ignorar)
    shutil.copytree(BASE / 'DLLs', runtime / 'DLLs', ignore=ignorar)
    shutil.copytree(SITE, runtime / 'Lib' / 'site-packages',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'pip', 'pip-*.dist-info'))
    # Rutas relativas: no depende del Python ni del perfil de quien construyó el ZIP.
    (runtime / 'python312._pth').write_text(
        '.\n..\nLib\nDLLs\nLib/site-packages\nimport site\n', encoding='ascii')
    compiler = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64',
                    '/reference:System.Windows.Forms.dll',
                    '/win32icon:' + str(APP / 'assets' / 'jembamd-pixel.ico'),
                    '/out:' + str(APP / 'JembaMD.exe'),
                    str(RAIZ / 'empaquetado' / 'Launcher.cs')], check=True)
    shutil.copy2(RAIZ / 'empaquetado' / 'LEEME-portable.txt', APP / 'LEEME.txt')
    deps = sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions(path=[str(SITE)])
                  if d.metadata['Name'].lower() != 'pip')
    (APP / 'COMPONENTES.txt').write_text(
        'JembaMD incluye Python ' + sys.version.split()[0] + '. Licencia: runtime/LICENSE.txt.\n'
        'Las licencias y avisos de los componentes están en runtime/Lib/site-packages/*.dist-info.\n'
        'Fuente Press Start 2P: assets/PressStart2P-OFL.txt.\n\n' +
        '\n'.join(f'{name}=={version}' for name, version in deps), encoding='utf-8')
    print('Carpeta portable creada:', APP, flush=True)


def comprimir():
    # Nunca comparte estado, resultados o registros de las pruebas.
    excluidos = {'.logs', '.webview', 'salidas', '__pycache__'}
    files = [p for p in APP.rglob('*') if p.is_file() and
             not any(part in excluidos for part in p.relative_to(APP).parts) and p.suffix != '.pyc']
    zip_path = SALIDA / 'JembaMD-Windows-x64.zip'
    with ZipFile(zip_path, 'w', ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, p.relative_to(SALIDA).as_posix())
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    zip_path.with_suffix('.zip.sha256').write_text(digest + '  ' + zip_path.name + '\n', encoding='ascii')
    print(json.dumps({'zip': str(zip_path), 'MB': round(zip_path.stat().st_size / 1024**2, 1),
                      'archivos': len(files), 'sha256': digest}), flush=True)


if __name__ == '__main__':
    comprimir() if '--zip' in sys.argv else construir()
