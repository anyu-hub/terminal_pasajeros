from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from domain import (
    AutobusEjecutivo,
    AutobusEstandar,
    Flota,
    Ruta,
    Taxi,
    Terminal,
    VehiculoTransporte,
)


class ErrorPersistencia(Exception):
    """Error al guardar o cargar el estado de la terminal."""


def _vehiculo_desde_dict(data: dict[str, Any]) -> VehiculoTransporte:
    tipo = data.get("tipo")
    comunes = {
        "identificador": data["identificador"],
        "tarifa_base": data["tarifa_base"],
        "tasa_entrada": data.get("tasa_entrada", 0.0),
        "tasa_salida": data.get("tasa_salida", 0.0),
    }

    if tipo == AutobusEstandar.tipo:
        vehiculo = AutobusEstandar(capacidad=data["capacidad"], **comunes)
    elif tipo == AutobusEjecutivo.tipo:
        vehiculo = AutobusEjecutivo(
            capacidad=data["capacidad"],
            servicios_vip=data.get("servicios_vip", []),
            recargo_vip=data.get("recargo_vip", 25.0),
            **comunes,
        )
    elif tipo == Taxi.tipo:
        vehiculo = Taxi(
            recargo_servicio=data.get("recargo_servicio", 10.0),
            **comunes,
        )
    else:
        raise ErrorPersistencia(f"Tipo de vehículo no soportado: {tipo}")

    vehiculo.restaurar_ocupacion(data.get("asientos_ocupados", 0))
    vehiculo.restaurar_disponibilidad(data.get("disponible", True))
    return vehiculo


def terminal_a_dict(terminal: Terminal) -> dict[str, Any]:
    return {
        "nombre": terminal.nombre,
        "ciudad_origen": terminal.ciudad_origen,
        "rutas": [
            {
                "origen": ruta.origen,
                "destino": ruta.destino,
                "tarifas_por_tipo": ruta.tarifas_por_tipo,
                "recargos_por_tipo": ruta.recargos_por_tipo,
                "turnos_por_tipo": ruta.flota.turnos_por_tipo,
                "vehiculos": [vehiculo.to_dict() for vehiculo in ruta.flota.vehiculos],
            }
            for ruta in terminal.rutas
        ],
    }


def terminal_desde_dict(data: dict[str, Any]) -> Terminal:
    if not isinstance(data, dict) or "nombre" not in data or "rutas" not in data:
        raise ErrorPersistencia("La estructura del archivo no es válida")

    rutas_data = data["rutas"]
    ciudad_origen = data.get("ciudad_origen")
    if ciudad_origen is None and rutas_data:
        ciudad_origen = rutas_data[0].get("origen")
    terminal = Terminal(data["nombre"], ciudad_origen=ciudad_origen)
    for ruta_data in rutas_data:
        ruta = Ruta(
            ruta_data["origen"],
            ruta_data["destino"],
            tarifas_por_tipo=ruta_data.get("tarifas_por_tipo", {}),
            recargos_por_tipo=ruta_data.get("recargos_por_tipo", {}),
        )
        ruta.flota.turnos_por_tipo.update(ruta_data.get("turnos_por_tipo", {}))
        for vehiculo_data in ruta_data.get("vehiculos", []):
            ruta.flota.agregar_vehiculo(_vehiculo_desde_dict(vehiculo_data))
        terminal.agregar_ruta(ruta)
    return terminal


def guardar_terminal(terminal: Terminal, ruta_archivo: str | Path) -> None:
    path = Path(ruta_archivo)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(terminal_a_dict(terminal), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, TypeError) as error:
        raise ErrorPersistencia(f"No se pudo guardar el archivo: {error}") from error


def cargar_terminal(ruta_archivo: str | Path, nombre_por_defecto: str = "Terminal Principal") -> Terminal:
    path = Path(ruta_archivo)
    if not path.exists():
        return Terminal(nombre_por_defecto)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return terminal_desde_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ErrorPersistencia(f"No se pudo cargar el archivo: {error}") from error
