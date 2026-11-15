# Pruebas y evidencias

## Verificación automatizada realizada

Entorno local: Linux, Python 3.12, NumPy 2.3.5, OpenCV contrib 4.11.0.86 y PySide6 Essentials 6.12.0. Interfaz Qt ejecutada con plataforma `offscreen`.

Comando: `python -m unittest discover -s tests -v`.

**Resultado: 14 pruebas correctas.** Se utilizan matrices sintéticas y componentes controlados; no se utilizaron datos biométricos reales.

| Área | Comprobación | Resultado local |
| --- | --- | --- |
| Confirmación | Autorizar a partir del octavo cuadro y reiniciar al perder el rostro. | Correcto |
| Calidad y exclusión | Denegar con varios rostros, oscuridad, desenfoque o etiqueta distinta. | Correcto |
| Calibración | Comparación estricta del umbral, condición real y exportación de tres filas. | Correcto |
| Registro y modelo | Guardar 35 muestras sintéticas e invalidar modelo anterior. | Correcto |
| Entrenamiento | Entrenar, guardar y recargar un LBPH real con imágenes sintéticas. | Correcto |
| Validación | Rechazar muestras insuficientes y cancelar sin publicar modelo. | Correcto |
| Eliminación | Eliminar muestras/modelo y conservar CSV y archivos ajenos. | Correcto |
| Rutas del `.exe` | Resolver `%LOCALAPPDATA%` mediante entorno controlado. | Correcto |
| Interfaz | Consentimiento obligatorio y navegación por cinco pantallas. | Correcto |
| Errores | Modelo ausente y cámara no disponible; recuperación de controles. | Correcto |
| Cierre | Esperar la finalización del hilo antes de cerrar. | Correcto |
| Hilo de registro | Completar 35 imágenes; liberar cámara controlada. | Correcto |
| Cancelación | Conservar muestras y modelo anteriores si se interrumpe el registro. | Correcto |
| Hilo de verificación | Generar estados y CSV sin guardar imágenes de verificación. | Correcto |

Las cinco capturas de `docs/capturas/` muestran ventanas reales en estado vacío. No acreditan reconocimiento facial, exactitud, presencia física ni ejecución del `.exe`.

## Pruebas físicas por completar

Realizar estas pruebas en Windows con la cámara del participante y reemplazar «Pendiente» por lo observado. No completar con resultados supuestos.

| Prueba | Criterio a observar | Resultado | Evidencia sugerida |
| --- | --- | --- | --- |
| Registro consentido | Completa 35 muestras con un rostro y calidad suficiente. | Pendiente | Progreso y estado final, sin exponer terceros. |
| Registro cancelado | Conserva el registro anterior al detener antes de 35. | Pendiente | Estado y conteo de muestras. |
| Entrenamiento | Modelo disponible tras entrenar; interfaz responde. | Pendiente | Pantalla Inicio y mensaje final. |
| Persona registrada | Autoriza solo tras ocho cuadros válidos. | Pendiente | Estado, distancia y progreso. |
| Persona no registrada, con consentimiento | Evaluar rechazo y registrar cualquier falsa aceptación. | Pendiente | Resultado y distancia observada. |
| Poca luz o desenfoque | Bloquea predicción y muestra motivo. | Pendiente | Indicador de calidad. |
| Sin rostro / dos rostros consentidos | Deniega y reinicia la confirmación. | Pendiente | Estado y motivo. |
| Fotografía del participante | Registrar si engaña al prototipo. | Pendiente | Resultado y explicación de la limitación. |
| Calibración | Etiquetar pruebas; comparar 50, 65 y 80. | Pendiente | Tabla y CSV exportado. |
| Eliminación | Cancelar no borra; escribir ELIMINAR borra muestras y modelo. | Pendiente | Confirmación y estado posterior. |
| Distribución Windows | Extraer carpeta completa y abrir el `.exe` sin Python instalado. | Pendiente | Ventana abierta desde la distribución. |
| Datos del `.exe` | Persisten en `%LOCALAPPDATA%\VerificacionFacial` al reiniciar. | Pendiente | Configuración y conteo tras reiniciar. |

La compilación automatizada de Windows se consulta en GitHub Actions. Su estado debe comprobarse antes de afirmar que se generó el artefacto; tampoco sustituye la prueba manual con cámara.

## Conclusión técnica provisional

La implementación integra las operaciones y mantiene los controles del proyecto anterior. Las pruebas automatizadas verifican el flujo y los archivos, pero no permiten afirmar una precisión biométrica ni que la interfaz mejore la resistencia a fotografías. Los hallazgos finales se redactarán después de las pruebas físicas.
