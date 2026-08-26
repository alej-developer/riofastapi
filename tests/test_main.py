"""
============================================================
tests/test_main.py - Suite de tests de integracion y ciberseguridad
============================================================
Descripcion:
    Este modulo contiene las pruebas automatizadas de la API REST.
    Cubre dos categorias principales:

    CATEGORIA 1 - Tests funcionales (casos de exito CRUD):
        Verifican que los endpoints devuelven las respuestas correctas
        cuando se usan con datos validos y bien formados.

    CATEGORIA 2 - Tests de ciberseguridad:
        Verifican que el sistema rechaza activamente datos peligrosos,
        origenes no autorizados y trafico excesivo. Cada test documenta
        el tipo de ataque que valida.

    PRINCIPIO GENERAL DE PRUEBAS DE SEGURIDAD:
        "No basta con probar que el sistema funciona con datos validos.
        Hay que probar que el sistema FALLA CORRECTAMENTE con datos
        invalidos o maliciosos." — Enfoque de pruebas negativas.

Uso:
    Ejecutar todos los tests:
        pytest tests/

    Ejecutar solo los tests de seguridad:
        pytest tests/ -k "seguridad"

    Ejecutar con reporte de cobertura (requiere pytest-cov):
        pytest tests/ --cov=app --cov-report=term-missing
============================================================
"""

# ------------------------------------------------------------
# Importaciones de pytest y del cliente de prueba
# ------------------------------------------------------------
import pytest                              # Framework de pruebas
from fastapi.testclient import TestClient  # Cliente HTTP sin servidor real
from fastapi import status                 # Codigos HTTP semanticos (200, 201, 404, etc.)


# ============================================================
# ============================================================
# BLOQUE 1: TESTS DE ENDPOINTS DE ESTADO DEL SERVIDOR
# ============================================================
# ============================================================

class TestEstadoServidor:
    """
    Pruebas de los endpoints de verificacion de estado:
    GET / y GET /health.
    """

    def test_endpoint_raiz_responde_200(self, cliente: TestClient) -> None:
        """
        Verifica que el endpoint raiz esta activo y responde HTTP 200.

        POR QUE IMPORTA PARA SEGURIDAD: Un endpoint raiz que falla o
        devuelve stack traces expone informacion interna del servidor
        (rutas, versiones, dependencias). Este test garantiza que la
        respuesta es siempre limpia y controlada.
        """
        respuesta = cliente.get("/")

        assert respuesta.status_code == status.HTTP_200_OK
        datos = respuesta.json()
        assert datos["estado"] == "activo"
        assert "version" in datos
        assert "timestamp" in datos

    def test_endpoint_health_responde_saludable(self, cliente: TestClient) -> None:
        """
        Verifica que el health check devuelve estado 'saludable'.

        POR QUE IMPORTA PARA SEGURIDAD: Un health check mal implementado
        puede revelar informacion sensible del sistema (versiones exactas
        de dependencias vulnerables, estado de la BD). Este test valida
        que solo se expone informacion controlada.
        """
        respuesta = cliente.get("/health")

        assert respuesta.status_code == status.HTTP_200_OK
        datos = respuesta.json()
        assert datos["estado"] == "saludable"


# ============================================================
# ============================================================
# BLOQUE 2: TESTS FUNCIONALES DEL CRUD DE TAREAS (CASOS DE EXITO)
# ============================================================
# ============================================================

