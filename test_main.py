import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain import (
    AutobusEjecutivo,
    AutobusEstandar,
    CapacidadExcedidaError,
    Flota,
    Ruta,
    Taxi,
    Terminal,
)
from persistence import ErrorPersistencia, cargar_terminal, guardar_terminal
from console import AplicacionConsola


class VehiculoTestCase(unittest.TestCase):
    def test_abordaje_actualiza_ocupacion_sin_exponer_asignacion(self):
        autobus = AutobusEstandar("BUS-1", 40, 100, 5, 7)
        autobus.abordar(3)

        self.assertEqual(autobus.asientos_ocupados, 3)
        self.assertEqual(autobus.asientos_disponibles, 37)
        with self.assertRaises(AttributeError):
            autobus.asientos_ocupados = 10

    def test_rechaza_sobrecupo_y_no_modifica_ocupacion(self):
        taxi = Taxi("TAXI-1", 50)
        with self.assertRaises(CapacidadExcedidaError):
            taxi.abordar(5)
        self.assertEqual(taxi.asientos_ocupados, 0)

    def test_taxi_tiene_exactamente_cuatro_puestos(self):
        taxi = Taxi("TAXI-2", 50)
        self.assertEqual(taxi.capacidad, 4)
        taxi.abordar(4)
        self.assertEqual(taxi.asientos_disponibles, 0)

    def test_costos_son_polimorficos(self):
        estandar = AutobusEstandar("BUS-2", 40, 100, 5, 7)
        ejecutivo = AutobusEjecutivo("BUS-3", 30, 100, ["Wi-Fi"], 25, 5, 7)
        taxi = Taxi("TAXI-3", 100, 10, 5, 7)

        self.assertEqual(estandar.calcular_costo_total(), 112)
        self.assertEqual(ejecutivo.calcular_costo_total(), 137)
        self.assertEqual(taxi.calcular_costo_total(), 122)

    def test_flota_procesa_vehiculos_heterogeneos(self):
        flota = Flota()
        flota.agregar_vehiculo(AutobusEstandar("BUS-4", 40, 100))
        flota.agregar_vehiculo(Taxi("TAXI-4", 50))

        flota.abordar("BUS-4", 2)
        flota.abordar("TAXI-4", 4)

        self.assertEqual(flota.buscar_vehiculo("BUS-4").asientos_ocupados, 2)
        self.assertEqual(flota.buscar_vehiculo("TAXI-4").asientos_ocupados, 4)
        self.assertEqual(flota.calcular_costos(), {"BUS-4": 100.0, "TAXI-4": 60.0})

    def test_abordaje_por_tipo_respeta_el_orden_de_la_flota(self):
        flota = Flota()
        primer_taxi = Taxi("TAXI-1", 50)
        segundo_taxi = Taxi("TAXI-2", 50)
        flota.agregar_vehiculo(primer_taxi)
        flota.agregar_vehiculo(segundo_taxi)

        asignado = flota.abordar_por_tipo(" taxi ", 1)
        self.assertIs(asignado, primer_taxi)
        self.assertEqual(primer_taxi.asientos_ocupados, 1)
        self.assertEqual(segundo_taxi.asientos_ocupados, 0)

        primer_taxi.abordar(3)
        asignado = flota.abordar_por_tipo("taxi", 1)
        self.assertIs(asignado, segundo_taxi)

    def test_vehiculo_en_viaje_no_recibe_pasajeros(self):
        flota = Flota()
        primer_taxi = Taxi("TAXI-1", 50)
        segundo_taxi = Taxi("TAXI-2", 50)
        flota.agregar_vehiculo(primer_taxi)
        flota.agregar_vehiculo(segundo_taxi)
        primer_taxi.registrar_salida()

        asignado = flota.abordar_por_tipo("taxi", 1)

        self.assertIs(asignado, segundo_taxi)
        self.assertFalse(primer_taxi.disponible)

    def test_reingreso_habilita_vehiculo_y_limpia_ocupacion(self):
        taxi = Taxi("TAXI-4", 50)
        taxi.abordar(2)
        taxi.registrar_salida()

        taxi.reingresar()

        self.assertTrue(taxi.disponible)
        self.assertEqual(taxi.asientos_ocupados, 0)

    def test_vehiculo_reintegrado_espera_si_otro_ya_esta_cargando(self):
        flota = Flota()
        primer_taxi = Taxi("TAXI-1", 50)
        segundo_taxi = Taxi("TAXI-2", 50)
        flota.agregar_vehiculo(primer_taxi)
        flota.agregar_vehiculo(segundo_taxi)

        primer_taxi.registrar_salida()
        asignado = flota.abordar_por_tipo("taxi", 1)
        self.assertIs(asignado, segundo_taxi)

        primer_taxi.reingresar()
        asignado = flota.abordar_por_tipo("taxi", 1)

        self.assertIs(asignado, segundo_taxi)

    def test_vehiculo_que_ya_cargaba_tiene_prioridad_sobre_reintegrado(self):
        flota = Flota()
        primer_taxi = Taxi("TAXI-1", 4)
        segundo_taxi = Taxi("TAXI-2", 4)
        flota.agregar_vehiculo(primer_taxi)
        flota.agregar_vehiculo(segundo_taxi)

        primer_taxi.registrar_salida()
        flota.abordar_por_tipo("taxi", 3)
        primer_taxi.reingresar()

        asignado = flota.abordar_por_tipo("taxi", 1)

        self.assertIs(asignado, segundo_taxi)
        self.assertEqual(segundo_taxi.asientos_ocupados, 4)
        self.assertEqual(primer_taxi.asientos_ocupados, 0)

    def test_turno_rotativo_avanza_con_cada_salida(self):
        flota = Flota()
        primer_taxi = Taxi("TAXI-1", 4)
        segundo_taxi = Taxi("TAXI-2", 4)
        tercer_taxi = Taxi("TAXI-3", 4)
        for taxi in (primer_taxi, segundo_taxi, tercer_taxi):
            flota.agregar_vehiculo(taxi)

        flota.registrar_salida("TAXI-1")
        self.assertIs(flota.abordar_por_tipo("taxi", 1), segundo_taxi)
        flota.registrar_salida("TAXI-2")
        self.assertIs(flota.abordar_por_tipo("taxi", 1), tercer_taxi)
        flota.registrar_salida("TAXI-3")
        primer_taxi.reingresar()
        self.assertIs(flota.abordar_por_tipo("taxi", 1), primer_taxi)

    def test_abordaje_por_tipo_rechaza_servicio_inexistente(self):
        flota = Flota()
        flota.agregar_vehiculo(Taxi("TAXI-3", 50))

        with self.assertRaises(KeyError):
            flota.abordar_por_tipo("ejecutivo", 1)

    def test_abordaje_estandar_usa_el_tipo_de_servicio(self):
        flota = Flota()
        autobus = AutobusEstandar("BUS-1", 32, 0.0)
        flota.agregar_vehiculo(autobus)

        asignado = flota.abordar_por_tipo("estandar", 1)

        self.assertIs(asignado, autobus)
        self.assertEqual(autobus.asientos_ocupados, 1)

    def test_reingresar_vehiculo_reinicia_sus_asientos_ocupados(self):
        autobus = AutobusEstandar("BUS-2", 32, 0.0)
        autobus.abordar(12)

        autobus.reiniciar_ocupacion()

        self.assertEqual(autobus.asientos_ocupados, 0)
        self.assertEqual(autobus.asientos_disponibles, 32)

    def test_ruta_maneja_tarifas_por_tipo_independientes_del_vehiculo(self):
        ruta = Ruta("Caracas", "Valencia")
        ruta.establecer_tarifa(" estandar ", 80)
        ruta.establecer_tarifa("ejecutivo", 120, 15)
        ruta.establecer_tarifa("taxi", 45, 5)

        self.assertEqual(ruta.calcular_tarifa(" ESTANDAR "), 80.0)
        self.assertEqual(ruta.calcular_tarifa("ejecutivo"), 135.0)
        self.assertEqual(ruta.calcular_tarifa("taxi"), 50.0)

    def test_recargo_se_aplica_o_exonera_segun_condicion_del_pasajero(self):
        ruta = Ruta("Caracas", "Valencia")
        ruta.establecer_tarifa("estandar", 80, 15)

        self.assertEqual(ruta.calcular_tarifa("estandar"), 95.0)
        self.assertEqual(ruta.calcular_tarifa("estandar", aplicar_recargo=False), 80.0)
        self.assertEqual(ruta.calcular_tarifa("estandar", aplicar_recargo=True), 95.0)

    def test_tarifas_solo_se_modifican_con_operacion_autorizada(self):
        ruta = Ruta("Caracas", "Valencia")
        tarifas_iniciales = {
            "estandar": (80, 5),
            "ejecutivo": (120, 15),
            "taxi": (45, 5),
        }
        tarifas_nuevas = {
            "estandar": (90, 6),
            "ejecutivo": (140, 20),
            "taxi": (55, 8),
        }

        ruta.configurar_tarifas(tarifas_iniciales)
        with self.assertRaises(ValueError):
            ruta.configurar_tarifas(tarifas_nuevas)

        self.assertEqual(ruta.calcular_tarifa("estandar"), 85.0)
        ruta.modificar_tarifas(tarifas_nuevas)
        self.assertEqual(ruta.calcular_tarifa("estandar"), 96.0)

    def test_no_se_puede_modificar_una_ruta_sin_configuracion_inicial(self):
        ruta = Ruta("Caracas", "Valencia")
        tarifas = {
            "estandar": (80, 5),
            "ejecutivo": (120, 15),
            "taxi": (45, 5),
        }

        with self.assertRaises(ValueError):
            ruta.modificar_tarifas(tarifas)

    def test_terminal_mantiene_una_sola_ciudad_de_origen(self):
        terminal = Terminal("Terminal Norte")
        terminal.agregar_ruta(Ruta("Caracas", "Valencia"))

        self.assertEqual(terminal.ciudad_origen, "Caracas")
        with self.assertRaises(ValueError):
            terminal.agregar_ruta(Ruta("Maracay", "Barquisimeto"))

    def test_flota_y_terminal_pueden_eliminar_elementos(self):
        terminal = Terminal("Terminal Norte")
        ruta = Ruta("Caracas", "Valencia")
        ruta.flota.agregar_vehiculo(Taxi("TAXI-1", 50))
        terminal.agregar_ruta(ruta)

        eliminado = ruta.flota.eliminar_vehiculo("TAXI-1")
        ruta_eliminada = terminal.eliminar_ruta("Valencia")

        self.assertEqual(eliminado.identificador, "TAXI-1")
        self.assertEqual(ruta_eliminada.destino, "Valencia")
        self.assertEqual(terminal.rutas, [])


