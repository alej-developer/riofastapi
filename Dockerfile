# ============================================================
# Dockerfile — Imagen de produccion para Rio API
# ============================================================
# Estrategia: construccion en dos etapas (multi-stage build).
#
# ETAPA 1 (builder): instala todas las dependencias Python en
#   un entorno temporal con las herramientas de compilacion.
#
# ETAPA 2 (final): copia solo el resultado de la etapa 1 y el
#   codigo de la aplicacion. La imagen final NO contiene pip,
#   compiladores, ni ninguna herramienta de construccion.
#   Resultado: imagen mas pequeña, superficie de ataque reducida.
#
# SEGURIDAD:
#   - Se ejecuta como usuario no-root (usuario 'appuser').
#   - No se instalan herramientas de testing ni desarrollo.
#   - El directorio de trabajo pertenece al usuario sin privilegios.
#   - El puerto 8080 es el estandar de Google Cloud Run.
# ============================================================


# ============================================================
# ETAPA 1: builder
# Propósito: instalar y compilar todas las dependencias Python.
# Esta etapa NO llega a la imagen final.
# ============================================================

# python:3.11-slim es la imagen oficial minima de Python 3.11.
# 'slim' omite muchos paquetes del sistema operativo que no son
# necesarios en tiempo de ejecucion (documentacion, locales, etc.).
# Se fija la version exacta (3.11-slim) para garantizar builds
# reproducibles y evitar regresiones por actualizaciones implicitas.
FROM python:3.11-slim AS builder

# Se establece el directorio de trabajo dentro del contenedor
# para todos los comandos RUN, COPY y CMD siguientes.
WORKDIR /app

# Se desactiva el buffer de stdout/stderr de Python.
# Sin esto, los mensajes de log podrian perderse si el proceso
# termina abruptamente (por ejemplo, en un crash de Cloud Run).
# Con PYTHONUNBUFFERED=1 los logs se escriben inmediatamente.
ENV PYTHONUNBUFFERED=1

# Se evita que Python genere archivos .pyc (bytecode compilado)
# dentro del contenedor. Reduce el tamaño de la imagen final
# y evita ruido en el sistema de archivos del contenedor.
ENV PYTHONDONTWRITEBYTECODE=1

# Se actualiza pip a la ultima version disponible.
# Una version desactualizada puede tener vulnerabilidades de
# seguridad o incompatibilidades con paquetes modernos.
# '--no-cache-dir' evita almacenar el cache de pip en la imagen,
# reduciendo el tamaño del layer de Docker.
RUN pip install --no-cache-dir --upgrade pip

# Se copian PRIMERO solo los archivos de dependencias.
# Tecnica de optimizacion de cache de Docker:
# Si requirements-prod.txt no cambia entre builds, Docker
# reutilizara el layer de instalacion de dependencias desde
# el cache, haciendo el build mucho mas rapido.
# Si se copiara todo el codigo primero, cualquier cambio en
# un archivo .py invalidaria este layer costoso.
COPY requirements-prod.txt .

# Se instalan las dependencias de produccion en el directorio
# '/opt/venv' usando un entorno virtual aislado.
# '--prefix' equivale a instalar en un venv sin activarlo.
# Instalamos en '/opt/venv' para poder copiar solo ese directorio
# a la imagen final, dejando fuera pip y sus dependencias.
RUN pip install --no-cache-dir --prefix=/opt/venv -r requirements-prod.txt


# ============================================================
# ETAPA 2: final
# Propósito: imagen minima de produccion lista para ejecutar.
# Solo contiene: Python, las dependencias y el codigo de la app.
# ============================================================

# Se reutiliza la misma imagen base ligera.
# Esto garantiza que la version de Python del runtime coincide
# exactamente con la version usada durante la construccion.
FROM python:3.11-slim AS final

# Se declara el puerto en el que escuchara la aplicacion.
# Cloud Run inyecta la variable de entorno PORT=8080 en tiempo
# de ejecucion. EXPOSE es documentacion: no publica el puerto,
# solo indica cual usara el proceso.
EXPOSE 8080

# Variables de entorno de Python para produccion.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Se añade el directorio de las dependencias instaladas en la
# etapa 'builder' al PATH de Python, para que el interprete
# las encuentre sin necesidad de activar un venv explicito.
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/opt/venv/lib/python3.11/site-packages:$PYTHONPATH"

# Se crea un usuario del sistema sin shell interactivo y sin
# directorio home (--no-create-home). Este usuario 'appuser'
# ejecutara el proceso de la aplicacion.
#
# POR QUE NO USAR ROOT:
# Ejecutar como root dentro de un contenedor es un riesgo de
# seguridad. Si un atacante explota una vulnerabilidad en la
# aplicacion y escapa del contenedor, tendria privilegios de
# root en el host. Un usuario sin privilegios limita el daño.
RUN adduser --disabled-password --no-create-home --gecos "" appuser

# Se establece el directorio de trabajo de la aplicacion.
WORKDIR /app

# Se copian las dependencias compiladas desde la etapa 'builder'.
# Solo se copia el resultado final de pip, no pip en si mismo.
# Esto es lo que hace que la imagen final sea significativamente
# mas pequeña que si se hubiera instalado todo en una sola etapa.
COPY --from=builder /opt/venv /opt/venv

# Se copia el codigo fuente de la aplicacion al contenedor.
# Gracias al .dockerignore, solo se copian los archivos
# necesarios: main.py, app/, frontend/ (sin venv ni tests).
COPY . .

# Se transfiere la propiedad de todos los archivos de /app
# al usuario 'appuser'. Sin esto, el usuario sin privilegios
# no podria leer ni ejecutar los archivos del directorio.
RUN chown -R appuser:appuser /app

# A partir de aqui todos los comandos se ejecutan como 'appuser'.
# Ningun proceso dentro del contenedor tendra privilegios de root.
USER appuser

# Comando de inicio de la aplicacion en produccion.
# Se usa la variable de entorno PORT que Cloud Run inyecta
# (por defecto 8080). El script de shell permite la expansion
# de variables de entorno en el CMD.
#
# Parametros de uvicorn para produccion:
#   --host 0.0.0.0    Escucha en todas las interfaces de red del contenedor.
#   --port $PORT      Usa el puerto que Cloud Run especifica.
#   --workers 2       Dos workers para paralelismo (ajustar segun vCPU de Cloud Run).
#   --loop uvloop     Bucle de eventos de alta performance (incluido en uvicorn[standard]).
#   --access-log      Registra cada peticion en stdout para los logs de Cloud Run.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2 --loop uvloop --access-log"]
