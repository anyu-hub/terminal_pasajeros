from __future__ import annotations

from pathlib import Path

from domain import (
    AutobusEjecutivo,
    AutobusEstandar,
    ErrorDominio,
    Flota,
    Ruta,
    Taxi,
    Terminal,
)
from persistence import ErrorPersistencia, cargar_terminal, guardar_terminal


class AplicacionConsola:
    def __init__(self, archivo_datos: str | Path | None = None) -> None:
        base = Path(__file__).resolve().parent
        self.archivo_datos = Path(archivo_datos or base / "data" / "terminal.json")
        self.terminal = cargar_terminal(self.archivo_datos)

    def ejecutar(self) -> None:
        print(f"\n=== {self.terminal.nombre} ===")
        print(f"Ciudad de origen: {self.terminal.ciudad_origen or 'pendiente de configurar'}")
        while True:
            self._mostrar_menu()
            opcion = self._leer_opcion()
            try:
                if opcion == "1":
                    self._crear_ruta()
                elif opcion == "2":
                    self._crear_flota()
                elif opcion == "3":
                    self._agregar_vehiculo()
                elif opcion == "4":
                    self._configurar_tarifa()
                elif opcion == "5":
                    self._modificar_tarifas()
                elif opcion == "6":
                    self._listar_rutas()
                elif opcion == "7":
                    self._mostrar_costos()
                elif opcion == "8":
                    self._abordar_pasajeros()
                elif opcion == "9":
                    self._eliminar_ruta()
                elif opcion == "10":
                    self._eliminar_vehiculo()
                elif opcion == "11":
                    self._registrar_salida()
                elif opcion == "12":
                    self._reingresar_vehiculo()
                elif opcion == "13":
                    self._eliminar_flota()
                elif opcion == "0":
                    guardar_terminal(self.terminal, self.archivo_datos)
                    print("Datos guardados. Hasta pronto.")
                    return
                else:
                    print("Opción inválida.")
            except (ErrorDominio, ErrorPersistencia, KeyError, TypeError, ValueError) as error:
                print(f"No se pudo completar la operación: {error}")

    @staticmethod
    def _mostrar_menu() -> None:
        print(
            "\n1. Crear ruta\n"
            "2. Crear flota para una ruta\n"
            "3. Agregar vehículo a una ruta\n"
            "4. Configurar tarifas y recargos de la flota\n"
            "5. Modificar tarifas y recargos de la flota\n"
            "6. Listar rutas y vehículos\n"
            "7. Consultar tarifas por ruta\n"
            "8. Abordar pasajeros\n"
            "9. Eliminar ruta\n"
            "10. Eliminar vehículo\n"
            "11. Registrar salida de vehículo\n"
            "12. Reingresar vehículo disponible\n"
            "13. Eliminar flota de una ruta\n"
            "0. Salir"
        )

    def _seleccionar_ruta(self) -> Ruta:
        while True:
            destino = self._leer_texto("Destino: ")
            try:
                return self.terminal.buscar_ruta_destino(destino)
            except KeyError as error:
                self._anunciar_error(str(error))
                print("Ingrese nuevamente un destino válido.")

    def _seleccionar_flota(self, ruta: Ruta) -> Flota:
        if not ruta.flotas:
            raise ValueError(
                f"La ruta {ruta.nombre} no tiene flotas asociadas. "
                "Use primero la opción 2 para crear una flota."
            )
        if len(ruta.flotas) == 1:
            return ruta.flota
        print(f"Flotas disponibles para {ruta.nombre}:")
        for flota in ruta.flotas:
            print(f"- {flota.nombre}")
        while True:
            nombre = self._leer_texto("Nombre de la flota: ")
            try:
                return ruta.buscar_flota(nombre)
            except KeyError as error:
                self._anunciar_error(str(error))
                print("Ingrese nuevamente un nombre de flota válido.")

    def _crear_ruta(self) -> None:
        while True:
            if self.terminal.ciudad_origen is None:
                ciudad = self._leer_texto("Ciudad del terminal: ")
                self.terminal.establecer_ciudad_origen(ciudad)
            origen = self.terminal.ciudad_origen
            destino = self._leer_texto("Destino: ")
            try:
                self.terminal.agregar_ruta(Ruta(origen, destino))
                break
            except ValueError as error:
                self._anunciar_error(str(error))
                print("Ingrese una ruta válida e intente nuevamente.")
        guardar_terminal(self.terminal, self.archivo_datos)
        print("Ruta creada y guardada.")

    def _crear_flota(self) -> None:
        ruta = self._seleccionar_ruta()
        nombre = self._leer_texto("Nombre de la nueva flota: ")
        ruta.agregar_flota(Flota(nombre=nombre))
        guardar_terminal(self.terminal, self.archivo_datos)
        print(f"Flota {nombre} creada y guardada para la ruta {ruta.nombre}.")

    def _eliminar_flota(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        confirmacion = self._leer_confirmacion(
            f"¿Eliminar la flota {flota.nombre} de la ruta {ruta.nombre}? (SI/NO): "
        )
        if not confirmacion:
            print("Eliminación cancelada.")
            return
        ruta.eliminar_flota(flota.nombre)
        guardar_terminal(self.terminal, self.archivo_datos)
        print(f"Flota {flota.nombre} eliminada y datos guardados.")

    def _eliminar_ruta(self) -> None:
        ruta = self._seleccionar_ruta()
        confirmacion = self._leer_texto(
            f"Escriba 'SI' para eliminar la ruta {ruta.nombre}: "
        ).upper()
        if confirmacion != "SI":
            print("Eliminación cancelada.")
            return
        self.terminal.eliminar_ruta(ruta.destino)
        guardar_terminal(self.terminal, self.archivo_datos)
        print("Ruta eliminada y datos guardados.")

    def _eliminar_vehiculo(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        identificador = self._leer_texto("Identificador del vehículo: ")
        vehiculo = flota.buscar_vehiculo(identificador)
        confirmacion = self._leer_texto(
            f"Escriba 'SI' para eliminar {vehiculo.identificador}: "
        ).upper()
        if confirmacion != "SI":
            print("Eliminación cancelada.")
            return
        flota.eliminar_vehiculo(identificador)
        guardar_terminal(self.terminal, self.archivo_datos)
        print("Vehículo eliminado y datos guardados.")

    def _reingresar_vehiculo(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        identificador = self._leer_texto("Identificador del vehículo que regresó: ")
        vehiculo = flota.buscar_vehiculo(identificador)
        if vehiculo.disponible:
            print("El vehículo ya está disponible.")
            return
        confirmacion = self._leer_confirmacion(
            f"¿Marcar {vehiculo.identificador} como disponible? (SI/NO): "
        )
        if not confirmacion:
            print("Reingreso cancelado.")
            return
        vehiculo.reingresar()
        guardar_terminal(self.terminal, self.archivo_datos)
        print(f"Vehículo {vehiculo.identificador} disponible nuevamente.")

    def _registrar_salida(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        identificador = self._leer_texto("Identificador del vehículo que salió: ")
        vehiculo = flota.buscar_vehiculo(identificador)
        if not vehiculo.disponible:
            print("El vehículo ya está registrado fuera de disponibilidad.")
            return
        confirmacion = self._leer_confirmacion(
            f"¿Registrar salida de {vehiculo.identificador}? (SI/NO): "
        )
        if not confirmacion:
            print("Salida cancelada.")
            return
        flota.registrar_salida(identificador)
        guardar_terminal(self.terminal, self.archivo_datos)
        print(f"Vehículo {vehiculo.identificador} salió y quedó fuera de disponibilidad.")

    def _listar_rutas(self) -> None:
        if not self.terminal.rutas:
            print("No hay rutas registradas.")
            return
        for ruta in self.terminal.rutas:
            print(f"\nRuta: {ruta.nombre}")
            print(f"  Flotas asociadas ({len(ruta.flotas)}):")
            for flota in ruta.flotas:
                print(f"    Flota: {flota.nombre}")
                if flota.tarifas_por_tipo:
                    print("      Tarifas de la flota:")
                    for tipo, tarifa in flota.tarifas_por_tipo.items():
                        recargo = flota.recargos_por_tipo.get(tipo, 0.0)
                        print(
                            f"        {tipo}: base ${tarifa:.2f} + "
                            f"recargo ${recargo:.2f} = ${tarifa + recargo:.2f}"
                        )
                else:
                    print("      Sin tarifas configuradas.")
                if not flota.vehiculos:
                    print("      Sin vehículos asignados.")
                    continue
                for vehiculo in flota.vehiculos:
                    tarifa = "no configurada"
                    if vehiculo.tipo_servicio in flota.tarifas_por_tipo:
                        tarifa = f"${flota.calcular_tarifa(vehiculo.tipo_servicio):.2f}"
                    print(
                        f"      {vehiculo.identificador} | {vehiculo.tipo} | "
                        f"ocupados: {vehiculo.asientos_ocupados}/{vehiculo.capacidad} | "
                        f"precio: {tarifa} | "
                        f"estado: {'disponible' if vehiculo.disponible else 'en viaje'}"
                    )

    def _agregar_vehiculo(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        identificador = self._leer_texto("Identificador del vehículo: ")
        tipo = self._leer_tipo_vehiculo()
        if tipo == "estandar":
            capacidad = self._leer_entero("Capacidad: ")
            vehiculo = AutobusEstandar(identificador, capacidad, 0.0)
        elif tipo == "ejecutivo":
            capacidad = self._leer_entero("Capacidad: ")
            servicios = self._leer_texto("Servicios VIP separados por coma: ")
            servicios_vip = [item.strip() for item in servicios.split(",") if item.strip()]
            vehiculo = AutobusEjecutivo(
                identificador,
                capacidad,
                0.0,
                servicios_vip,
            )
        elif tipo == "taxi":
            vehiculo = Taxi(identificador, 0.0)
        while True:
            try:
                flota.agregar_vehiculo(vehiculo)
                break
            except (TypeError, ValueError) as error:
                self._anunciar_error(str(error))
                identificador = self._leer_texto(
                    "Identificador diferente del vehículo: "
                )
                vehiculo.identificador = identificador
        guardar_terminal(self.terminal, self.archivo_datos)
        print("Vehículo agregado y datos guardados.")

    def _abordar_pasajeros(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        while True:
            try:
                tipo = self._leer_tipo_vehiculo()
                print(f"Servicio seleccionado: {tipo}")
                if not flota.tiene_vehiculos_disponibles(tipo):
                    print(
                        f"La flota {flota.nombre} no tiene vehículos disponibles "
                        f"del tipo {tipo}. El abordaje se canceló."
                    )
                    return
                if not self._leer_confirmacion("¿Desea abordar este servicio? (SI/NO): "):
                    print("Abordaje cancelado.")
                    return
                cantidad = self._leer_entero("Cantidad de pasajeros: ")
                es_estudiante = self._leer_confirmacion("¿Es estudiante? (SI/NO): ")
                es_mayor_de_60 = False
                if not es_estudiante:
                    es_mayor_de_60 = self._leer_confirmacion(
                        "¿Tiene 60 años o más? (SI/NO): "
                    )
                aplica_recargo = not (es_estudiante or es_mayor_de_60)
                tarifa = flota.calcular_tarifa(tipo, aplicar_recargo=aplica_recargo)
                vehiculo = flota.abordar_por_tipo(tipo, cantidad)
                break
            except (ErrorDominio, KeyError, ValueError) as error:
                self._anunciar_error(str(error))
                print("Ingrese nuevamente el tipo de servicio y la cantidad.")
        guardar_terminal(self.terminal, self.archivo_datos)
        print("\n=== FACTURA DE ABORDAJE ===")
        print(f"Ruta: {ruta.nombre}")
        print(f"Flota: {flota.nombre}")
        print(f"Servicio: {tipo}")
        print(f"Pasajeros: {cantidad}")
        print(f"Vehículo/placa asignado: {vehiculo.identificador}")
        print(f"Recargo aplicado: {'SI' if aplica_recargo else 'NO'}")
        print(f"Tarifa por pasajero: ${tarifa:.2f}")
        print(f"Total: ${tarifa * cantidad:.2f}")

    def _mostrar_costos(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        tipos = ("estandar", "ejecutivo", "taxi")
        if not flota.tarifas_configuradas:
            self._anunciar_error(
                f"la flota '{flota.nombre}' no tiene configuradas las tarifas de todos los tipos"
            )
            print("Configure las tarifas de la flota antes de consultarlas.")
            return
        print(f"\n=== TARIFAS DE {flota.nombre} EN LA RUTA {ruta.nombre} ===")
        for tipo in tipos:
            base = flota.tarifas_por_tipo[tipo]
            recargo = flota.recargos_por_tipo[tipo]
            tarifa = base + recargo
            print(
                f"{tipo}: base ${base:.2f} + recargo ${recargo:.2f} "
                f"= total ${tarifa:.2f}"
            )

    def _configurar_tarifa(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        if flota.tarifas_configuradas:
            self._anunciar_error("las tarifas de esta flota ya están definidas")
            print("Use la opción 5 para modificarlas.")
            return
        tarifas = self._leer_tarifas()
        flota.configurar_tarifas(tarifas)
        guardar_terminal(self.terminal, self.archivo_datos)
        print(f"Tarifas y recargos configurados para {flota.nombre} y guardados.")

    def _modificar_tarifas(self) -> None:
        ruta = self._seleccionar_ruta()
        flota = self._seleccionar_flota(ruta)
        tarifas = self._leer_tarifas()
        flota.modificar_tarifas(tarifas)
        guardar_terminal(self.terminal, self.archivo_datos)
        print(f"Tarifas y recargos de {flota.nombre} modificados y guardados.")

    def _leer_tarifas(self) -> dict[str, tuple[float, float]]:
        tarifas = {}
        for tipo in ("estandar", "ejecutivo", "taxi"):
            print(f"\nConfiguración para vehículo {tipo}")
            tarifa = self._leer_float(f"Tarifa base de {tipo}: ")
            recargo = self._leer_float(f"Recargo de {tipo}: ")
            tarifas[tipo] = (tarifa, recargo)
        return tarifas

    @staticmethod
    def _anunciar_error(mensaje: str) -> None:
        print(f"El tipo de dato o información a registrar no es correcto: {mensaje}")
        print("Ingrese un valor válido.")

    @staticmethod
    def _leer_texto(mensaje: str) -> str:
        while True:
            valor = input(mensaje).strip().upper()
            if valor:
                return valor
            AplicacionConsola._anunciar_error("el texto no puede estar vacío")

    @staticmethod
    def _leer_opcion() -> str:
        while True:
            opcion = input("Seleccione una opción: ").strip()
            if opcion in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"}:
                return opcion
            AplicacionConsola._anunciar_error("la opción debe estar entre 0 y 13")

    @staticmethod
    def _leer_tipo_vehiculo() -> str:
        tipos = {"estandar", "ejecutivo", "taxi"}
        while True:
            tipo = input("Tipo (ESTANDAR, EJECUTIVO, TAXI): ").strip().upper().lower()
            if tipo in tipos:
                return tipo
            AplicacionConsola._anunciar_error("tipo de vehículo no reconocido")

    @staticmethod
    def _leer_confirmacion(mensaje: str) -> bool:
        while True:
            respuesta = input(mensaje).strip().upper()
            if respuesta in {"SI", "SÍ"}:
                return True
            if respuesta in {"NO", "N"}:
                return False
            AplicacionConsola._anunciar_error("responda SI o NO")

    @staticmethod
    def _leer_entero(mensaje: str, minimo: int = 1) -> int:
        while True:
            valor = input(mensaje).strip()
            try:
                numero = int(valor)
                if numero >= minimo:
                    return numero
                raise ValueError
            except ValueError:
                AplicacionConsola._anunciar_error(
                    f"debe ingresar un número entero mayor o igual que {minimo}"
                )

    @staticmethod
    def _leer_float(mensaje: str, minimo: float = 0.0) -> float:
        while True:
            valor = input(mensaje).strip()
            try:
                numero = float(valor)
                if numero >= minimo:
                    return numero
                raise ValueError
            except ValueError:
                AplicacionConsola._anunciar_error(
                    f"debe ingresar un número mayor o igual que {minimo}"
                )


def ejecutar_aplicacion() -> None:
    try:
        AplicacionConsola().ejecutar()
    except ErrorPersistencia as error:
        print(f"No se pudo iniciar la aplicación: {error}")
    except EOFError:
        print("No se recibió ninguna entrada. El sistema se cerró de forma segura.")
