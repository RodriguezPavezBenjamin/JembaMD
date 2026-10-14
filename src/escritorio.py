"""Ventana de escritorio de JembaMD y ciclo de vida del servidor local."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import logging
import os
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

RAIZ = Path(__file__).resolve().parents[1]
LOGS = RAIZ / '.logs'


def adquirir_instancia(verificar=False):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    nombre_mutex = 'Local\\JembaMD.Escritorio' + ('.Verificacion' if verificar else '')
    mutex = kernel.CreateMutexW(None, False, nombre_mutex)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        user = ctypes.windll.user32
        user.FindWindowW.restype = wintypes.HWND
        ventana = user.FindWindowW(None, 'JembaMD')
        if ventana:
            user.ShowWindow(wintypes.HWND(ventana), 9)
            user.SetForegroundWindow(wintypes.HWND(ventana))
        kernel.CloseHandle(mutex)
        return kernel, None
    return kernel, mutex


def puerto_libre():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def esperar_servidor(proceso, url, limite=60):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if proceso.poll() is not None:
            raise RuntimeError('El servicio local no pudo iniciarse. Revisa .logs/servidor.log.')
        try:
            with urlopen(url + '/_stcore/health', timeout=1) as respuesta:
                if respuesta.status == 200:
                    return
        except OSError:
            pass
        time.sleep(.25)
    raise RuntimeError('La app tardó demasiado en iniciar. Revisa .logs/servidor.log.')


def main():
    verificar = '--verificar' in sys.argv
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(filename=LOGS / 'escritorio.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    kernel, mutex = adquirir_instancia(verificar)
    if mutex is None:
        return 0
    proceso = None
    salida = None
    puente = None
    try:
        import webview
        from puente_servidor import PuenteEscritorio
        puente = PuenteEscritorio()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Jemba.JembaMD')
        puerto = puerto_libre()
        url = f'http://127.0.0.1:{puerto}'
        # Usa el mismo entorno tanto en desarrollo como en la edición portable.
        python = Path(sys.executable).with_name('python.exe')
        if not python.is_file():
            python = Path(sys.executable)
        salida = (LOGS / 'servidor.log').open('w', encoding='utf-8')
        proceso = subprocess.Popen([
            str(python), '-m', 'streamlit', 'run', str(RAIZ / 'src' / 'app.py'),
            '--server.address=127.0.0.1', f'--server.port={puerto}',
            '--server.headless=true', '--server.showEmailPrompt=false',
            '--browser.gatherUsageStats=false', '--server.fileWatcherType=none',
        ], cwd=RAIZ, stdout=salida, stderr=subprocess.STDOUT,
           creationflags=subprocess.CREATE_NO_WINDOW,
           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                    JEMBAMD_BRIDGE_URL=puente.url, JEMBAMD_BRIDGE_TOKEN=puente.token))
        esperar_servidor(proceso, url)
        webview.settings['ALLOW_DOWNLOADS'] = True
        ventana = webview.create_window('JembaMD', url, width=1180, height=820,
                                        resizable=False, background_color='#081323',
                                        text_select=True, hidden=verificar)
        puente.ventana = ventana
        estado = {}

        def comprobar():
            try:
                for _ in range(120):
                    texto = ventana.evaluate_js('document.body.innerText') or ''
                    if 'Markdown' in texto and 'JembaMD' in texto and 'Cargar' in texto:
                        estado.update(ok=True, interfaz=True, descargas=webview.settings['ALLOW_DOWNLOADS'])
                        estado.update(ventana_fija=not ventana.resizable,
                                      dimensiones_correctas=(ventana.width, ventana.height) == (1180, 820))
                        break
                    time.sleep(.5)
                else:
                    estado.update(ok=False, error='La interfaz no terminó de cargar')
            except Exception as error:
                estado.update(ok=False, error=str(error))
            finally:
                ventana.destroy()

        webview.start(comprobar if verificar else None, gui='edgechromium',
                      icon=str(RAIZ / 'assets' / 'jembamd-pixel.ico'),
                      storage_path=str(RAIZ / '.webview'), private_mode=True)
        if verificar:
            (LOGS / 'verificacion.json').write_text(json.dumps(estado, ensure_ascii=False), encoding='utf-8')
            if not estado.get('ok'):
                raise RuntimeError(estado.get('error', 'No se pudo verificar la ventana'))
        return 0
    except Exception as error:
        logging.exception('No se pudo abrir JembaMD')
        if not verificar:
            ctypes.windll.user32.MessageBoxW(None,
                f'No se pudo abrir JembaMD.\n\n{error}\n\nDetalles: {LOGS / "escritorio.log"}\n'
                'Puedes usar iniciar.bat para comprobar la instalación.', 'JembaMD', 0x10)
        return 1
    finally:
        if proceso is not None and proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=5)
        if salida:
            salida.close()
        if puente:
            puente.cerrar()
        kernel.CloseHandle(mutex)


if __name__ == '__main__':
    sys.exit(main())