class TestCrudTareasExito:
    """
    Pruebas de los cinco endpoints CRUD del recurso Tarea
    con datos validos y bien formados.
    """

    # ----------------------------------------------------------
    # POST /api/v1/tareas — Crear tarea
    # ----------------------------------------------------------

    def test_crear_tarea_devuelve_201(self, cliente: TestClient) -> None:
        """
        Verifica que crear una tarea con datos validos devuelve HTTP 201.

        POR QUE: HTTP 201 Created (no 200 OK) es la respuesta semanticamente
        correcta para una creacion exitosa segun el estandar REST. Un 200
        indicaria que el recurso ya existia, lo que podria confundir a los
        clientes y ocultar errores de logica.
        """
        payload = {
            "titulo": "Revisar informe de seguridad",
            "descripcion": "Analizar el informe mensual de vulnerabilidades.",
            "prioridad": "alta",
        }
        respuesta = cliente.post("/api/v1/tareas/", json=payload)

        assert respuesta.status_code == status.HTTP_201_CREATED

    def test_crear_tarea_devuelve_campos_correctos(self, cliente: TestClient) -> None:
        """
        Verifica que la respuesta de creacion contiene todos los campos
        esperados y que el servidor asigna el ID (no el cliente).

        POR QUE IMPORTA PARA SEGURIDAD: Verificar que 'id' y 'fecha_creacion'
        son generados por el servidor garantiza que el cliente no puede
        manipular estos campos para sobreescribir registros existentes
        o falsificar marcas temporales.
        """
        payload = {"titulo": "Tarea con todos los campos", "prioridad": "media"}
        respuesta = cliente.post("/api/v1/tareas/", json=payload)

        datos = respuesta.json()
        # El servidor debe asignar un ID positivo (no el cliente)
        assert "id" in datos and datos["id"] > 0
        # La fecha de creacion la genera el servidor, no la envia el cliente
        assert "fecha_creacion" in datos
        # Los demas campos deben reflejar los datos enviados
        assert datos["titulo"] == "Tarea con todos los campos"
        assert datos["prioridad"] == "media"
        assert datos["completada"] is False  # Valor por defecto

    def test_crear_tarea_ids_autoincrementales(self, cliente: TestClient) -> None:
        """
        Verifica que cada tarea creada recibe un ID unico y creciente.

        POR QUE IMPORTA PARA SEGURIDAD: Los IDs autoincrementales
        garantizan que el servidor controla la asignacion de identidades.
        Si el cliente pudiera asignar IDs, podria sobreescribir registros
        existentes enviando el mismo ID en una peticion POST.
        """
        id_uno = cliente.post("/api/v1/tareas/", json={"titulo": "Primera"}).json()["id"]
        id_dos = cliente.post("/api/v1/tareas/", json={"titulo": "Segunda"}).json()["id"]
        id_tres = cliente.post("/api/v1/tareas/", json={"titulo": "Tercera"}).json()["id"]

        assert id_uno < id_dos < id_tres  # IDs crecientes y unicos

    # ----------------------------------------------------------
    # GET /api/v1/tareas — Listar tareas
    # ----------------------------------------------------------

    def test_listar_tareas_devuelve_lista_vacia(self, cliente: TestClient) -> None:
        """
        Verifica que listar tareas en un repositorio vacio devuelve
        una lista vacia (no un error 404 ni null).

        POR QUE: Un endpoint que devuelve null o error en lugar de []
        puede causar excepciones no controladas en el cliente,
        potencialmente revelando informacion del sistema.
        """
        respuesta = cliente.get("/api/v1/tareas/")

        assert respuesta.status_code == status.HTTP_200_OK
        assert respuesta.json() == []

    def test_listar_tareas_devuelve_todas(self, cliente_con_tareas: TestClient) -> None:
        """
        Verifica que el endpoint de listado devuelve exactamente
        la cantidad de tareas que se crearon.
        """
        respuesta = cliente_con_tareas.get("/api/v1/tareas/")

        assert respuesta.status_code == status.HTTP_200_OK
        assert len(respuesta.json()) == 3

    # ----------------------------------------------------------
    # GET /api/v1/tareas/{id} — Obtener tarea por ID
    # ----------------------------------------------------------

    def test_obtener_tarea_existente(self, cliente_con_tareas: TestClient) -> None:
        """
        Verifica que se puede recuperar una tarea existente por su ID.
        Comprueba que los datos devueltos son correctos.
        """
        respuesta = cliente_con_tareas.get("/api/v1/tareas/1")

        assert respuesta.status_code == status.HTTP_200_OK
        datos = respuesta.json()
        assert datos["id"] == 1
        assert datos["titulo"] == "Tarea de prueba uno"

    def test_obtener_tarea_inexistente_devuelve_404(self, cliente: TestClient) -> None:
        """
        Verifica que buscar una tarea que no existe devuelve HTTP 404.

        POR QUE IMPORTA PARA SEGURIDAD: Un error 500 en lugar de 404
        indicaria que el sistema no maneja correctamente los recursos
        inexistentes, lo que podria revelar excepciones internas.
        El 404 debe ser generico (no debe indicar si el recurso
        "nunca existio" o "fue eliminado") para evitar enumeration attacks.
        """
        respuesta = cliente.get("/api/v1/tareas/9999")

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        # El mensaje no debe revelar detalles internos del sistema
        assert "stack" not in respuesta.text.lower()
        assert "traceback" not in respuesta.text.lower()

    # ----------------------------------------------------------
    # PUT /api/v1/tareas/{id} — Actualizar tarea
    # ----------------------------------------------------------

    def test_actualizar_tarea_existente(self, cliente_con_tareas: TestClient) -> None:
        """
        Verifica que actualizar una tarea existente modifica correctamente
        los campos enviados y no altera los campos no enviados.

        POR QUE: Una actualizacion parcial (PATCH semantica via PUT) que
        borre campos no enviados podria causar perdida involuntaria de datos.
        """
        payload_actualizacion = {"completada": True, "prioridad": "baja"}
        respuesta = cliente_con_tareas.put("/api/v1/tareas/1", json=payload_actualizacion)

        assert respuesta.status_code == status.HTTP_200_OK
        datos = respuesta.json()
        assert datos["completada"] is True
        assert datos["prioridad"] == "baja"
        # El titulo no fue enviado, no debe haber sido modificado
        assert datos["titulo"] == "Tarea de prueba uno"

    def test_actualizar_tarea_inexistente_devuelve_404(self, cliente: TestClient) -> None:
        """
        Verifica que intentar actualizar una tarea inexistente devuelve 404.
        """
        respuesta = cliente.put("/api/v1/tareas/9999", json={"titulo": "Nuevo titulo"})

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND

    # ----------------------------------------------------------
    # DELETE /api/v1/tareas/{id} — Eliminar tarea
    # ----------------------------------------------------------

    def test_eliminar_tarea_existente_devuelve_204(self, cliente_con_tareas: TestClient) -> None:
        """
        Verifica que eliminar una tarea devuelve HTTP 204 No Content.

        POR QUE: HTTP 204 es el codigo correcto para un DELETE exitoso
        segun el estandar REST. No debe incluir cuerpo en la respuesta,
        lo que garantiza que no se filtra informacion del registro eliminado.
        """
        respuesta = cliente_con_tareas.delete("/api/v1/tareas/1")

        assert respuesta.status_code == status.HTTP_204_NO_CONTENT
        # HTTP 204 no debe tener cuerpo de respuesta
        assert respuesta.content == b""

    def test_eliminar_tarea_la_elimina_del_repositorio(self, cliente_con_tareas: TestClient) -> None:
        """
        Verifica que tras eliminar una tarea, esta ya no existe en el sistema.
        Un GET al mismo ID debe devolver 404.

        POR QUE: Confirmar la eliminacion real previene condiciones de carrera
        donde un registro "eliminado" sigue siendo accesible, lo que podria
        ser explotado para acceder a datos que deberian estar borrados.
        """
        cliente_con_tareas.delete("/api/v1/tareas/2")
        respuesta_get = cliente_con_tareas.get("/api/v1/tareas/2")

        assert respuesta_get.status_code == status.HTTP_404_NOT_FOUND

    def test_eliminar_tarea_inexistente_devuelve_404(self, cliente: TestClient) -> None:
        """
        Verifica que intentar eliminar una tarea inexistente devuelve 404.
        """
        respuesta = cliente.delete("/api/v1/tareas/9999")

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND


