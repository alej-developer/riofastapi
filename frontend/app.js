/**
 * ============================================================
 * app.js — Logica principal del frontend de Rio API
 * ============================================================
 * Descripcion:
 *   Conecta la interfaz HTML con la API FastAPI mediante la
 *   Fetch API nativa del navegador. Implementa las cinco
 *   operaciones CRUD del recurso Tarea:
 *     - Listar todas las tareas (GET /api/v1/tareas/)
 *     - Crear una nueva tarea   (POST /api/v1/tareas/)
 *     - Actualizar una tarea   (PUT /api/v1/tareas/{id})
 *     - Marcar como completada (PUT /api/v1/tareas/{id})
 *     - Eliminar una tarea     (DELETE /api/v1/tareas/{id})
 *
 * Arquitectura:
 *   - api.*:      Capa de acceso a datos (todas las llamadas HTTP).
 *   - ui.*:       Capa de presentacion (renderizado y DOM).
 *   - eventos.*:  Capa de controladores (listeners y coordinacion).
 *   - init():     Punto de entrada que arranca la aplicacion.
 *
 * Manejo de errores:
 *   Todos los errores de red y de la API se capturan y se muestran
 *   al usuario mediante notificaciones toast no intrusivas, sin
 *   lanzar excepciones no controladas a la consola.
 * ============================================================
 */

'use strict';  /* Modo estricto: previene errores silenciosos de JavaScript */


/* ============================================================
   CONFIGURACION GLOBAL
   ============================================================ */

/**
 * URL base de la API. Como el frontend se sirve desde el mismo
 * servidor (FastAPI con StaticFiles), se usa una URL relativa.
 * Esto elimina cualquier problema de CORS automaticamente.
 */
const URL_API = '/api/v1';

/**
 * Duracion en milisegundos de las notificaciones toast antes de desaparecer.
 */
const DURACION_TOAST = 3000;


/* ============================================================
   CAPA API — Todas las llamadas HTTP a la API REST
   ============================================================ */
