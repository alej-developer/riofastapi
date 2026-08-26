# ============================================================
# README.md - Documentación del Proyecto Río API
# ============================================================

# Río API 🚀

API REST construida con **Python** y **FastAPI** como proyecto base escalable.

## 📁 Estructura del Proyecto

```
Río/
├── main.py                    # Punto de entrada principal de la API
├── requirements.txt           # Dependencias del proyecto
├── .gitignore                 # Archivos ignorados por Git
├── .env                       # Variables de entorno (NO subir a Git)
│
├── app/                       # Paquete principal de la aplicación
│   ├── __init__.py
│   ├── core/                  # Configuración central del proyecto
│   │   ├── __init__.py
│   │   └── config.py          # Variables de entorno y configuración
│   ├── routers/               # Enrutadores de la API (endpoints por recurso)
│   │   └── __init__.py
│   ├── models/                # Modelos de base de datos (ORM)
│   │   └── __init__.py
│   ├── schemas/               # Esquemas Pydantic (validación de datos)
│   │   └── __init__.py
│   └── services/              # Lógica de negocio
│       └── __init__.py
│
└── tests/                     # Pruebas unitarias y de integración
    ├── __init__.py
    └── test_main.py           # Pruebas del endpoint principal
```

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/alej-developer/riofastapi.git
cd riofastapi
```

### 2. Crear y activar el entorno virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows
venv\Scripts\activate

# Activar en Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo y editarlo con tus valores
cp .env.example .env
```

## 🚀 Ejecución

```bash
# Modo desarrollo (con recarga automática)
uvicorn main:app --reload

# Modo producción
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📖 Documentación de la API

Una vez el servidor esté en ejecución, accede a:

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/` | Endpoint de bienvenida (Hola Mundo) |
| `http://localhost:8000/health` | Comprobación de salud del servidor |
| `http://localhost:8000/docs` | Documentación interactiva (Swagger UI) |
| `http://localhost:8000/redoc` | Documentación alternativa (ReDoc) |

## 🧪 Pruebas

```bash
# Ejecutar todas las pruebas
pytest tests/

# Ejecutar con detalle
pytest tests/ -v
```

## 🛡️ Seguridad

Este proyecto incluye las siguientes librerías de seguridad:

- **python-jose**: Para generación y verificación de tokens JWT
- **passlib[bcrypt]**: Para hash seguro de contraseñas
- **python-multipart**: Para manejo seguro de formularios

## 📄 Licencia

MIT License
