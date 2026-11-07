# Verificación facial con OpenCV

Prototipo académico desarrollado en Python que permite registrar muestras faciales, entrenar un modelo LBPH y verificar un rostro mediante una cámara web.

El programa simula la autorización de acceso a una aplicación. No desbloquea el sistema operativo ni controla dispositivos físicos.

## Requisitos

- Python y un entorno virtual.
- Cámara web disponible y permisos para utilizarla.
- Entorno local con interfaz gráfica para mostrar las ventanas de OpenCV.
- Dependencias especificadas en `requirements.txt`:

```text
numpy==2.5.4
opencv-contrib-python==5.0.0.93
```

La instalación de estas versiones depende de que existan paquetes compatibles con la versión de Python y el sistema operativo utilizados.

## Archivos del proyecto

| Archivo | Función |
| --- | --- |
| `registrar.py` | Captura hasta 35 muestras faciales del participante. |
| `entrenar.py` | Entrena un modelo LBPH con al menos 15 muestras válidas. |
| `verificar.py` | Verifica el rostro e integra las primeras cinco mejoras. |
| `eliminar_datos.py` | Elimina las muestras y el modelo después de solicitar confirmación. |
| `requirements.txt` | Especifica las versiones de las dependencias. |
| `.gitignore` | Excluye datos biométricos, registros locales y archivos del entorno virtual. |
| `README.md` | Describe la instalación, ejecución y funcionamiento del proyecto. |

## Archivos generados durante el uso

| Elemento | Contenido |
| --- | --- |
| `datos/` | Muestras faciales con nombres como `usuario1_000.png`. |
| `modelo/lbph.yml` | Modelo generado durante el entrenamiento. |
| `calibracion.csv` | Estadísticas de comparación de los tres umbrales. |
| `eventos.csv` | Fecha, hora, resultado y motivo de los eventos registrados. |

Estos elementos se generan localmente y se excluyen del repositorio mediante `.gitignore`.

## Instalación en Windows

Abre una terminal dentro de la carpeta del proyecto.

### 1. Crear el entorno virtual

```powershell
python -m venv .venv
```

### 2. Activar el entorno virtual

En PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En CMD:

```bat
.venv\Scripts\activate.bat
```

### 3. Instalar las dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Evita instalar otras variantes de OpenCV en el mismo entorno, porque comparten el módulo `cv2`.

### 4. Comprobar la instalación

```powershell
python -c "import cv2; print(cv2.__version__); print(hasattr(cv2, 'face'))"
```

La comprobación debe mostrar la versión de OpenCV y `True`, indicando que el módulo `cv2.face` está disponible.

## Ejecución

Ejecuta los programas desde la carpeta del proyecto y con el entorno virtual activado.

### 1. Registrar muestras

```powershell
python registrar.py
```

El programa crea la carpeta `datos/` si no existe y captura hasta 35 muestras cuando detecta exactamente un rostro.

Cada muestra se convierte a escala de grises y se redimensiona a 160 × 160 píxeles. Presiona `q` para finalizar anticipadamente.

Utiliza únicamente tu propio rostro o el de una persona que haya autorizado expresamente su participación.

### 2. Entrenar el modelo

```powershell
python entrenar.py
```

El entrenamiento requiere al menos 15 muestras válidas. Se utiliza la etiqueta `1` para el usuario registrado.

Al finalizar, se genera el archivo:

```text
modelo/lbph.yml
```

### 3. Verificar el rostro

```powershell
python verificar.py
```

El programa detecta rostros y evalúa la calidad de la imagen antes de realizar la predicción.

Para autorizar el acceso simulado deben cumplirse estas condiciones:

- Aparece exactamente un rostro.
- El brillo y la nitidez superan los límites configurados.
- La etiqueta predicha es `1`.
- La distancia LBPH es menor que el umbral seleccionado.
- Se mantienen ocho cuadros consecutivos válidos.

Cualquier cuadro inválido reinicia el contador de confirmación.

### Controles del teclado

La ventana de OpenCV debe estar seleccionada para recibir las teclas.

| Tecla | Acción |
| --- | --- |
| `R` | Indica que se está probando con la persona registrada. |
| `N` | Indica que se está probando con una persona no registrada. |
| `P` | Pausa la recopilación de estadísticas de calibración. |
| `1` | Selecciona el umbral 50 para decidir el acceso. |
| `2` | Selecciona el umbral 65 para decidir el acceso. |
| `3` | Selecciona el umbral 80 para decidir el acceso. |
| `Q` | Cierra la verificación. |

Las teclas R y N indican la condición real del participante para clasificar los resultados de calibración. No autorizan ni deniegan directamente el acceso.

La tecla P pausa únicamente el conteo de estadísticas; la verificación continúa funcionando.

## Mejoras implementadas

### 1. Calibración del umbral

Se comparan los umbrales 50, 65 y 80 sobre las mismas predicciones.

Para cada umbral se contabilizan:

- Aceptaciones correctas.
- Rechazos correctos.
- Falsas aceptaciones.
- Falsos rechazos.

El participante indica la condición real mediante R o N. Si no se selecciona una condición, no se acumulan estadísticas.

Los resultados cuentan cuadros evaluados con calidad suficiente, no intentos independientes de acceso. La selección del umbral para decidir el acceso es manual; el programa no elige automáticamente el mejor valor.

Al finalizar la verificación, se genera o reemplaza `calibracion.csv` con los resultados de esa ejecución.

### 2. Confirmación temporal

Se exigen ocho cuadros consecutivos válidos antes de autorizar el acceso simulado.

Mientras se completa la confirmación, se muestra el estado `CONFIRMANDO`. Cualquier cuadro inválido reinicia el contador.

