from pathlib import Path

BASE = Path(__file__).resolve().parent


def eliminar_datos():
    # Seleccionar únicamente las muestras y el modelo de la práctica.
    archivos = sorted((BASE / "datos").glob("usuario1_*.png"))
    modelo = BASE / "modelo" / "lbph.yml"

    if modelo.is_file():
        archivos.append(modelo)

    archivos = [ruta for ruta in archivos if ruta.is_file()]

    if not archivos:
        print("No hay muestras ni modelo para eliminar.")
        return

    print("\nArchivos que se eliminarán:")
    for ruta in archivos:
        print(f" - {ruta.relative_to(BASE)}")

    print("\nEsta acción es irreversible.")
    confirmacion = input(
        "Escribe ELIMINAR para confirmar: "
    ).strip()

    if confirmacion != "ELIMINAR":
        print("Operación cancelada. No se eliminó ningún archivo.")
        return

    eliminados = 0

    for ruta in archivos:
        try:
            ruta.unlink()
            eliminados += 1
            print(f"Eliminado: {ruta.relative_to(BASE)}")
        except OSError as error:
            print(f"No se pudo eliminar {ruta.name}: {error}")

    print(f"\nArchivos eliminados: {eliminados}/{len(archivos)}")

    if eliminados == len(archivos):
        print("Las muestras y el modelo seleccionados fueron eliminados.")


if __name__ == "__main__":
    eliminar_datos()