# ============================================================
# ============================================================
# BLOQUE 3: TESTS DE CIBERSEGURIDAD
# ============================================================
# ============================================================

class TestCiberseguridadValidacionDatos:
    """
    CATEGORIA: Validacion de datos de entrada / Prevencion de inyeccion.

    Estos tests verifican que el sistema rechaza activamente datos
    maliciosos, malformados o que intentan explotar vulnerabilidades
    conocidas antes de que lleguen a la logica de negocio.

    PRINCIPIO: La validacion de entrada es la defensa mas efectiva
    contra inyeccion de codigo (XSS, SQL Injection, Command Injection).
    """

    def test_seguridad_rechaza_titulo_con_etiqueta_xss(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Cross-Site Scripting (XSS)

        Un atacante podria intentar inyectar codigo JavaScript en el
        titulo de una tarea con la esperanza de que sea renderizado
        y ejecutado por un cliente web (navegador). Por ejemplo:
            <script>document.cookie='session=robada'</script>

        El validador de Pydantic en TareaCrear debe rechazar cualquier
        titulo que contenga el caracter '<' o '>' con HTTP 422.
        """
        payload_xss = {
            "titulo": "<script>alert('XSS')</script>",
            "prioridad": "media",
        }
        respuesta = cliente.post("/api/v1/tareas/", json=payload_xss)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
            "El sistema debe rechazar titulos con etiquetas HTML/JS (prevencion XSS)"
        )

    def test_seguridad_rechaza_titulo_con_comillas_sql(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: SQL Injection

        Un atacante podria intentar cerrar una consulta SQL e inyectar
        sus propios comandos mediante el uso de comillas simples o
        secuencias como '--' (comentario SQL). Por ejemplo:
            ' OR '1'='1'--

        Aunque la implementacion actual usa un repositorio en memoria
        (sin SQL), la validacion se aplica por si en el futuro se
        integra una base de datos SQL real.
        """
        payload_sql = {
            "titulo": "'; DROP TABLE tareas; --",
            "prioridad": "baja",
        }
        respuesta = cliente.post("/api/v1/tareas/", json=payload_sql)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
            "El sistema debe rechazar titulos con secuencias de inyeccion SQL"
        )

    def test_seguridad_rechaza_titulo_vacio(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Denegacion de servicio por datos invalidos / Bypass de logica.

        Un titulo vacio podria:
        1. Causar errores en interfaces que asuman que el titulo existe.
        2. Ser usado para crear registros "fantasma" dificiles de identificar.

        La restriccion min_length=1 en el schema garantiza que todo registro
        tenga un identificador legible.
        """
        payload_vacio = {"titulo": "", "prioridad": "media"}
        respuesta = cliente.post("/api/v1/tareas/", json=payload_vacio)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_seguridad_rechaza_titulo_demasiado_largo(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Desbordamiento de buffer / Consumo de recursos.

        Un atacante podria enviar un campo de texto extremadamente largo
        para consumir memoria del servidor, provocar errores de base de
        datos o explotar vulnerabilidades de desbordamiento.

        El campo 'titulo' tiene max_length=100 caracteres.
        """
        payload_largo = {"titulo": "A" * 101, "prioridad": "media"}
        respuesta = cliente.post("/api/v1/tareas/", json=payload_largo)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
            "El sistema debe rechazar titulos que superen los 100 caracteres"
        )

    def test_seguridad_rechaza_descripcion_demasiado_larga(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Consumo de recursos del servidor (DoS por payload).

        La descripcion tiene un limite de 500 caracteres para prevenir
        que un atacante envie payloads masivos que consuman memoria
        o causen timeouts en el procesamiento.
        """
        payload_largo = {
            "titulo": "Titulo valido",
            "descripcion": "B" * 501,
            "prioridad": "baja",
        }
        respuesta = cliente.post("/api/v1/tareas/", json=payload_largo)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_seguridad_rechaza_prioridad_invalida(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Inyeccion de valores de enumeracion invalidos.

        El campo 'prioridad' esta restringido a un Enum de tres valores.
        Un atacante podria enviar valores arbitrarios para:
        1. Provocar comportamiento inesperado en logica que dependa del valor.
        2. Intentar inyectar valores que desencadenen errores internos.

        El Enum de Pydantic garantiza que solo 'baja', 'media' o 'alta' son validos.
        """
        payload_invalido = {"titulo": "Tarea con prioridad inventada", "prioridad": "CRITICA_URGENTE"}
        respuesta = cliente.post("/api/v1/tareas/", json=payload_invalido)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_seguridad_rechaza_tipo_incorrecto_en_completada(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Type confusion / Manipulacion de tipos.

        Un atacante podria enviar un tipo de dato inesperado en el campo
        'completada' (que debe ser boolean) para intentar manipular la
        logica del servidor. Por ejemplo, enviar un objeto o lista podria
        causar excepciones no controladas si no se validan los tipos.

        Pydantic rechaza cualquier valor que no sea convertible a bool.
        """
        payload_tipo_incorrecto = {
            "titulo": "Tarea valida",
            "completada": {"inyeccion": "de objeto"},  # Debe ser bool, no dict
        }
        respuesta = cliente.post("/api/v1/tareas/", json=payload_tipo_incorrecto)

        assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_seguridad_rechaza_id_negativo_en_ruta(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Manipulacion de identificadores de recursos.

        Un atacante podria enviar IDs negativos, cero o extremadamente
        grandes para intentar acceder a registros no previstos, causar
        desbordamientos en la logica de busqueda o explotar comportamientos
        fuera de los limites.

        El validador Path(ge=1) rechaza cualquier ID que no sea >= 1.
        """
        for id_invalido in ["/api/v1/tareas/0", "/api/v1/tareas/-1", "/api/v1/tareas/-999"]:
            respuesta = cliente.get(id_invalido)
            assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
                f"El ID '{id_invalido}' deberia ser rechazado como no valido"
            )

    def test_seguridad_rechaza_id_no_entero_en_ruta(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Inyeccion mediante parametros de ruta no esperados.

        Un atacante podria enviar strings en lugar de enteros en la ruta
        con la esperanza de causar errores de parseo o comportamiento
        inesperado en la logica de consulta.
        Por ejemplo: GET /tareas/admin, /tareas/null, /tareas/../../etc/passwd
        """
        for id_invalido in ["/api/v1/tareas/abc", "/api/v1/tareas/null", "/api/v1/tareas/1.5"]:
            respuesta = cliente.get(id_invalido)
            assert respuesta.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
                f"El ID '{id_invalido}' deberia ser rechazado como no entero"
            )

    def test_seguridad_rechaza_campos_extra_no_declarados(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Mass Assignment / Parameter Pollution.

        Un atacante podria intentar enviar campos no declarados en el
        schema (como 'id', 'fecha_creacion', 'rol_admin') esperando que
        el servidor los acepte y los procese (Mass Assignment Vulnerability).

        Pydantic ignora por defecto los campos extra, pero este test
        verifica que la peticion se procesa correctamente y que los
        campos inyectados son silenciados (no causan un error 500
        que revele informacion del sistema).
        """
        payload_con_campos_extra = {
            "titulo": "Tarea normal",
            "prioridad": "media",
            "id": 999,                  # Intento de forzar un ID especifico
            "fecha_creacion": "2000-01-01T00:00:00",  # Intento de falsificar fecha
            "rol_admin": True,          # Campo inventado que no existe en el schema
        }
        respuesta = cliente.post("/api/v1/tareas/", json=payload_con_campos_extra)

        # La peticion debe completarse exitosamente (los campos extra se ignoran)
        assert respuesta.status_code == status.HTTP_201_CREATED
        datos = respuesta.json()
        # El ID asignado NO debe ser el 999 enviado por el atacante
        assert datos["id"] != 999, "El servidor nunca debe aceptar IDs propuestos por el cliente"
        # La fecha tampoco debe ser la enviada por el cliente
        assert "2000-01-01" not in datos["fecha_creacion"]


class TestCiberseguridadCabeceras:
    """
    CATEGORIA: Cabeceras de seguridad HTTP.

    Estos tests verifican que el middleware CabecerasSeguridad
    inyecta correctamente las cabeceras protectoras en TODAS
    las respuestas de la API.
    """

    def test_seguridad_cabecera_x_content_type_options(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: MIME-Type Sniffing.

        Verifica que la cabecera 'X-Content-Type-Options: nosniff' esta
        presente en la respuesta. Sin ella, los navegadores podrian
        intentar adivinar el tipo MIME del contenido y ejecutar archivos
        disfrazados de texto como si fueran JavaScript.
        """
        respuesta = cliente.get("/")

        assert "x-content-type-options" in respuesta.headers
        assert respuesta.headers["x-content-type-options"] == "nosniff"

    def test_seguridad_cabecera_x_frame_options(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Clickjacking.

        Verifica que la cabecera 'X-Frame-Options: DENY' impide que la
        aplicacion sea incrustada en iframes de paginas de terceros.
        Un iframe invisible puede usarse para engañar al usuario para
        que interactue con la API sin saberlo.
        """
        respuesta = cliente.get("/")

        assert "x-frame-options" in respuesta.headers
        assert respuesta.headers["x-frame-options"] == "DENY"

    def test_seguridad_cabecera_x_xss_protection(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Cross-Site Scripting (XSS) en navegadores legacy.

        Verifica que la cabecera 'X-XSS-Protection: 1; mode=block' activa
        el filtro XSS de navegadores antiguos. En caso de detectar un
        ataque XSS reflejado, el navegador bloquea la carga de la pagina.
        """
        respuesta = cliente.get("/")

        assert "x-xss-protection" in respuesta.headers
        assert respuesta.headers["x-xss-protection"] == "1; mode=block"

    def test_seguridad_cabecera_referrer_policy(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Fuga de informacion via cabecera Referer.

        Verifica que la politica de referrer evita que URLs internas
        (con posibles tokens o rutas sensibles) sean enviadas a sitios
        de terceros cuando el usuario navega desde la API.
        """
        respuesta = cliente.get("/")

        assert "referrer-policy" in respuesta.headers
        assert respuesta.headers["referrer-policy"] == "strict-origin-when-cross-origin"

    def test_seguridad_cabecera_permissions_policy(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Abuso de APIs del navegador tras un XSS exitoso.

        Verifica que la cabecera Permissions-Policy deshabilita el acceso
        a APIs sensibles del navegador (camara, microfono, geolocalizacion).
        Aunque un atacante ejecute codigo JavaScript mediante XSS, no podra
        acceder a estos recursos si la cabecera los deshabilita explicitamente.
        """
        respuesta = cliente.get("/")

        assert "permissions-policy" in respuesta.headers
        cabecera = respuesta.headers["permissions-policy"]
        assert "camera=()" in cabecera
        assert "microphone=()" in cabecera
        assert "geolocation=()" in cabecera

    def test_seguridad_cabecera_content_security_policy(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: XSS avanzado e inyeccion de contenido.

        Verifica que la Content-Security-Policy (CSP) esta configurada
        y contiene la directiva frame-ancestors para bloquear iframes.
        CSP es la defensa mas robusta contra XSS en navegadores modernos.
        """
        respuesta = cliente.get("/")

        assert "content-security-policy" in respuesta.headers
        csp = respuesta.headers["content-security-policy"]
        # La directiva frame-ancestors debe estar presente (equivale a X-Frame-Options en modernos)
        assert "frame-ancestors 'none'" in csp

    def test_seguridad_cabecera_server_eliminada(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Fingerprinting del servidor (Information Disclosure).

        Verifica que la cabecera 'server' ha sido eliminada de la respuesta.
        Sin esta cabecera, un atacante no puede identificar facilmente el
        servidor web utilizado (uvicorn, nginx, etc.) ni su version,
        dificultando la busqueda de exploits especificos.
        """
        respuesta = cliente.get("/")

        # La cabecera 'server' no debe estar presente
        assert "server" not in respuesta.headers, (
            "La cabecera 'server' no debe exponerse para evitar fingerprinting"
        )

    def test_seguridad_cabeceras_presentes_en_respuestas_de_error(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: Bypass de cabeceras de seguridad mediante rutas de error.

        Un atacante podria intentar provocar errores (404, 422) para obtener
        respuestas sin las cabeceras de seguridad, aprovechando que algunos
        frameworks las aplican solo a respuestas exitosas. Este test
        verifica que las cabeceras de seguridad estan presentes INCLUSO en
        respuestas de error.
        """
        respuesta = cliente.get("/api/v1/tareas/9999")  # Provoca un 404

        assert respuesta.status_code == status.HTTP_404_NOT_FOUND
        # Las cabeceras de seguridad deben estar presentes en errores tambien
        assert "x-content-type-options" in respuesta.headers
        assert "x-frame-options" in respuesta.headers


class TestCiberseguridadCORS:
    """
    CATEGORIA: Politica de CORS (Cross-Origin Resource Sharing).

    Estos tests verifican que la configuracion CORS es restrictiva:
    solo los origenes autorizados reciben las cabeceras que permiten
    peticiones cross-origin desde el navegador.

    NOTA IMPORTANTE: CORS es un mecanismo del NAVEGADOR, no del servidor.
    El servidor responde a todas las peticiones, pero solo incluye la
    cabecera Access-Control-Allow-Origin para origenes autorizados.
    Un navegador que no recibe esa cabecera bloquea la respuesta.
    Las peticiones directas (curl, Postman) no estan sujetas a CORS.
    """

    def test_cors_origen_autorizado_recibe_cabecera(self, cliente: TestClient) -> None:
        """
        VERIFICACION: Los origenes autorizados reciben la cabecera CORS.

        Verifica que una peticion desde un origen de la lista blanca
        (localhost:3000) recibe la cabecera Access-Control-Allow-Origin,
        lo que permite al navegador mostrar la respuesta al codigo JS.
        """
        respuesta = cliente.get(
            "/",
            headers={"Origin": "http://localhost:3000"},  # Origen autorizado
        )

        assert respuesta.status_code == status.HTTP_200_OK
        # El origen autorizado debe aparecer en la cabecera de respuesta
        assert "access-control-allow-origin" in respuesta.headers
        assert respuesta.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_cors_origen_no_autorizado_no_recibe_cabecera(self, cliente: TestClient) -> None:
        """
        ATAQUE PREVENIDO: CSRF via JavaScript desde dominios maliciosos.

        Verifica que una peticion desde un origen no autorizado NO recibe
        la cabecera Access-Control-Allow-Origin. El navegador del usuario
        bloqueara la respuesta, impidiendo que el codigo malicioso
        (ejecutandose en el dominio del atacante) acceda a los datos
        de la API en nombre del usuario autenticado.
        """
        respuesta = cliente.get(
            "/",
            headers={"Origin": "http://sitio-malicioso.com"},  # Origen NO autorizado
        )

        # La peticion llega al servidor (CORS no bloquea en el servidor)
        assert respuesta.status_code == status.HTTP_200_OK
        # Pero la cabecera CORS no se incluye para origenes no autorizados
        cabecera_cors = respuesta.headers.get("access-control-allow-origin", "")
        assert "sitio-malicioso.com" not in cabecera_cors, (
            "Un origen no autorizado no debe recibir la cabecera CORS. "
            "El navegador bloqueara la respuesta en el cliente."
        )

    def test_cors_preflight_origen_autorizado(self, cliente: TestClient) -> None:
        """
        VERIFICACION: Peticion preflight OPTIONS para origen autorizado.

        Los navegadores envian una peticion OPTIONS (preflight) antes de
        peticiones cross-origin no simples (con cabeceras custom o metodos
        no GET/POST). Verifica que el servidor responde correctamente
        al preflight de un origen autorizado.
        """
        respuesta = cliente.options(
            "/api/v1/tareas/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )

        # El preflight debe responder con 200 o 204 para origenes autorizados
        assert respuesta.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)


class TestCiberseguridadRateLimiting:
    """
    CATEGORIA: Control de tasa de peticiones (Rate Limiting).

    Estos tests verifican que el sistema aplica limites de peticiones
    para prevenir ataques de fuerza bruta, DDoS y abuso de la API.

    NOTA: Los limites globales son 200/dia y 50/hora. Los limites
    por endpoint son mas estrictos (10-60/minuto segun el endpoint).
    En el entorno de test, se verifica el comportamiento con el
    endpoint de creacion (limite: 10/minuto).
    """

    def test_rate_limiting_acepta_peticiones_dentro_del_limite(
        self, cliente: TestClient
    ) -> None:
        """
        VERIFICACION: Peticiones dentro del limite son aceptadas.

        Verifica que el sistema no bloquea peticiones legitimas
        que estan dentro del umbral configurado. Un rate limiter
        mal configurado podria denegar trafico legitimo.
        """
        # Se realizan 5 peticiones de lectura (GET), bien por debajo del limite
        for _ in range(5):
            respuesta = cliente.get("/api/v1/tareas/")
            assert respuesta.status_code == status.HTTP_200_OK, (
                "Las peticiones dentro del limite no deben ser bloqueadas"
            )

    def test_rate_limiting_endpoint_post_bloquea_tras_exceder_limite(
        self, cliente: TestClient
    ) -> None:
        """
        ATAQUE PREVENIDO: Spam de creacion / Abuso de escritura.

        Verifica que el rate limiting bloquea con HTTP 429 (Too Many
        Requests) cuando se supera el limite de peticiones POST.

        El endpoint POST /tareas tiene un limite de 10 peticiones/minuto.
        Se envian 11 peticiones y se verifica que al menos la ultima es
        rechazada con HTTP 429.

        ATAQUES QUE PREVIENE:
        - Creacion masiva de registros para saturar el almacenamiento.
        - Ataques de fuerza bruta si se usara para autenticacion.
        - Spam de datos para contaminar la base de datos.
        """
        codigos_respuesta = []

        # Se envian 11 peticiones (una mas que el limite de 10/minuto)
        for i in range(11):
            respuesta = cliente.post(
                "/api/v1/tareas/",
                json={"titulo": f"Tarea numero {i + 1}", "prioridad": "baja"},
            )
            codigos_respuesta.append(respuesta.status_code)

        # Al menos una peticion debe haber sido bloqueada con HTTP 429
        assert status.HTTP_429_TOO_MANY_REQUESTS in codigos_respuesta, (
            "El rate limiter debe devolver HTTP 429 tras superar el limite de "
            "10 peticiones POST por minuto"
        )

    def test_rate_limiting_respuesta_429_no_revela_detalles_internos(
        self, cliente: TestClient
    ) -> None:
        """
        ATAQUE PREVENIDO: Information Disclosure en respuestas de error de rate limiting.

        Cuando el rate limiter bloquea una peticion, la respuesta de error
        no debe revelar detalles internos del sistema (configuracion interna,
        limites exactos implementados, IP del servidor, etc.).
        """
        # Se superan el limite del endpoint POST
        codigos = []
        for i in range(11):
            r = cliente.post(
                "/api/v1/tareas/",
                json={"titulo": f"T{i}", "prioridad": "baja"},
            )
            codigos.append(r.status_code)
            if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Se verifica que la respuesta 429 no contiene informacion sensible
                cuerpo = r.text.lower()
                assert "traceback" not in cuerpo
                assert "exception" not in cuerpo
                assert "internal" not in cuerpo
                break
