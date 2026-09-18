from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ErrorDominio(Exception):
    """Error producido por una operación inválida del dominio."""


class CapacidadExcedidaError(ErrorDominio):
    """Se intentó abordar más pasajeros de los disponibles."""


class VehiculoTransporte(ABC):
    """Plantilla común para cualquier vehículo de la terminal."""

    tipo = "vehiculo"
    tipo_servicio = "vehiculo"

    def __init__(
        self,
        identificador: str,
        capacidad: int,
        tarifa_base: float,
        tasa_entrada: float = 0.0,
        tasa_salida: float = 0.0,
    ) -> None:
        if not identificador.strip():
            raise ValueError("El identificador no puede estar vacío")
        if capacidad <= 0:
            raise ValueError("La capacidad debe ser mayor que cero")
        if tarifa_base < 0 or tasa_entrada < 0 or tasa_salida < 0:
            raise ValueError("Las tarifas y tasas no pueden ser negativas")

        self.identificador = identificador.strip()
        self.capacidad = capacidad
        self.tarifa_base = float(tarifa_base)
        self.tasa_entrada = float(tasa_entrada)
        self.tasa_salida = float(tasa_salida)
        self.__asientos_ocupados = 0
        self.__disponible = True

    @property
    def asientos_ocupados(self) -> int:
        """Cantidad ocupada expuesta sin permitir asignación externa."""
        return self.__asientos_ocupados

    @property
    def asientos_disponibles(self) -> int:
        return self.capacidad - self.__asientos_ocupados

    @property
    def disponible(self) -> bool:
        return self.__disponible

    @property
    def esta_cargando(self) -> bool:
        return self.__disponible and self.__asientos_ocupados > 0

    def abordar(self, cantidad: int) -> None:
        if not isinstance(cantidad, int) or isinstance(cantidad, bool):
            raise TypeError("La cantidad de pasajeros debe ser un entero")
        if cantidad <= 0:
            raise ValueError("La cantidad de pasajeros debe ser positiva")
        if cantidad > self.asientos_disponibles:
            raise CapacidadExcedidaError(
                f"{self.identificador} solo tiene "
                f"{self.asientos_disponibles} asiento(s) disponible(s)"
            )
        self.__asientos_ocupados += cantidad

    def reiniciar_ocupacion(self) -> None:
        self.__asientos_ocupados = 0

    def registrar_salida(self) -> None:
        if not self.__disponible:
            raise ErrorDominio(f"El vehículo {self.identificador} ya está en viaje")
        self.__disponible = False

    def reingresar(self) -> None:
        self.reiniciar_ocupacion()
        self.__disponible = True

    def costo_tasas(self) -> float:
        return self.tasa_entrada + self.tasa_salida

    @abstractmethod
    def calcular_costo_total(self) -> float:
        """Calcula el costo final según el tipo concreto de vehículo."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo,
            "identificador": self.identificador,
            "capacidad": self.capacidad,
            "tarifa_base": self.tarifa_base,
            "tasa_entrada": self.tasa_entrada,
            "tasa_salida": self.tasa_salida,
            "asientos_ocupados": self.asientos_ocupados,
            "disponible": self.disponible,
        }

    def restaurar_ocupacion(self, cantidad: int) -> None:
        if not isinstance(cantidad, int) or cantidad < 0 or cantidad > self.capacidad:
            raise ValueError("La ocupación guardada no es válida")
        self.__asientos_ocupados = cantidad

    def restaurar_disponibilidad(self, disponible: bool) -> None:
        if not isinstance(disponible, bool):
            raise ValueError("La disponibilidad guardada no es válida")
        self.__disponible = disponible


class AutobusEstandar(VehiculoTransporte):
    tipo = "autobus_estandar"
    tipo_servicio = "estandar"

    def calcular_costo_total(self) -> float:
        return self.tarifa_base + self.costo_tasas()


class AutobusEjecutivo(VehiculoTransporte):
    tipo = "autobus_ejecutivo"
    tipo_servicio = "ejecutivo"

    def __init__(
        self,
        identificador: str,
        capacidad: int,
        tarifa_base: float,
        servicios_vip: list[str] | None = None,
        recargo_vip: float = 25.0,
        tasa_entrada: float = 0.0,
        tasa_salida: float = 0.0,
    ) -> None:
        super().__init__(identificador, capacidad, tarifa_base, tasa_entrada, tasa_salida)
        if recargo_vip < 0:
            raise ValueError("El recargo VIP no puede ser negativo")
        self.servicios_vip = list(servicios_vip or [])
        self.recargo_vip = float(recargo_vip)

    def calcular_costo_total(self) -> float:
        return self.tarifa_base + self.costo_tasas() + self.recargo_vip

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "servicios_vip": self.servicios_vip,
                "recargo_vip": self.recargo_vip,
            }
        )
        return data


class Taxi(VehiculoTransporte):
    tipo = "taxi"
    tipo_servicio = "taxi"
    CAPACIDAD = 4

    def __init__(
        self,
        identificador: str,
        tarifa_base: float,
        recargo_servicio: float = 10.0,
        tasa_entrada: float = 0.0,
        tasa_salida: float = 0.0,
    ) -> None:
        super().__init__(
            identificador,
            self.CAPACIDAD,
            tarifa_base,
            tasa_entrada,
            tasa_salida,
        )
        if recargo_servicio < 0:
            raise ValueError("El recargo del taxi no puede ser negativo")
        self.recargo_servicio = float(recargo_servicio)

    def calcular_costo_total(self) -> float:
        return self.tarifa_base + self.costo_tasas() + self.recargo_servicio

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["recargo_servicio"] = self.recargo_servicio
        return data


@dataclass
class Flota:
    vehiculos: list[VehiculoTransporte] = field(default_factory=list)
    turnos_por_tipo: dict[str, str] = field(default_factory=dict)

    def agregar_vehiculo(self, vehiculo: VehiculoTransporte) -> None:
        if not isinstance(vehiculo, VehiculoTransporte):
            raise TypeError("La flota solo admite vehículos de transporte")
        if any(
            item.identificador.upper() == vehiculo.identificador.upper()
            for item in self.vehiculos
        ):
            raise ValueError("Ya existe un vehículo con ese identificador")
        self.vehiculos.append(vehiculo)
        self.turnos_por_tipo.setdefault(vehiculo.tipo_servicio, vehiculo.identificador)

    def buscar_vehiculo(self, identificador: str) -> VehiculoTransporte:
        for vehiculo in self.vehiculos:
            if vehiculo.identificador.upper() == identificador.strip().upper():
                return vehiculo
        raise KeyError(f"No existe el vehículo '{identificador}'")

    def eliminar_vehiculo(self, identificador: str) -> VehiculoTransporte:
        vehiculo = self.buscar_vehiculo(identificador)
        self.vehiculos.remove(vehiculo)
        if self.turnos_por_tipo.get(vehiculo.tipo_servicio) == vehiculo.identificador:
            siguiente = next(
                (
                    item.identificador
                    for item in self.vehiculos
                    if item.tipo_servicio == vehiculo.tipo_servicio
                ),
                None,
            )
            if siguiente is None:
                self.turnos_por_tipo.pop(vehiculo.tipo_servicio, None)
            else:
                self.turnos_por_tipo[vehiculo.tipo_servicio] = siguiente
        return vehiculo

    def abordar(self, identificador: str, cantidad: int) -> None:
        self.buscar_vehiculo(identificador).abordar(cantidad)

    def registrar_salida(self, identificador: str) -> None:
        vehiculo = self.buscar_vehiculo(identificador)
        vehiculos_del_tipo = [
            item for item in self.vehiculos if item.tipo_servicio == vehiculo.tipo_servicio
        ]
        vehiculo.registrar_salida()
        posicion = vehiculos_del_tipo.index(vehiculo)
        siguiente = vehiculos_del_tipo[(posicion + 1) % len(vehiculos_del_tipo)]
        self.turnos_por_tipo[vehiculo.tipo_servicio] = siguiente.identificador

    def abordar_por_tipo(self, tipo: str, cantidad: int) -> VehiculoTransporte:
        tipo_normalizado = tipo.strip().lower()
        if tipo_normalizado not in {"estandar", "ejecutivo", "taxi"}:
            raise ValueError("El tipo de vehículo no es válido")

        vehiculos_del_tipo = [
            vehiculo
            for vehiculo in self.vehiculos
            if vehiculo.tipo_servicio == tipo_normalizado
            and vehiculo.disponible
        ]
        if not vehiculos_del_tipo:
            raise KeyError(f"No hay vehículos del tipo '{tipo_normalizado}'")

        vehiculos_cargando = [
            vehiculo for vehiculo in vehiculos_del_tipo if vehiculo.esta_cargando
        ]
        siguiente_id = self.turnos_por_tipo.get(tipo_normalizado)
        posicion = next(
            (
                indice
                for indice, vehiculo in enumerate(vehiculos_del_tipo)
                if vehiculo.identificador == siguiente_id
            ),
            0,
        )
        candidatos_rotativos = (
            vehiculos_del_tipo[posicion:]
            + vehiculos_del_tipo[:posicion]
        )
        candidatos = vehiculos_cargando + [
            vehiculo
            for vehiculo in candidatos_rotativos
            if vehiculo not in vehiculos_cargando
        ]
        for vehiculo in candidatos:
            if vehiculo.asientos_disponibles >= cantidad:
                vehiculo.abordar(cantidad)
                return vehiculo

        raise CapacidadExcedidaError(
            f"No hay cupos suficientes para el servicio '{tipo_normalizado}'"
        )

    def calcular_costos(self) -> dict[str, float]:
        return {
            vehiculo.identificador: vehiculo.calcular_costo_total()
            for vehiculo in self.vehiculos
        }


@dataclass
class Ruta:
    origen: str
    destino: str
    flota: Flota = field(default_factory=Flota)
    tarifas_por_tipo: dict[str, float] = field(default_factory=dict)
    recargos_por_tipo: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.origen = self.origen.strip()
        self.destino = self.destino.strip()
        if not self.origen or not self.destino:
            raise ValueError("El origen y el destino son obligatorios")

    @property
    def nombre(self) -> str:
        return f"{self.origen} -> {self.destino}"

    def establecer_tarifa(self, tipo: str, tarifa: float, recargo: float = 0.0) -> None:
        tipo_normalizado = tipo.strip().lower()
        if tipo_normalizado not in {"estandar", "ejecutivo", "taxi"}:
            raise ValueError("El tipo de vehículo no es válido")
        if tarifa < 0 or recargo < 0:
            raise ValueError("La tarifa y el recargo no pueden ser negativos")
        self.tarifas_por_tipo[tipo_normalizado] = float(tarifa)
        self.recargos_por_tipo[tipo_normalizado] = float(recargo)

    @property
    def tarifas_configuradas(self) -> bool:
        tipos = {"estandar", "ejecutivo", "taxi"}
        return tipos.issubset(self.tarifas_por_tipo) and tipos.issubset(
            self.recargos_por_tipo
        )

    def configurar_tarifas(self, tarifas: dict[str, tuple[float, float]]) -> None:
        if self.tarifas_configuradas:
            raise ValueError(
                "Las tarifas ya están configuradas; use la opción de modificar tarifas"
            )
        self._guardar_tarifas_completas(tarifas)

    def modificar_tarifas(self, tarifas: dict[str, tuple[float, float]]) -> None:
        if not self.tarifas_configuradas:
            raise ValueError("Configure primero las tarifas de la ruta")
        self._guardar_tarifas_completas(tarifas)

    def _guardar_tarifas_completas(
        self, tarifas: dict[str, tuple[float, float]]
    ) -> None:
        tipos = {"estandar", "ejecutivo", "taxi"}
        if set(tarifas) != tipos:
            raise ValueError("Debe indicar tarifa y recargo para los tres tipos")
        for tipo, (tarifa, recargo) in tarifas.items():
            self.establecer_tarifa(tipo, tarifa, recargo)

    def calcular_tarifa(self, tipo: str, aplicar_recargo: bool = True) -> float:
        tipo_normalizado = tipo.strip().lower()
        try:
            tarifa_base = self.tarifas_por_tipo[tipo_normalizado]
            recargo = self.recargos_por_tipo.get(tipo_normalizado, 0.0)
            return tarifa_base + (recargo if aplicar_recargo else 0.0)
        except KeyError as error:
            raise KeyError(
                f"No hay una tarifa configurada para el tipo '{tipo_normalizado}'"
            ) from error


@dataclass
class Terminal:
    nombre: str
    ciudad_origen: str | None = None
    rutas: list[Ruta] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.ciudad_origen is not None:
            self.ciudad_origen = self.ciudad_origen.strip()
            if not self.ciudad_origen:
                self.ciudad_origen = None

    def establecer_ciudad_origen(self, ciudad: str) -> None:
        ciudad = ciudad.strip()
        if not ciudad:
            raise ValueError("La ciudad de origen no puede estar vacía")
        if self.rutas and self.ciudad_origen and ciudad.lower() != self.ciudad_origen.lower():
            raise ValueError("No se puede cambiar la ciudad de un terminal con rutas")
        self.ciudad_origen = ciudad

    def agregar_ruta(self, ruta: Ruta) -> None:
        if self.ciudad_origen is None:
            self.ciudad_origen = ruta.origen
        if ruta.origen.lower() != self.ciudad_origen.lower():
            raise ValueError(
                f"El origen debe ser la ciudad del terminal: {self.ciudad_origen}"
            )
        if any(item.destino.lower() == ruta.destino.lower() for item in self.rutas):
            raise ValueError("Ya existe una ruta hacia ese destino")
        self.rutas.append(ruta)

    def eliminar_ruta(self, destino: str) -> Ruta:
        ruta = self.buscar_ruta_destino(destino)
        self.rutas.remove(ruta)
        return ruta

    def buscar_ruta_destino(self, destino: str) -> Ruta:
        destino = destino.strip()
        for ruta in self.rutas:
            if ruta.destino.lower() == destino.lower():
                return ruta
        raise KeyError(f"No existe una ruta hacia '{destino}'")

    def buscar_ruta(self, origen: str, destino: str) -> Ruta:
        for ruta in self.rutas:
            if ruta.origen.lower() == origen.lower() and ruta.destino.lower() == destino.lower():
                return ruta
        raise KeyError(f"No existe la ruta '{origen} -> {destino}'")
