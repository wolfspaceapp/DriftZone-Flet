# DriftZone Flet

App móvil de películas, series y anime construida con [Flet](https://flet.dev) (Flutter + Python).

## Requisitos

- Python 3.9+
- Flet 0.86.5

## Desarrollo local

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Compilar el APK

El APK se compila automáticamente en GitHub Actions. Cada push a `main` (o
ejecución manual del workflow) genera un APK y crea un **Release** con el
archivo `.apk` adjunto.

También puedes compilarlo localmente si tienes Flutter instalado:

```powershell
flet build apk
```

El APK resultante queda en `build/apk/`.

## Estructura

- `main.py` — código de la aplicación
- `pyproject.toml` — configuración del paquete Flet (org, package id, deps)
- `requirements.txt` — dependencias de Python
- `.github/workflows/build-apk.yml` — workflow de compilación y release
