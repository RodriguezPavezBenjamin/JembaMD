"""Acceso privado al selector de carpetas y la ventana de escritorio."""
import json
import os
from urllib.request import Request, urlopen


def disponible():
    return bool(os.environ.get('JEMBAMD_BRIDGE_URL'))


def llamar(accion, **datos):
    url = os.environ.get('JEMBAMD_BRIDGE_URL')
    token = os.environ.get('JEMBAMD_BRIDGE_TOKEN')
    if not url or not token:
        raise RuntimeError('Esta opción requiere abrir JembaMD desde su acceso directo.')
    solicitud = Request(url, data=json.dumps({'accion': accion, **datos}).encode('utf-8'),
                        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urlopen(solicitud, timeout=600) as respuesta:
        resultado = json.load(respuesta)
    if not resultado.get('ok'):
        raise RuntimeError(resultado.get('error', 'No se pudo completar la acción.'))
    return resultado