const api = {

    /**
     * Funcion privada auxiliar: realiza cualquier llamada HTTP a la API.
     *
     * Por que existe esta funcion:
     *   Centraliza la logica comun de todas las peticiones (cabeceras,
     *   manejo de errores HTTP, conversion de JSON). Evitar duplicar
     *   esta logica en cada metodo CRUD reduce bugs y facilita cambios.
     *
     * @param {string} ruta     - Ruta relativa al URL_API (ej: '/tareas/')
     * @param {Object} opciones - Opciones de fetch (method, body, etc.)
     * @returns {Promise<any>}  - Los datos JSON de la respuesta, o null para 204.
     * @throws {Error}          - Si la respuesta HTTP no es exitosa (4xx, 5xx).
     */
    async _peticion(ruta, opciones = {}) {
        /* Se construye la URL completa combinando la base con la ruta del endpoint */
        const url = `${URL_API}${ruta}`;

        /* Cabeceras por defecto: siempre enviamos y esperamos JSON */
        const cabeceraPorDefecto = { 'Content-Type': 'application/json' };

        /* Se fusionan las opciones del llamante con las cabeceras por defecto */
        const configuracion = {
            ...opciones,
            headers: {
                ...cabeceraPorDefecto,
                ...(opciones.headers || {}),
            },
        };

        let respuesta;
        try {
            /* Realiza la peticion HTTP con Fetch API */
            respuesta = await fetch(url, configuracion);
        } catch (errorRed) {
            /*
             * Este bloque catch captura errores de RED (no errores HTTP).
             * Ocurre cuando el servidor esta caido, sin internet, o CORS
             * bloquea la peticion a nivel del navegador.
             * Se relanza con un mensaje legible para el usuario.
             */
            throw new Error('No se pudo conectar con el servidor. Comprueba que la API este activa.');
        }

        /*
         * Respuesta HTTP 204 No Content (DELETE exitoso):
         * No tiene cuerpo, por lo que intentar parsear JSON causaria un error.
         * Se retorna null para indicar exito sin datos.
         */
        if (respuesta.status === 204) {
            return null;
        }

        /* Se intenta parsear el cuerpo como JSON independientemente del status */
        let datos;
        try {
            datos = await respuesta.json();
        } catch {
            /* Si el cuerpo no es JSON valido (respuesta vacia inesperada), se ignora */
            datos = null;
        }

        /* Si la respuesta HTTP no es exitosa (4xx o 5xx), se lanza un error */
        if (!respuesta.ok) {
            /*
             * La API devuelve errores en el campo "detail" segun el estandar FastAPI.
             * Se extrae ese mensaje para mostrarlo al usuario.
             */
            const mensajeError = datos?.detail || `Error ${respuesta.status}: ${respuesta.statusText}`;
            throw new Error(mensajeError);
        }

        return datos;
    },

    /**
     * Obtiene la lista completa de tareas de la API.
     * Corresponde a: GET /api/v1/tareas/
     *
     * @returns {Promise<Array>} - Array de objetos tarea.
     */
    async listarTareas() {
        return this._peticion('/tareas/');
    },

    /**
     * Crea una nueva tarea enviando los datos validados.
     * Corresponde a: POST /api/v1/tareas/
     *
     * @param {Object} datos - { titulo, descripcion, prioridad, completada }
     * @returns {Promise<Object>} - La tarea creada con su ID asignado por el servidor.
     */
    async crearTarea(datos) {
        return this._peticion('/tareas/', {
            method: 'POST',
            /* JSON.stringify serializa el objeto JS a texto JSON para el cuerpo */
            body: JSON.stringify(datos),
        });
    },

    /**
     * Actualiza los campos de una tarea existente (actualizacion parcial).
     * Corresponde a: PUT /api/v1/tareas/{id}
     *
     * @param {number} id       - Identificador de la tarea a actualizar.
     * @param {Object} cambios  - Campos a modificar (solo los que cambian).
     * @returns {Promise<Object>} - La tarea con los cambios aplicados.
     */
    async actualizarTarea(id, cambios) {
        return this._peticion(`/tareas/${id}`, {
            method: 'PUT',
            body: JSON.stringify(cambios),
        });
    },

    /**
     * Elimina permanentemente una tarea.
     * Corresponde a: DELETE /api/v1/tareas/{id}
     *
     * @param {number} id - Identificador de la tarea a eliminar.
     * @returns {Promise<null>} - null en caso de exito (HTTP 204).
     */
    async eliminarTarea(id) {
        return this._peticion(`/tareas/${id}`, { method: 'DELETE' });
    },

    /**
     * Verifica el estado de salud de la API.
     * Corresponde a: GET /health
     * Se usa al arrancar la app para actualizar el indicador de conexion.
     *
     * @returns {Promise<Object>} - { estado: 'saludable', ... }
     */
    async verificarSalud() {
        /* Llama directamente a /health (fuera del prefijo /api/v1) */
        const respuesta = await fetch('/health');
        if (!respuesta.ok) throw new Error('API no disponible');
        return respuesta.json();
    },
};


/* ============================================================
   CAPA UI — Renderizado y manipulacion del DOM
   ============================================================ */
