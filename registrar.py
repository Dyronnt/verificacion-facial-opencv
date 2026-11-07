import cv2
from pathlib import Path

Path("datos").mkdir(exist_ok=True)
cascada = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

camara = cv2.VideoCapture(0)
if not camara.isOpened():
    raise RuntimeError("No se pudo abrir la cámara")


contador = 0
while contador < 35:
    ok, cuadro = camara.read()
    if not ok:
        break
    gris = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)
    rostros = cascada.detectMultiScale(gris, 1.2, 5, minSize=(80, 80))
    if len(rostros) == 1:
        x, y, w, h = rostros[0]
        rostro = cv2.resize(gris[y : y + h, x : x + w], (160, 160))
        cv2.imwrite(f"datos/usuario1_{contador:03}.png", rostro)
        contador += 1
        cv2.rectangle(cuadro, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.putText(
        cuadro,
        f"Muestras: {contador}/35",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 0),
        2,
    )
    cv2.imshow("Registro consentido", cuadro)
    if cv2.waitKey(120) & 0xFF == ord("q"):
        break
camara.release()
cv2.destroyAllWindows()
