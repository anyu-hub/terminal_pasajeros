 # Sistema de Terminal de Pasajeros

Aplicación de consola desarrollada en Python para administrar rutas, flotas y vehículos de transporte. Los datos se guardan en `data/terminal.json`, por lo que las rutas, vehículos y asientos ocupados permanecen disponibles al volver a ejecutar el programa.

## Estructura

- `main.py`: punto de entrada.
- `domain.py`: clases del dominio y reglas de negocio.
- `persistence.py`: serialización y persistencia en JSON.
- `console.py`: menú interactivo.
- `test_main.py`: pruebas unitarias con `unittest`.

## Modelo orientado a objetos

- **Abstracción:** `VehiculoTransporte` define la estructura común y obliga a implementar `calcular_costo_total()`.
- **Encapsulamiento:** la ocupación se guarda en `__asientos_ocupados` y solo se modifica mediante `abordar()` o la restauración controlada desde persistencia.
- **Herencia:** `AutobusEstandar`, `AutobusEjecutivo` y `Taxi` extienden `VehiculoTransporte`.
- **Polimorfismo:** `Flota` calcula costos y registra abordajes usando la interfaz común, sin conocer la implementación concreta de cada vehículo.

La composición principal es:

```text
Terminal -> Ruta -> Flota -> VehiculoTransporte
```

Cada terminal tiene una sola ciudad de origen. Al crear la primera ruta se establece esa ciudad; las demás rutas solo solicitan el destino y siempre salen desde el mismo terminal.

## Vehículos y tarifas

- Autobús estándar, ejecutivo y taxi pueden ofrecerse en cada ruta.
- Cada ruta mantiene una tarifa independiente para cada tipo: `estandar`, `ejecutivo` y `taxi`.
- Cada tipo tiene una tarifa base y un recargo configurados en el mismo formulario de la ruta; la tarifa final es la suma de ambos valores.
- La tarifa consultada no depende del identificador ni de la tarifa interna de un vehículo registrado.
- El autobús ejecutivo puede registrar servicios como Wi-Fi o Catering y el taxi mantiene una capacidad fija de 4 puestos.

Un abordaje que supera los puestos disponibles se rechaza y no modifica la ocupación.

Para abordar, el pasajero selecciona el tipo de servicio (`estandar`, `ejecutivo` o `taxi`) y confirma con `SI`. Luego indica si es estudiante; si no lo es, indica si tiene 60 años o más. Si cumple cualquiera de las dos condiciones no se aplica el recargo de la ruta; de lo contrario, se aplica. La flota asigna automáticamente el primer vehículo registrado de ese tipo que tenga capacidad suficiente; cuando se llena, continúa con el siguiente. El identificador o placa no se solicita al pasajero: aparece en la factura de abordaje junto con la ruta, el servicio, la cantidad, el recargo aplicado y el total.

Cuando un vehículo regresa de su viaje, la opción `10. Reingresar vehículo disponible` permite seleccionarlo por ruta e identificador, confirmar su retorno y reiniciar su ocupación para que vuelva a recibir pasajeros. La operación se guarda automáticamente.

Antes de que salga, la opción `11. Registrar salida de vehículo` lo marca como `en viaje`. Mientras permanezca en ese estado no puede recibir pasajeros y el sistema asignará el siguiente vehículo disponible del mismo tipo. Al regresar, se utiliza la opción 10 para habilitarlo de nuevo.

La flota utiliza un turno rotativo por tipo de servicio, no un orden fijo de registro. Cuando un vehículo sale, el turno pasa al siguiente vehículo del mismo tipo. Si un vehículo reingresa, conserva su posición en el ciclo y espera hasta que los demás vehículos hayan tenido su salida y el turno vuelva a él. Los vehículos que ya están cargando pasajeros tienen prioridad para completar su capacidad antes de avanzar.

Todos los textos ingresados se limpian y se convierten a mayúsculas automáticamente; los números conservan su formato numérico.

## Validación de entradas

El menú permite eliminar rutas y vehículos solicitando una confirmación `SI`; los datos se guardan inmediatamente después de eliminar.

También valida cada dato antes de registrarlo. La opción de configuración solicita consecutivamente tarifa base y recargo para `estandar`, `ejecutivo` y `taxi`, y guarda todo automáticamente al terminar. Si se introduce un tipo incorrecto, un texto vacío, un número inválido, una opción inexistente o una cantidad fuera de rango, el sistema muestra un mensaje y vuelve a solicitar ese dato hasta recibir uno válido. Los espacios al principio y al final se eliminan automáticamente; por ejemplo, `  Caracas  ` se guarda como `Caracas`.

Las tarifas se configuran una sola vez mediante la opción 6. Si una ruta ya tiene sus tres tarifas definidas, esa opción no las sobrescribe. Los cambios posteriores solo se pueden realizar mediante la opción 9, `Modificar tarifas y recargos de la ruta`.

## Ejecución

Desde la carpeta `sistema_terminal`:

```bash
python main.py
```

El menú permite crear rutas, agregar vehículos, abordar pasajeros, consultar todas las tarifas de una ruta en una sola vista, configurar tarifas y modificarlas mediante la opción exclusiva de modificación. Los cambios se guardan automáticamente; la opción `0` guarda antes de salir y es la única opción de salida. Si el archivo JSON no existe, se crea una terminal vacía al guardar por primera vez.

## Pruebas

```bash
python -m unittest discover -v
```

Las pruebas verifican capacidades, encapsulamiento, costos polimórficos, composición de objetos y persistencia con JSON, incluyendo archivos corruptos y tipos de vehículo desconocidos.
