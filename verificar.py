import csv
from datetime import datetime
from pathlib import Path

import cv2

BASE = Path(__file__).resolve().parent
RUTA_MODELO = BASE / "modelo" / "lbph.yml"

UMBRALES = (50, 65, 80)
umbral = 65

CUADROS_NECESARIOS = 8
BRILLO_MINIMO = 55
NITIDEZ_MINIMA = 60

# R = persona registrada; N = persona no registrada.
# La condición real la indica el participante, no el modelo.
condicion_real = None

estadisticas = {
    valor: {
        "aceptaciones_correctas": 0,
        "rechazos_correctos": 0,
        "falsas_aceptaciones": 0,
        "falsos_rechazos": 0,
    }
    for valor in UMBRALES
}


def guardar_evento(resultado, motivo):
    ruta = BASE / "eventos.csv"
    nuevo = not ruta.exists() or ruta.stat().st_size == 0

    with ruta.open("a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if nuevo:
            escritor.writerow(["fecha_hora", "resultado", "motivo"])

        escritor.writerow([
            datetime.now().astimezone().isoformat(timespec="seconds"),
            resultado,
            motivo,
        ])


def guardar_calibracion():
    ruta = BASE / "calibracion.csv"

    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow([
            "umbral",
            "aceptaciones_correctas",
            "rechazos_correctos",
            "falsas_aceptaciones",
            "falsos_rechazos",
        ])

        for valor, datos in estadisticas.items():
            escritor.writerow([
                valor,
                datos["aceptaciones_correctas"],
                datos["rechazos_correctos"],
                datos["falsas_aceptaciones"],
                datos["falsos_rechazos"],
            ])


def evaluar_umbrales(etiqueta, distancia):
    if condicion_real is None:
        return

    for valor in UMBRALES:
        aceptado = etiqueta == 1 and distancia < valor

        if condicion_real == "registrada":
            clave = (
                "aceptaciones_correctas"
                if aceptado else "falsos_rechazos"
            )
        else:
            clave = (
                "falsas_aceptaciones"
                if aceptado else "rechazos_correctos"
            )

        estadisticas[valor][clave] += 1


def ejecutar():
    global umbral, condicion_real

    if not hasattr(cv2, "face"):
        raise RuntimeError(
            "Falta cv2.face. Usa opencv-contrib-python en tu entorno."
        )

    if not RUTA_MODELO.is_file():
        raise FileNotFoundError(
            "No existe modelo/lbph.yml. Ejecuta primero entrenar.py."
        )

    modelo = cv2.face.LBPHFaceRecognizer_create()
    modelo.read(str(RUTA_MODELO))

    cascada = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    if cascada.empty():
        raise RuntimeError("No se pudo cargar el detector facial.")

    camara = cv2.VideoCapture(0)
    consecutivos = 0
    ultimo_estado = None

    try:
        if not camara.isOpened():
            raise RuntimeError("No se pudo abrir la camara.")

        while True:
            ok, cuadro = camara.read()

            if not ok:
                guardar_evento("ERROR", "No se pudo leer la camara")
                print("No se pudo leer la camara.")
                break

            gris = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)
            rostros = cascada.detectMultiScale(
                gris,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(80, 80),
            )

            resultado = "DENEGADO"
            motivo = "Ubica un solo rostro frente a la camara"
            detalle = "Distancia: -- | Brillo: -- | Nitidez: --"
            valido = False

            if len(rostros) > 1:
                motivo = "Hay varios rostros: debe aparecer solo uno"

            elif len(rostros) == 1:
                x, y, w, h = rostros[0]
                rostro = cv2.resize(
                    gris[y:y + h, x:x + w], (160, 160)
                )

                brillo = float(rostro.mean())
                nitidez = float(
                    cv2.Laplacian(rostro, cv2.CV_64F).var()
                )

                detalle = (
                    f"Distancia: -- | Brillo: {brillo:.0f}"
                    f" | Nitidez: {nitidez:.0f}"
                )

                if brillo < BRILLO_MINIMO:
                    motivo = "Rostro oscuro: mejora la iluminacion"

                elif nitidez < NITIDEZ_MINIMA:
                    motivo = "Rostro borroso: quedate quieto y ajusta distancia"

                else:
                    etiqueta, distancia = modelo.predict(rostro)
                    evaluar_umbrales(etiqueta, distancia)

                    detalle = (
                        f"Distancia: {distancia:.1f}"
                        f" | Brillo: {brillo:.0f}"
                        f" | Nitidez: {nitidez:.0f}"
                    )

                    valido = etiqueta == 1 and distancia < umbral
                    motivo = "El rostro no coincide con el usuario registrado"

                cv2.rectangle(
                    cuadro, (x, y), (x + w, y + h),
                    (0, 255, 0) if valido else (0, 0, 255), 2,
                )

            # Cualquier cuadro inválido reinicia la confirmación.
            if valido:
                consecutivos = min(
                    consecutivos + 1, CUADROS_NECESARIOS
                )

                if consecutivos >= CUADROS_NECESARIOS:
                    resultado = "AUTORIZADO SIMULADO"
                    motivo = "Coincidencia confirmada"
                else:
                    resultado = "CONFIRMANDO"
                    motivo = "Mantente frente a la camara"
            else:
                consecutivos = 0

            estado = (resultado, motivo)

            # Registra cambios de estado, evitando una fila por cuadro.
            if estado != ultimo_estado:
                guardar_evento(resultado, motivo)
                ultimo_estado = estado

            # Panel separado para no tapar el rostro.
            panel = cv2.copyMakeBorder(
                cuadro, 0, 185, 0, 0,
                cv2.BORDER_CONSTANT, value=(0, 0, 0),
            )

            color = (
                (0, 255, 0)
                if resultado == "AUTORIZADO SIMULADO"
                else (0, 220, 255)
            )

            lineas = [
                resultado,
                motivo,
                detalle,
                f"Confirmacion: {consecutivos}/{CUADROS_NECESARIOS}"
                f" | Umbral: {umbral}",
                f"Prueba: {condicion_real or 'sin etiquetar'}",
                "R: registrada | N: no registrada | P: pausar prueba",
                "1: umbral 50 | 2: umbral 65 | 3: umbral 80 | Q: salir",
            ]

            for i, texto in enumerate(lineas):
                cv2.putText(
                    panel, texto,
                    (10, cuadro.shape[0] + 23 + i * 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.47,
                    color if i == 0 else (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

            cv2.imshow("Verificacion facial - mejoras", panel)
            tecla = cv2.waitKey(1) & 0xFF

            if tecla in (ord("q"), ord("Q")):
                break

            elif tecla in (ord("r"), ord("R")):
                condicion_real = "registrada"
                consecutivos = 0

            elif tecla in (ord("n"), ord("N")):
                condicion_real = "no registrada"
                consecutivos = 0

            elif tecla in (ord("p"), ord("P")):
                condicion_real = None
                consecutivos = 0

            elif tecla in (ord("1"), ord("2"), ord("3")):
                umbral = UMBRALES[tecla - ord("1")]
                consecutivos = 0

    finally:
        camara.release()
        cv2.destroyAllWindows()
        guardar_calibracion()
        print("Comparacion guardada en:", BASE / "calibracion.csv")


if __name__ == "__main__":
    ejecutar()