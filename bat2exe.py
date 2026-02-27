import os
import subprocess
import shutil


def convertir_bat_a_exe_en_carpeta(carpeta):
    if not os.path.isdir(carpeta):
        print("La ruta indicada no es una carpeta válida.")
        return

    # Listar todos los .bat
    archivos_bat = [f for f in os.listdir(carpeta) if f.lower().endswith(".bat")]

    if not archivos_bat:
        print("No se encontraron archivos .bat en la carpeta.")
        return

    print(f"Encontrados {len(archivos_bat)} archivos .bat. Convirtiendo...\n")

    for bat in archivos_bat:
        ruta_bat = os.path.join(carpeta, bat)
        nombre_base = os.path.splitext(bat)[0]
        nombre_exe = nombre_base  # sin extensión, PyInstaller agrega .exe

        print(f"Creando EXE para: {bat}")

        # Crear wrapper temporal
        wrapper_py = os.path.join(carpeta, f"wrapper_{nombre_base}.py")
        with open(wrapper_py, "w") as f:
            f.write(f'import os\nos.system(r"{ruta_bat}")')

        # Ejecutar pyinstaller
        subprocess.call([
            "pyinstaller",
            "--onefile",
            "--distpath", carpeta,  # EXE final en misma carpeta
            "--workpath", os.path.join(carpeta, "build_tmp"),  # carpeta temporal
            "--specpath", carpeta,  # colocar el .spec ahí también
            "--name", nombre_exe,
            wrapper_py
        ])

        # Eliminar wrapper y archivos temporales
        os.remove(wrapper_py)

        # limpiar .spec
        spec_file = os.path.join(carpeta, f"{nombre_exe}.spec")
        if os.path.exists(spec_file):
            os.remove(spec_file)

        print(f"✔ EXE creado: {nombre_exe}.exe\n")

    # Borrar carpeta temporal build_tmp
    build_tmp = os.path.join(carpeta, "build_tmp")
    if os.path.isdir(build_tmp):
        shutil.rmtree(build_tmp)

    print("✔ Todos los archivos fueron convertidos exitosamente.")


# ------------------------------
# EJECUCIÓN
# ------------------------------
if __name__ == "__main__":
    carpeta = input("Indica la carpeta donde están los .bat: ").strip('"')
    convertir_bat_a_exe_en_carpeta(carpeta)