### 3. Calidad de imagen

Se comprueba el brillo medio del rostro y su nitidez antes de ejecutar la predicción.

Los valores iniciales son:

| Parámetro | Valor |
| --- | --- |
| Brillo medio mínimo | 55 |
| Nitidez mínima, medida mediante la varianza del Laplaciano | 60 |

Si la imagen está demasiado oscura o borrosa, se bloquea la predicción y se muestra una indicación.

Estos límites son experimentales y requieren evaluación con la cámara y las condiciones de uso.

### 4. Registro de eventos

Se guarda en `eventos.csv`:

- Fecha y hora.
- Resultado.
- Motivo.

Se registra un evento cuando cambia el resultado o el motivo, evitando escribir una fila por cada cuadro mientras el estado permanece igual.

También se registra un error si no se puede leer un cuadro de la cámara. El archivo añade nuevos registros sin reemplazar los anteriores y no contiene imágenes.

### 5. Interfaz mejorada

Se añade un panel negro debajo de la imagen para mostrar:

- Resultado y motivo.
- Distancia LBPH.
- Brillo y nitidez.
- Progreso de confirmación.
- Umbral seleccionado.
- Condición de la prueba.
- Controles del teclado.

El rectángulo del rostro es verde cuando el cuadro cumple el criterio de coincidencia y rojo cuando no lo cumple. El rectángulo verde por sí solo no significa que ya se hayan completado los ocho cuadros de confirmación.

### 6. Protección de datos

El programa `eliminar_datos.py` permite eliminar las muestras y el modelo entrenado al finalizar la práctica.

```powershell
python eliminar_datos.py
```

Primero muestra los archivos seleccionados y solicita escribir:

```text
ELIMINAR
```

Cualquier otra respuesta cancela la operación sin borrar archivos.

Los archivos seleccionados para eliminación son:

- `datos/usuario1_*.png`
- `modelo/lbph.yml`

El programa informa cuántos archivos se eliminaron correctamente y muestra los errores que puedan producirse. No elimina automáticamente los CSV, otras imágenes ni copias guardadas en otras ubicaciones.

Después de borrar las muestras y el modelo, es necesario repetir el registro y el entrenamiento para volver a utilizar la verificación.

## Pruebas

La evaluación del prototipo contempla los siguientes escenarios:

| Escenario | Comportamiento que se debe evaluar |
| --- | --- |
| Persona registrada con iluminación suficiente | Coincidencia y autorización tras ocho cuadros válidos. |
| Persona registrada con poca luz | Bloqueo por calidad o rechazo de la coincidencia. |
| Persona voluntaria no registrada | Denegación del acceso y posibles falsas aceptaciones. |
| Ausencia de rostro o presencia de varios rostros | Acceso denegado y contador reiniciado. |
| Fotografía de la persona registrada | Posible suplantación por ausencia de detección de vida. |

Los resultados observados, las distancias y las capturas se documentan en el informe de la práctica.

## Fundamentos

### Píxeles y matrices

Las imágenes digitales se representan como matrices de valores. OpenCV utiliza habitualmente el orden BGR para los canales de una imagen de color.

### Escala de grises

La conversión a escala de grises reduce la imagen a un solo canal para el procesamiento utilizado en esta práctica.

### Detección Haar

El detector Haar Cascade localiza regiones candidatas a rostro. Detectar un rostro no permite determinar su identidad.

### Reconocimiento LBPH

El modelo LBPH compara patrones locales del rostro con las muestras utilizadas durante el entrenamiento.

### Tamaño uniforme

Los rostros se redimensionan a 160 × 160 píxeles para mantener un formato consistente entre registro y verificación.

### Distancia y umbral

Una distancia LBPH menor representa mayor similitud según el modelo. No es un porcentaje de confianza.

El umbral determina cuándo se acepta una coincidencia. Su elección requiere pruebas porque pueden producirse falsas aceptaciones y falsos rechazos.

## Problemas frecuentes

| Problema | Acción |
| --- | --- |
| No existe `cv2.face` | Comprueba que utilizas el entorno virtual correcto y que está instalado `opencv-contrib-python`. |
| No se puede abrir la cámara | Revisa los permisos y cierra otras aplicaciones que puedan estar utilizándola. |
| No existe `modelo/lbph.yml` | Ejecuta primero el registro y después el entrenamiento. |
| No hay suficientes muestras | Registra al menos 15 imágenes válidas. |
| Se rechaza a la persona registrada | Revisa iluminación, enfoque, posición, variedad de muestras y umbral. |
| La calibración muestra todos los contadores en cero | Selecciona R o N y comprueba que el rostro supere los controles de calidad. |
| Las teclas no responden | Selecciona la ventana de OpenCV antes de pulsarlas. |

## Privacidad y publicación

Las imágenes faciales y el modelo entrenado se mantienen localmente y no se publican en GitHub.

El archivo `.gitignore` excluye:

```gitignore
.venv/
venv/
__pycache__/
*.pyc

datos/
modelo/
eventos.csv
calibracion.csv

.xd/
*.zip
```

El repositorio incluye el código y las instrucciones. Cada participante genera sus propias muestras y su modelo al ejecutar los programas.

## Limitaciones

Este sistema es un prototipo académico y no debe utilizarse como autenticación de producción.

No incorpora detección de vida, por lo que una fotografía puede engañar al modelo. La confirmación temporal y los controles de calidad no eliminan esta vulnerabilidad.

La iluminación, el enfoque, la orientación del rostro y la variedad de las muestras pueden afectar los resultados. Las mejoras implementadas permiten controlar y analizar el proceso, pero no garantizan una identificación segura.