class PersistenciaTestCase(unittest.TestCase):
    def test_guarda_y_carga_terminal_con_ocupacion_y_servicios(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "terminal.json"
            terminal = Terminal("Terminal Norte")
            ruta = Ruta("Caracas", "Valencia")
            ruta.establecer_tarifa("ejecutivo", 200, 30)
            ejecutivo = AutobusEjecutivo(
                "EJ-1", 30, 150, ["Wi-Fi", "Catering"], 30, 4, 6
            )
            ejecutivo.abordar(8)
            ruta.flota.agregar_vehiculo(ejecutivo)
            terminal.agregar_ruta(ruta)

            guardar_terminal(terminal, archivo)
            restaurado = cargar_terminal(archivo)
            vehiculo = restaurado.rutas[0].flota.vehiculos[0]

            self.assertEqual(restaurado.nombre, "Terminal Norte")
            self.assertEqual(restaurado.ciudad_origen, "Caracas")
            self.assertEqual(restaurado.rutas[0].nombre, "Caracas -> Valencia")
            self.assertEqual(vehiculo.asientos_ocupados, 8)
            self.assertEqual(vehiculo.servicios_vip, ["Wi-Fi", "Catering"])
            self.assertEqual(restaurado.rutas[0].calcular_tarifa("ejecutivo"), 230.0)
            self.assertEqual(restaurado.rutas[0].recargos_por_tipo["ejecutivo"], 30.0)

    def test_persistencia_conserva_vehiculo_fuera_de_disponibilidad(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "terminal.json"
            terminal = Terminal("Terminal Norte")
            ruta = Ruta("Caracas", "Valencia")
            taxi = Taxi("TAXI-5", 50)
            taxi.registrar_salida()
            ruta.flota.agregar_vehiculo(taxi)
            terminal.agregar_ruta(ruta)

            guardar_terminal(terminal, archivo)
            restaurado = cargar_terminal(archivo)

            self.assertFalse(restaurado.rutas[0].flota.vehiculos[0].disponible)

    def test_archivo_inexistente_crea_terminal_vacio(self):
        with tempfile.TemporaryDirectory() as directorio:
            terminal = cargar_terminal(Path(directorio) / "no_existe.json")
            self.assertEqual(terminal.rutas, [])

    def test_archivo_corrupto_lanza_error(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "terminal.json"
            archivo.write_text("{no es json", encoding="utf-8")
            with self.assertRaises(ErrorPersistencia):
                cargar_terminal(archivo)


class EntradaConsolaTestCase(unittest.TestCase):
    def test_texto_ingresado_se_normaliza_a_mayusculas(self):
        with patch("builtins.input", return_value="  hada236  "):
            resultado = AplicacionConsola._leer_texto("Identificador: ")

        self.assertEqual(resultado, "HADA236")

    def test_texto_limpia_espacios_y_repite_si_esta_vacio(self):
        with patch("builtins.input", side_effect=["   ", "  Caracas  "]), patch(
            "builtins.print"
        ) as imprimir:
            resultado = AplicacionConsola._leer_texto("Origen: ")

        self.assertEqual(resultado, "CARACAS")
        self.assertTrue(
            any("tipo de dato" in llamada.args[0] for llamada in imprimir.call_args_list)
        )

    def test_entero_repite_entrada_no_valida(self):
        with patch("builtins.input", side_effect=[" texto ", "  4  "]), patch(
            "builtins.print"
        ) as imprimir:
            resultado = AplicacionConsola._leer_entero("Pasajeros: ")

        self.assertEqual(resultado, 4)
        self.assertTrue(
            any("Ingrese un valor válido" in llamada.args[0] for llamada in imprimir.call_args_list)
        )

    def test_opcion_repite_hasta_recibir_una_opcion_valida(self):
        with patch("builtins.input", side_effect=[" 12 ", " 0 "]), patch(
            "builtins.print"
        ) as imprimir:
            resultado = AplicacionConsola._leer_opcion()

        self.assertEqual(resultado, "0")
        self.assertTrue(imprimir.called)

    def test_tipo_desconocido_lanza_error(self):
        with tempfile.TemporaryDirectory() as directorio:
            archivo = Path(directorio) / "terminal.json"
            archivo.write_text(
                json.dumps(
                    {
                        "nombre": "Terminal",
                        "rutas": [
                            {
                                "origen": "A",
                                "destino": "B",
                                "vehiculos": [{"tipo": "avion", "identificador": "X"}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ErrorPersistencia):
                cargar_terminal(archivo)


if __name__ == "__main__":
    unittest.main()
