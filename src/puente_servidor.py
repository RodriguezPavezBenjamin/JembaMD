"""Servicio loopback autenticado, accesible solo por el backend de esta instancia."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import os


class PuenteEscritorio:
    def __init__(self):
        self.ventana = None
        self.token = secrets.token_urlsafe(32)
        puente = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                auth = self.headers.get('Authorization', '')
                if not secrets.compare_digest(auth, 'Bearer ' + puente.token):
                    self.send_error(403)
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 32768:
                        raise ValueError('Solicitud no válida.')
                    respuesta = puente.ejecutar(json.loads(self.rfile.read(length)))
                except Exception as error:
                    respuesta = {'ok': False, 'error': str(error)}
                contenido = json.dumps(respuesta).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(contenido)))
                self.end_headers()
                self.wfile.write(contenido)

        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.hilo.start()
        self.url = f'http://127.0.0.1:{self.servidor.server_port}/'

    def ejecutar(self, datos):
        if self.ventana is None:
            raise RuntimeError('La ventana todavía se está preparando.')
        accion = datos.get('accion')
        if accion == 'elegir_carpeta':
            import webview
            seleccion = None
            def elegir():
                nonlocal seleccion
                seleccion = self.ventana.create_file_dialog(webview.FileDialog.FOLDER)
            native = getattr(self.ventana, 'native', None)
            if native is not None and native.InvokeRequired:
                # Los diálogos de Windows deben ejecutarse en el hilo STA de la ventana.
                from System import Action
                native.Invoke(Action(elegir))
            else:
                elegir()
            return {'ok': True, 'carpeta': seleccion[0] if seleccion else None}
        if accion == 'abrir_carpeta':
            ruta = Path(datos.get('carpeta', '')).resolve()
            if not ruta.is_dir():
                raise ValueError('La carpeta no existe.')
            os.startfile(str(ruta))
            return {'ok': True}
        raise ValueError('Acción no disponible.')

    def cerrar(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.hilo.join(timeout=3)