const ui = {

    /* Referencias en cache a los elementos DOM de uso frecuente.
     * Al cachearlas al inicio, se evitan multiples querySelector()
     * que son costosos si se llaman en bucles o eventos frecuentes. */
    elementos: {
        listaContenedor:  () => document.getElementById('lista-tareas'),
        estadoCargando:   () => document.getElementById('cargando'),
        estadoVacio:      () => document.getElementById('lista-vacia'),
        formularioCrear:  () => document.getElementById('formulario-crear'),
        formularioEditar: () => document.getElementById('formulario-editar'),
        modalFondo:       () => document.getElementById('modal-fondo'),
        zonaToast:        () => document.getElementById('zona-toast'),
        estadoPunto:      () => document.getElementById('estado-punto'),
        estadoTexto:      () => document.getElementById('estado-texto'),
        contadorTitulo:   () => document.getElementById('contador-titulo'),
        contadorDesc:     () => document.getElementById('contador-descripcion'),
    },

    /**
     * Actualiza el indicador de estado de conexion en la cabecera.
     *
     * @param {'conectando'|'activo'|'error'} estado - Estado de la conexion.
     */
    actualizarEstadoConexion(estado) {
        const punto = this.elementos.estadoPunto();
        const texto = this.elementos.estadoTexto();

        /* Se eliminan todas las clases de estado anteriores */
        punto.classList.remove('conectado', 'error');

        /* Se aplica la clase y el texto correspondiente al nuevo estado */
        const configuraciones = {
            conectando: { clase: '',        label: 'Conectando...' },
            activo:     { clase: 'conectado', label: 'API activa' },
            error:      { clase: 'error',    label: 'Sin conexion' },
        };

        const config = configuraciones[estado] || configuraciones.conectando;
        if (config.clase) punto.classList.add(config.clase);
        texto.textContent = config.label;
    },

    /**
     * Muestra el estado de carga de la lista (spinner, vacio, o nada).
     *
     * @param {'cargando'|'vacio'|'oculto'} estado
     */
    mostrarEstadoLista(estado) {
        const cargando = this.elementos.estadoCargando();
        const vacio    = this.elementos.estadoVacio();

        /* Ambos ocultos por defecto */
        cargando.hidden = true;
        vacio.hidden    = true;

        if (estado === 'cargando') cargando.hidden = false;
        if (estado === 'vacio')    vacio.hidden    = false;
    },

    /**
     * Renderiza la lista completa de tareas en el DOM.
     * Borra el contenido anterior y vuelve a generarlo.
     *
     * @param {Array} tareas - Array de objetos tarea de la API.
     */
    renderizarTareas(tareas) {
        const lista = this.elementos.listaContenedor();

        /* Si no hay tareas, se muestra el estado vacio */
        if (!tareas || tareas.length === 0) {
            lista.innerHTML = '';
            this.mostrarEstadoLista('vacio');
            return;
        }

        /* Hay tareas: se oculta el estado vacio y se renderizan las tarjetas */
        this.mostrarEstadoLista('oculto');

        /*
         * Se usa DocumentFragment para construir todos los elementos en memoria
         * y hacer un unico insert en el DOM real, minimizando los reflows
         * del navegador (optimizacion de rendimiento).
         */
        const fragmento = document.createDocumentFragment();
        tareas.forEach(tarea => {
            fragmento.appendChild(this.crearElementoTarea(tarea));
        });

        /* Se reemplaza el contenido en un solo paso */
        lista.innerHTML = '';
        lista.appendChild(fragmento);
    },

    /**
     * Crea el elemento <li> de una tarea individual.
     * Construye la tarjeta con todos sus campos y botones de accion.
     *
     * @param {Object} tarea - Objeto tarea de la API.
     * @returns {HTMLElement} - El elemento <li> completo.
     */
    crearElementoTarea(tarea) {
        const li = document.createElement('li');
        li.className = `tarea-item ${tarea.completada ? 'completada' : ''}`;
        li.dataset.id = tarea.id;  /* Se almacena el ID para acceso rapido en handlers */

        /* Fecha formateada en locale espanol para mejor legibilidad */
        const fechaFormateada = new Date(tarea.fecha_creacion).toLocaleDateString('es-ES', {
            day: '2-digit', month: 'short', year: 'numeric'
        });

        /*
         * Se usa innerHTML con datos escapados de la API.
         * NOTA DE SEGURIDAD: Los datos vienen de nuestra propia API que ya
         * aplico validacion y sanitizacion de XSS. Para mayor seguridad en
         * produccion se deberia usar textContent para insertar texto del usuario.
         */
        li.innerHTML = `
            <input
                type="checkbox"
                class="tarea-checkbox"
                ${tarea.completada ? 'checked' : ''}
                aria-label="Marcar '${this._escaparHTML(tarea.titulo)}' como ${tarea.completada ? 'pendiente' : 'completada'}"
            />
            <div class="tarea-contenido">
                <p class="tarea-titulo">${this._escaparHTML(tarea.titulo)}</p>
                ${tarea.descripcion
                    ? `<p class="tarea-descripcion">${this._escaparHTML(tarea.descripcion)}</p>`
                    : ''}
                <div class="tarea-meta">
                    <span class="tarea-prioridad prioridad-${tarea.prioridad}">${tarea.prioridad}</span>
                    <span class="tarea-id">#${tarea.id} &middot; ${fechaFormateada}</span>
                </div>
            </div>
            <div class="tarea-acciones">
                <button class="boton boton-secundario btn-editar" style="padding:4px 10px;font-size:0.8125rem;" aria-label="Editar tarea">
                    Editar
                </button>
                <button class="boton boton-peligro btn-eliminar" aria-label="Eliminar tarea">
                    Eliminar
                </button>
            </div>
        `;

        return li;
    },

    /**
     * Escapa caracteres HTML especiales para prevenir XSS al insertar
     * texto de usuarios en el DOM mediante innerHTML.
     *
     * @param {string} texto - Texto a escapar.
     * @returns {string} - Texto seguro para insertar en HTML.
     */
    _escaparHTML(texto) {
        const mapa = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        return String(texto).replace(/[&<>"']/g, char => mapa[char]);
    },

    /**
     * Abre el modal de edicion con los datos actuales de una tarea.
     *
     * @param {Object} tarea - Objeto tarea a editar.
     */
    abrirModalEdicion(tarea) {
        /* Se rellenan los campos del formulario de edicion con los datos actuales */
        document.getElementById('editar-id').value          = tarea.id;
        document.getElementById('editar-titulo').value      = tarea.titulo;
        document.getElementById('editar-descripcion').value = tarea.descripcion || '';
        document.getElementById('editar-prioridad').value   = tarea.prioridad;
        document.getElementById('editar-completada').checked = tarea.completada;

        /* Se hace visible el modal quitando el atributo hidden */
        this.elementos.modalFondo().hidden = false;

        /* Se enfoca el primer campo para accesibilidad de teclado */
        document.getElementById('editar-titulo').focus();
    },

    /**
     * Cierra el modal de edicion.
     */
    cerrarModalEdicion() {
        this.elementos.modalFondo().hidden = true;
    },

    /**
     * Muestra una notificacion toast temporal al usuario.
     *
     * @param {string} mensaje   - Texto a mostrar.
     * @param {number} duracion  - Duracion en ms antes de desaparecer.
     */
    mostrarToast(mensaje, duracion = DURACION_TOAST) {
        const zona  = this.elementos.zonaToast();
        const toast = document.createElement('div');
        toast.className   = 'toast';
        toast.textContent = mensaje;
        toast.setAttribute('role', 'status');

        zona.appendChild(toast);

        /*
         * Despues de la duracion configurada, se añade la clase 'saliendo'
         * que dispara la animacion de salida CSS. Una vez termina la animacion,
         * se elimina el elemento del DOM.
         */
        setTimeout(() => {
            toast.classList.add('saliendo');
            /* Se espera a que termine la animacion CSS antes de eliminar el elemento */
            toast.addEventListener('animationend', () => toast.remove(), { once: true });
        }, duracion);
    },

    /**
     * Activa o desactiva el estado de carga de un boton de submit.
     * Muestra el spinner y deshabilita el boton para evitar doble envio.
     *
     * @param {HTMLElement} boton   - Elemento <button> a controlar.
     * @param {boolean}     cargando - true para activar carga, false para restaurar.
     */
    setBotonCargando(boton, cargando) {
        const texto   = boton.querySelector('.boton-texto');
        const spinner = boton.querySelector('.boton-spinner');

        boton.disabled    = cargando;
        texto.hidden      = cargando;
        spinner.hidden    = !cargando;
    },
};


/* ============================================================
   CAPA DE EVENTOS — Controladores y coordinacion
   ============================================================ */
const eventos = {

    /**
     * Registra todos los listeners de eventos de la aplicacion.
     * Se llama una sola vez en init() al cargar la pagina.
     */
    registrar() {
        this._registrarFormularioCrear();
        this._registrarFormularioEditar();
        this._registrarBotonesDelegados();
        this._registrarModal();
        this._registrarContadoresCaracteres();
        this._registrarBotonRecargar();
    },

    /**
     * Registro del formulario de creacion de tareas.
     * Valida el formulario HTML5 y luego llama a la API.
     */
    _registrarFormularioCrear() {
        const formulario = ui.elementos.formularioCrear();
        const boton      = document.getElementById('boton-crear');

        formulario.addEventListener('submit', async (evento) => {
            /* Previene el envio HTML nativo del formulario (recarga de pagina) */
            evento.preventDefault();

            /* Validacion HTML5 nativa antes de llamar a la API */
            if (!formulario.checkValidity()) {
                formulario.reportValidity();
                return;
            }

            /* Se recogen los valores de los campos */
            const datos = {
                titulo:      document.getElementById('campo-titulo').value.trim(),
                descripcion: document.getElementById('campo-descripcion').value.trim() || null,
                prioridad:   document.getElementById('campo-prioridad').value,
                completada:  document.getElementById('campo-completada').checked,
            };

            /* Bloquea el boton durante la peticion para prevenir doble envio */
            ui.setBotonCargando(boton, true);

            try {
                /* Llama a la API para crear la tarea */
                await api.crearTarea(datos);

                /* Limpia el formulario tras el exito */
                formulario.reset();
                /* Resetea los contadores de caracteres manualmente */
                document.getElementById('contador-titulo').textContent    = '0 / 100';
                document.getElementById('contador-descripcion').textContent = '0 / 500';

                ui.mostrarToast('Tarea creada correctamente.');

                /* Recarga la lista para mostrar la nueva tarea */
                await cargarTareas();

            } catch (error) {
                /* Muestra el error al usuario sin lanzar excepciones no controladas */
                ui.mostrarToast(`No se pudo crear la tarea: ${error.message}`);
            } finally {
                /* Restaura el boton siempre, haya exito o error */
                ui.setBotonCargando(boton, false);
            }
        });
    },

    /**
     * Registro del formulario de edicion de tareas (dentro del modal).
     */
    _registrarFormularioEditar() {
        const formulario = ui.elementos.formularioEditar();
        const boton      = document.getElementById('boton-guardar');

        formulario.addEventListener('submit', async (evento) => {
            evento.preventDefault();

            if (!formulario.checkValidity()) {
                formulario.reportValidity();
                return;
            }

            /* Se recoge el ID de la tarea que se esta editando */
            const id = parseInt(document.getElementById('editar-id').value, 10);

            const cambios = {
                titulo:      document.getElementById('editar-titulo').value.trim(),
                descripcion: document.getElementById('editar-descripcion').value.trim() || null,
                prioridad:   document.getElementById('editar-prioridad').value,
                completada:  document.getElementById('editar-completada').checked,
            };

            ui.setBotonCargando(boton, true);

            try {
                await api.actualizarTarea(id, cambios);
                ui.cerrarModalEdicion();
                ui.mostrarToast('Tarea actualizada correctamente.');
                await cargarTareas();
            } catch (error) {
                ui.mostrarToast(`No se pudo actualizar la tarea: ${error.message}`);
            } finally {
                ui.setBotonCargando(boton, false);
            }
        });
    },

    /**
     * Delega los eventos de click en la lista de tareas.
     *
     * Por que delegacion de eventos:
     *   Las tarjetas de tareas se crean dinamicamente. Si se añadieran
     *   listeners directamente a cada boton al crearlos, habria que
     *   eliminarlos al recargar la lista para evitar fugas de memoria.
     *   Con delegacion, se añade UN SOLO listener al contenedor padre
     *   que captura eventos de todos los botones hijo, independientemente
     *   de cuando se crearon.
     */
    _registrarBotonesDelegados() {
        const lista = ui.elementos.listaContenedor();

        lista.addEventListener('click', async (evento) => {
            const boton    = evento.target.closest('button');
            const checkbox = evento.target.closest('.tarea-checkbox');

            /* --- Accion: Toggle completada (click en checkbox circular) --- */
            if (checkbox) {
                const item = checkbox.closest('.tarea-item');
                const id   = parseInt(item.dataset.id, 10);
                /* El nuevo estado es el valor actual del checkbox tras el click */
                const nuevoEstado = checkbox.checked;

                try {
                    await api.actualizarTarea(id, { completada: nuevoEstado });
                    /* Se actualiza solo la clase del item sin recargar toda la lista */
                    item.classList.toggle('completada', nuevoEstado);
                    const titulo = item.querySelector('.tarea-titulo');
                    /* El titulo tachado se maneja via CSS segun la clase .completada */
                } catch (error) {
                    /* Si falla, se revierte el estado visual del checkbox */
                    checkbox.checked = !nuevoEstado;
                    ui.mostrarToast(`Error al actualizar: ${error.message}`);
                }
                return;
            }

            if (!boton) return;  /* Click en area vacia, se ignora */

            const item = boton.closest('.tarea-item');
            if (!item) return;
            const id = parseInt(item.dataset.id, 10);

            /* --- Accion: Editar tarea (boton "Editar") --- */
            if (boton.classList.contains('btn-editar')) {
                /*
                 * Para abrir el modal de edicion se necesitan los datos actuales
                 * de la tarea. En lugar de hacer una peticion GET a la API, se
                 * leen los datos directamente del DOM ya renderizado.
                 */
                const tareaActual = {
                    id,
                    titulo:      item.querySelector('.tarea-titulo').textContent,
                    descripcion: item.querySelector('.tarea-descripcion')?.textContent || null,
                    prioridad:   item.querySelector('.tarea-prioridad').textContent,
                    completada:  item.querySelector('.tarea-checkbox').checked,
                };
                ui.abrirModalEdicion(tareaActual);
                return;
            }

            /* --- Accion: Eliminar tarea (boton "Eliminar") --- */
            if (boton.classList.contains('btn-eliminar')) {
                /*
                 * Se pide confirmacion antes de eliminar para prevenir
                 * borrados accidentales. En produccion se podria reemplazar
                 * por un dialogo personalizado mas elegante.
                 */
                const titulo = item.querySelector('.tarea-titulo').textContent;
                if (!confirm(`Eliminar la tarea "${titulo}"? Esta accion no se puede deshacer.`)) {
                    return;
                }

                /* Se deshabilita el boton durante la operacion */
                boton.disabled = true;
                /* Animacion de salida sutil antes de eliminar del DOM */
                item.style.transition = 'opacity 300ms ease, transform 300ms ease';
                item.style.opacity    = '0.4';

                try {
                    await api.eliminarTarea(id);
                    ui.mostrarToast('Tarea eliminada.');
                    /* Se elimina el elemento del DOM sin recargar toda la lista */
                    item.remove();

                    /*
                     * Si la lista queda vacia tras la eliminacion, se muestra
                     * el estado vacio sin recargar desde la API.
                     */
                    if (ui.elementos.listaContenedor().children.length === 0) {
                        ui.mostrarEstadoLista('vacio');
                    }
                } catch (error) {
                    /* En caso de error, se revierte la opacidad del item */
                    boton.disabled = false;
                    item.style.opacity = '1';
                    ui.mostrarToast(`No se pudo eliminar: ${error.message}`);
                }
            }
        });
    },

    /**
     * Registra los eventos del modal (cerrar con boton, cancelar y fondo).
     */
    _registrarModal() {
        /* Boton de cierre (la X) */
        document.getElementById('modal-cerrar').addEventListener('click', () => {
            ui.cerrarModalEdicion();
        });

        /* Boton Cancelar dentro del formulario de edicion */
        document.getElementById('modal-cancelar').addEventListener('click', () => {
            ui.cerrarModalEdicion();
        });

        /*
         * Cierre al hacer click en el fondo semitransparente (fuera del modal).
         * Se verifica que el click sea directamente en el fondo y no en el modal.
         */
        ui.elementos.modalFondo().addEventListener('click', (evento) => {
            if (evento.target === ui.elementos.modalFondo()) {
                ui.cerrarModalEdicion();
            }
        });

        /* Cierre con la tecla Escape para accesibilidad de teclado */
        document.addEventListener('keydown', (evento) => {
            if (evento.key === 'Escape' && !ui.elementos.modalFondo().hidden) {
                ui.cerrarModalEdicion();
            }
        });
    },

    /**
     * Registra los contadores de caracteres en los campos de texto.
     * Actualiza el contador en tiempo real mientras el usuario escribe.
     */
    _registrarContadoresCaracteres() {
        const pares = [
            {
                campo:    document.getElementById('campo-titulo'),
                contador: document.getElementById('contador-titulo'),
                max:      100,
            },
            {
                campo:    document.getElementById('campo-descripcion'),
                contador: document.getElementById('contador-descripcion'),
                max:      500,
            },
        ];

        pares.forEach(({ campo, contador, max }) => {
            /* Evento 'input': se dispara en cada pulsacion de tecla o cambio */
            campo.addEventListener('input', () => {
                const longitud = campo.value.length;
                contador.textContent = `${longitud} / ${max}`;

                /*
                 * Cuando se acerca al limite, se cambia el color del contador
                 * a un gris mas oscuro para llamar la atencion sin usar colores.
                 */
                contador.style.color = longitud >= max * 0.9
                    ? 'var(--color-texto-secundario)'
                    : '';
            });
        });
    },

    /**
     * Registra el boton de recargar la lista de tareas.
     */
    _registrarBotonRecargar() {
        document.getElementById('boton-recargar').addEventListener('click', async () => {
            await cargarTareas();
        });
    },
};


/* ============================================================
   FUNCIONES DE APLICACION — Coordinacion entre API y UI
   ============================================================ */

/**
 * Carga todas las tareas desde la API y las renderiza en la lista.
 * Muestra el estado de carga mientras espera y maneja errores de red.
 */
async function cargarTareas() {
    ui.mostrarEstadoLista('cargando');

    try {
        const tareas = await api.listarTareas();
        ui.renderizarTareas(tareas);
    } catch (error) {
        ui.mostrarEstadoLista('oculto');
        ui.mostrarToast(`No se pudieron cargar las tareas: ${error.message}`, 5000);
    }
}

/**
 * Verifica el estado de conexion con la API y actualiza el indicador.
 * Se llama una vez al inicio y no bloquea el resto de la inicializacion.
 */
async function verificarConexion() {
    ui.actualizarEstadoConexion('conectando');

    try {
        await api.verificarSalud();
        ui.actualizarEstadoConexion('activo');
    } catch {
        /*
         * Si el health check falla, se marca como error pero NO se lanza
         * excepcion: la app sigue intentando cargar tareas de todas formas,
         * ya que el error de /health podria ser temporal.
         */
        ui.actualizarEstadoConexion('error');
    }
}


/* ============================================================
   INICIALIZACION DE LA APLICACION
   ============================================================ */

/**
 * Punto de entrada principal.
 * Se ejecuta cuando el DOM esta completamente cargado.
 *
 * Orden de inicializacion:
 *   1. Registrar todos los listeners de eventos.
 *   2. Verificar conexion con la API (no bloqueante).
 *   3. Cargar y renderizar la lista inicial de tareas.
 */
async function init() {
    /* 1. Registra todos los listeners de eventos de la UI */
    eventos.registrar();

    /* 2. Verifica la conexion con la API en paralelo con la carga de tareas
     *    usando Promise.all para no esperar a una antes de iniciar la otra.
     *    Esto reduce el tiempo de carga percibido por el usuario. */
    await Promise.all([
        verificarConexion(),
        cargarTareas(),
    ]);
}

/*
 * DOMContentLoaded: se dispara cuando el HTML ha sido parseado completamente
 * pero antes de que las imagenes y hojas de estilo externas hayan cargado.
 * Es el momento correcto para inicializar la logica JS del DOM.
 */
document.addEventListener('DOMContentLoaded', init);
