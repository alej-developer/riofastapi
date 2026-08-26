# Rio API

API REST construida con Python y FastAPI. Incluye un CRUD completo de tareas, ciberseguridad por capas (CORS restrictivo, rate limiting, cabeceras HTTP de seguridad), validacion estricta de datos con Pydantic, suite de tests automatizados y un frontend minimalista servido desde el mismo servidor.

---

## Indice

1. [Estructura del proyecto](#estructura-del-proyecto)
2. [Requisitos previos](#requisitos-previos)
3. [Instalacion y ejecucion en local](#instalacion-y-ejecucion-en-local)
4. [Ejecucion de los tests](#ejecucion-de-los-tests)
5. [Despliegue con Docker en local](#despliegue-con-docker-en-local)
6. [Despliegue en Google Cloud Run](#despliegue-en-google-cloud-run)
7. [Variables de entorno](#variables-de-entorno)
8. [Endpoints de la API](#endpoints-de-la-api)
9. [Capas de ciberseguridad](#capas-de-ciberseguridad)

---

## Estructura del proyecto

```
Rio/
├── Dockerfile                 # Imagen de produccion multi-stage (sin root)
├── .dockerignore              # Exclusiones del contexto de Docker
├── main.py                    # Punto de entrada de la aplicacion FastAPI
├── requirements.txt           # Dependencias completas (desarrollo + produccion)
├── requirements-prod.txt      # Dependencias exclusivas de produccion (para Docker)
├── pytest.ini                 # Configuracion de pytest
│
├── app/
│   ├── core/
│   │   ├── config.py          # Configuracion centralizada (Pydantic Settings)
│   │   └── seguridad.py       # Middlewares: CORS, rate limiting, cabeceras HTTP
│   ├── models/
│   │   └── tarea.py           # Modelo interno y repositorio en memoria
│   ├── routers/
│   │   └── tareas.py          # Endpoints CRUD REST para el recurso Tarea
│   └── schemas/
│       └── tarea.py           # Esquemas de validacion Pydantic
│
├── frontend/
│   ├── index.html             # Interfaz de usuario
│   ├── styles.css             # Estilos con animacion de rio en CSS puro
│   └── app.js                 # Logica JS con Fetch API
│
└── tests/
    ├── conftest.py            # Fixtures de pytest (aislamiento entre tests)
    └── test_main.py           # 38 tests: CRUD, seguridad, cabeceras, CORS, rate limiting
```

---

## Requisitos previos

| Herramienta | Version minima | Uso |
|---|---|---|
| Python | 3.11 | Runtime de la aplicacion |
| pip | 23+ | Gestion de dependencias Python |
| Docker | 24+ | Contenedorizacion |
| gcloud CLI | Cualquiera reciente | Despliegue en Google Cloud |
| Cuenta de GCP | — | Proyecto activo con billing |

---

## Instalacion y ejecucion en local

### 1. Clonar el repositorio

```bash
git clone https://github.com/alej-developer/riofastapi.git
cd riofastapi
```

### 2. Crear y activar el entorno virtual

```bash
# Crear el entorno virtual en el directorio 'venv'
python -m venv venv

# Activar en Windows (PowerShell)
venv\Scripts\activate

# Activar en Linux o macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (opcional en desarrollo)

```bash
# Copiar el archivo de ejemplo y editarlo segun tus valores locales
# En desarrollo la aplicacion funciona con los valores por defecto
cp .env.example .env
```

### 5. Iniciar el servidor en modo desarrollo

```bash
uvicorn main:app --reload
```

La API estara disponible en:

| URL | Descripcion |
|---|---|
| `http://localhost:8000/` | Endpoint de bienvenida |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/v1/tareas/` | CRUD de tareas |
| `http://localhost:8000/frontend/index.html` | Interfaz web |
| `http://localhost:8000/docs` | Documentacion Swagger UI |
| `http://localhost:8000/redoc` | Documentacion ReDoc |

---

## Ejecucion de los tests

La suite de tests cubre 38 casos: CRUD exitoso, validacion de datos maliciosos (XSS, SQL injection, type confusion, mass assignment), cabeceras de seguridad HTTP, politica CORS y rate limiting.

```bash
# Ejecutar todos los tests con salida detallada
pytest tests/ -v

# Ejecutar solo los tests de ciberseguridad
pytest tests/ -k "seguridad" -v

# Ejecutar solo los tests de CRUD
pytest tests/ -k "Crud" -v

# Ejecutar con reporte de cobertura (requiere pytest-cov)
pip install pytest-cov
pytest tests/ --cov=app --cov-report=term-missing
```

Resultado esperado: `38 passed` sin warnings de Pydantic.

---

## Despliegue con Docker en local

Usar Docker localmente permite verificar que la imagen de produccion funciona correctamente antes de subir a la nube.

### 1. Construir la imagen

```bash
# El flag --no-cache fuerza la reconstruccion completa (util para CI/CD)
docker build --no-cache -t rio-api:local .

# Construccion normal (usa cache de layers para mayor velocidad)
docker build -t rio-api:local .
```

### 2. Verificar que la imagen se creo correctamente

```bash
docker images rio-api
```

### 3. Ejecutar el contenedor localmente

```bash
# -p 8080:8080  Mapea el puerto 8080 del host al 8080 del contenedor
# --rm          Elimina el contenedor automaticamente al detenerlo
# -e PORT=8080  Simula la variable de entorno que inyecta Cloud Run
docker run --rm -p 8080:8080 -e PORT=8080 rio-api:local
```

### 4. Verificar que funciona

```bash
# En otra terminal o en el navegador:
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/tareas/
```

### 5. Detener el contenedor

```bash
# Ctrl+C en la terminal donde corre, o en otra terminal:
docker ps                        # Obtener el ID del contenedor
docker stop <ID_DEL_CONTENEDOR>
```

---

## Despliegue en Google Cloud Run

Google Cloud Run ejecuta contenedores sin necesidad de gestionar servidores. Escala automaticamente a cero cuando no hay trafico y cobra solo por el tiempo de procesamiento real.

### Prerequisitos de GCP

Antes de ejecutar los comandos de despliegue, asegurate de tener:

1. Un proyecto de GCP activo con billing habilitado.
2. Las APIs necesarias activadas en el proyecto.
3. gcloud CLI instalado y autenticado.

### Paso 1: Autenticarse con gcloud

```bash
# Inicia el flujo de autenticacion en el navegador
gcloud auth login

# Configura el proyecto por defecto (sustituye TU_PROYECTO_ID)
gcloud config set project TU_PROYECTO_ID

# Configura la region por defecto
gcloud config set run/region europe-west1
```

### Paso 2: Activar las APIs necesarias

Este comando solo es necesario la primera vez por proyecto.

```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com
```

### Paso 3: Crear el repositorio de contenedores en Artifact Registry

Artifact Registry es el registro privado de Docker de GCP. Es mas seguro y rapido que Docker Hub para imagenes privadas.

```bash
# Crea el repositorio (solo necesario la primera vez)
gcloud artifacts repositories create rio-api-repo \
    --repository-format=docker \
    --location=europe-west1 \
    --description="Repositorio de imagenes para Rio API"

# Configura Docker para autenticarse con Artifact Registry
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

### Paso 4: Construir y subir la imagen a Artifact Registry

```bash
# Define las variables para no repetirlas (sustituye TU_PROYECTO_ID)
export PROYECTO_ID="TU_PROYECTO_ID"
export REGION="europe-west1"
export REPO="rio-api-repo"
export SERVICIO="rio-api"
export IMAGEN="${REGION}-docker.pkg.dev/${PROYECTO_ID}/${REPO}/${SERVICIO}:latest"

# Construye la imagen usando Cloud Build (en la nube, no en tu maquina local)
# Ventaja: no requiere Docker instalado localmente y usa la red de GCP
gcloud builds submit --tag "${IMAGEN}" .

# Alternativa: construir localmente y subir
docker build -t "${IMAGEN}" .
docker push "${IMAGEN}"
```

### Paso 5: Desplegar en Cloud Run

```bash
gcloud run deploy "${SERVICIO}" \
    --image "${IMAGEN}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "ENTORNO=produccion"
```

Descripcion de cada parametro:

| Parametro | Valor | Descripcion |
|---|---|---|
| `--image` | URL de Artifact Registry | Imagen Docker a desplegar |
| `--platform managed` | managed | Cloud Run completamente gestionado (sin Kubernetes) |
| `--region` | europe-west1 | Region de Europa Occidental (baja latencia desde Espana) |
| `--allow-unauthenticated` | — | Permite acceso publico sin token de GCP |
| `--port` | 8080 | Puerto que escucha la aplicacion (coincide con el Dockerfile) |
| `--memory` | 512Mi | Memoria RAM asignada al contenedor |
| `--cpu` | 1 | vCPUs asignadas |
| `--min-instances` | 0 | Escala a cero cuando no hay trafico (ahorro de costes) |
| `--max-instances` | 10 | Limite de instancias para controlar costes en picos |
| `--set-env-vars` | ENTORNO=produccion | Activa HSTS y CSP estricta en produccion |

### Paso 6: Verificar el despliegue

```bash
# Obtiene la URL publica del servicio desplegado
gcloud run services describe "${SERVICIO}" \
    --region "${REGION}" \
    --format "value(status.url)"

# Comprueba el health check del servicio
curl "$(gcloud run services describe ${SERVICIO} --region ${REGION} --format 'value(status.url)')/health"
```

### Paso 7: Ver los logs en tiempo real

```bash
gcloud logging read \
    "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICIO}" \
    --limit 50 \
    --format "value(textPayload)" \
    --freshness 1h
```

### Actualizaciones posteriores

Para desplegar una nueva version de la aplicacion:

```bash
# 1. Construir y subir la nueva imagen (con tag de version recomendado)
export VERSION="v1.1.0"
export IMAGEN_VERSION="${REGION}-docker.pkg.dev/${PROYECTO_ID}/${REPO}/${SERVICIO}:${VERSION}"

gcloud builds submit --tag "${IMAGEN_VERSION}" .

# 2. Desplegar la nueva version (Cloud Run crea una nueva revision automaticamente)
gcloud run deploy "${SERVICIO}" \
    --image "${IMAGEN_VERSION}" \
    --region "${REGION}"

# 3. Cloud Run enruta el 100% del trafico a la nueva revision sin tiempo de inactividad
```

---

## Variables de entorno

| Variable | Por defecto | Descripcion |
|---|---|---|
| `ENTORNO` | `desarrollo` | Modo de ejecucion. En `produccion` activa HSTS y CSP estricta |
| `PORT` | `8000` | Puerto de escucha. Cloud Run inyecta `8080` automaticamente |
| `CLAVE_SECRETA` | Valor de ejemplo | Clave para firmar tokens JWT. Cambiar obligatoriamente en produccion |
| `ALGORITMO_JWT` | `HS256` | Algoritmo de firma de tokens |
| `MINUTOS_EXPIRACION_TOKEN` | `30` | Duracion de los tokens de acceso en minutos |

En Google Cloud Run, las variables sensibles como `CLAVE_SECRETA` deben gestionarse con **Secret Manager**:

```bash
# Crear el secreto en Secret Manager
echo -n "mi-clave-secreta-de-produccion-muy-larga" | \
    gcloud secrets create rio-api-clave-secreta --data-file=-

# Referenciar el secreto en el despliegue de Cloud Run
gcloud run deploy "${SERVICIO}" \
    --image "${IMAGEN}" \
    --region "${REGION}" \
    --set-secrets "CLAVE_SECRETA=rio-api-clave-secreta:latest"
```

---

## Endpoints de la API

### Estado del servidor

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Bienvenida y version de la API |
| GET | `/health` | Health check para orquestadores |

### Tareas (CRUD)

| Metodo | Ruta | Descripcion | Codigo de exito |
|---|---|---|---|
| GET | `/api/v1/tareas/` | Listar todas las tareas | 200 |
| POST | `/api/v1/tareas/` | Crear una nueva tarea | 201 |
| GET | `/api/v1/tareas/{id}` | Obtener una tarea por ID | 200 |
| PUT | `/api/v1/tareas/{id}` | Actualizar una tarea (parcial) | 200 |
| DELETE | `/api/v1/tareas/{id}` | Eliminar una tarea | 204 |

### Documentacion interactiva

| URL | Descripcion |
|---|---|
| `/docs` | Swagger UI: prueba los endpoints desde el navegador |
| `/redoc` | ReDoc: documentacion de referencia |

### Ejemplo de peticion con curl

```bash
# Crear una tarea
curl -X POST http://localhost:8000/api/v1/tareas/ \
    -H "Content-Type: application/json" \
    -d '{"titulo": "Revisar el servidor", "prioridad": "alta"}'

# Listar todas las tareas
curl http://localhost:8000/api/v1/tareas/

# Eliminar una tarea (sustituye 1 por el ID real)
curl -X DELETE http://localhost:8000/api/v1/tareas/1
```

---

## Capas de ciberseguridad

El proyecto implementa seis capas de proteccion independientes:

| Capa | Mecanismo | Ataque prevenido |
|---|---|---|
| Validacion de tipos | Pydantic con tipos estrictos | Type confusion, payloads malformados |
| Sanitizacion de entrada | field_validator en titulos | XSS, SQL Injection |
| Limites de longitud | min_length / max_length | Desbordamiento, DoS por payload |
| CORS restrictivo | Lista blanca de origenes | CSRF via JavaScript desde dominios externos |
| Rate limiting | slowapi por IP (10-60/min) | DDoS, brute-force, spam de datos |
| Cabeceras HTTP | Middleware personalizado (7 cabeceras) | XSS, clickjacking, MIME sniffing, fingerprinting |

---

## Licencia

MIT License
