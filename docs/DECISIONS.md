# Decisiones técnicas

Este registro reúne las decisiones de arquitectura y producto del proyecto. Cada una sigue el mismo formato:
contexto → decisión → alternativas descartadas → ejemplo.
El plan de trabajo está en [PLAN_MAESTRO.md](PLAN_MAESTRO.md).

---

## D01 · El PDF define el alcance y el Figma la guía visual

**Contexto.** El Figma incluye funcionalidades que el PDF no pide: servicios adicionales, Wynwood Points,
impuestos, Apple/Google Pay y mapas. A la vez, no incluye la sección "Por qué viajar a España", que el PDF sí exige.

**Decisión.** El PDF es el alcance obligatorio y el Figma es la referencia visual. Lo que el Figma agrega se clasifica
por costo y valor (ver el alcance en el plan maestro). Lo que el PDF exige y el Figma no dibuja se diseña con el
lenguaje visual del Figma. Por ejemplo, "Por qué viajar a España" reutiliza el componente de la sección "Servicios en Wynwood House".

**Alternativas descartadas.** Implementar todo el Figma: no entra en el plazo y pone en riesgo los requisitos obligatorios.

---

## D02 · PostgreSQL como base principal; SQLite como alternativa documentada

**Contexto.** El enunciado admite cualquiera de las dos, pero pide que el README explique ambas.

**Decisión.** PostgreSQL en desarrollo (Docker), tests, CI y producción. La base se elige con `DATABASE_URL`, así que
SQLite funciona sin cambiar código. La restricción de exclusión de fechas es exclusiva de PostgreSQL: su migración
comprueba el motor y en SQLite no se aplica.

**Ejemplo.** `DATABASE_URL=sqlite:///db.sqlite3 python manage.py runserver` levanta el proyecto sin Docker.
En ese modo, la protección contra reservas simultáneas queda en la capa de aplicación (D07).

---

## D03 · Docker Compose para correr el proyecto en cualquier máquina

**Decisión.** Hay tres servicios en desarrollo: `web`, `db` (PostgreSQL 17) y `mailpit` (bandeja de correo local).
La imagen trae gettext, así que las traducciones compilan igual en Windows, macOS y Linux.

**Ejemplo.** `docker compose up` seguido de `docker compose exec web python manage.py seed_data` deja el sitio listo
en `http://localhost:8000` y los correos visibles en `http://localhost:8025`.

---

## D04 · Modelo de usuario propio con email como identificador

**Contexto.** En el `User` por defecto de Django el email no es único, y el enunciado exige emails únicos.

**Decisión.** `User(AbstractUser)` sin `username`, con `USERNAME_FIELD = "email"`. El email se normaliza a minúsculas
y lleva una restricción `UniqueConstraint(Lower("email"))`. Se define antes de la primera migración, porque cambiarlo
después es muy costoso.

**Ejemplo.** Si existe `ana@mail.com`, el registro con `Ana@Mail.com` se rechaza con el mensaje "Ya existe una cuenta con este email".

---

## D05 · Contraseñas seguras con los validadores de Django y una lista de requisitos en vivo

**Decisión.** El servidor aplica los validadores de Django: longitud mínima de 8 caracteres, contraseña común,
solo números y parecido con los datos del usuario. Se suma un validador propio que exige al menos un número o símbolo.
El navegador muestra la lista de requisitos del Figma mientras el usuario escribe. Esa lista es solo una ayuda:
la regla real la aplica el servidor.

---

## D06 · Solapamiento de reservas como intervalo semiabierto `[check_in, check_out)`

**Contexto.** "Reserva duplicada" se interpreta como cualquier solapamiento de fechas, no solo como fechas idénticas.

**Decisión.** La noche de salida no se ocupa. Dos reservas chocan si `A.check_in < B.check_out` y `A.check_out > B.check_in`.

**Ejemplo.** Existe una reserva A del 10 al 15 (noches del 10 al 14).

| Nueva reserva | Resultado | Motivo |
|---|---|---|
| 15 → 18 | ✅ permitida | A sale el 15 y la nueva entra el 15 |
| 5 → 10 | ✅ permitida | La nueva sale el día en que entra A |
| 14 → 16 | ❌ choca | Ambas ocupan la noche del 14 |
| 8 → 11 | ❌ choca | Ambas ocupan la noche del 10 |
| 11 → 13 | ❌ choca | Queda dentro de A |
| 5 → 20 | ❌ choca | Contiene a A |

Estos seis casos forman un test parametrizado.

---

## D07 · Validación de reservas en capas

| Capa | Mecanismo | Para qué sirve |
|---|---|---|
| Navegador | flatpickr con fecha mínima y fechas ocupadas deshabilitadas | Experiencia de usuario (no da seguridad) |
| Formulario | Fechas pasadas, orden de las fechas, capacidad | Mensajes claros junto a cada campo |
| Servicio | `transaction.atomic()` + `select_for_update()` sobre la propiedad + consulta de solapamiento | Serializa las reservas de una misma propiedad |
| Base de datos | `CheckConstraint(check_out > check_in)` y una restricción de exclusión de PostgreSQL (`EXCLUDE USING gist`, con `btree_gist`) sobre `daterange(check_in, check_out, '[)')` en `PENDING`/`CONFIRMED`, creada en una migración que en SQLite no hace nada | Garantía final, aunque fallara el código |

"No en el pasado" no puede ser una restricción de la base de datos: depende de la fecha actual y volvería inválidas
las reservas históricas. Por eso se valida solo al crear la reserva.

---

## D08 · Retención temporal de fechas con expiración perezosa

**Contexto.** Si las fechas se bloquearan sin límite al entrar al checkout, un usuario que abandona el pago las dejaría
ocupadas. Si no se bloquearan, dos personas podrían llegar al pago con las mismas fechas.

**Decisión.** Funciona como la compra de entradas en un cine:
- "Reservar" crea una reserva `PENDING` con `expires_at` (15 minutos, configurable por variable de entorno).
- El checkout muestra una cuenta regresiva.
- Una retención vencida deja de bloquear: las consultas la ignoran y, antes de crear otra que choque, el servicio la marca `EXPIRED` bajo el mismo bloqueo.
- Hay una sola retención activa por sesión: empezar otra libera la anterior.
- El comando `expire_holds` solo limpia estados; no hace falta para que el sistema sea correcto.

**Alternativas descartadas.** Celery + Redis para expirar retenciones: es infraestructura extra para algo que una
consulta con `expires_at > now()` ya resuelve.

**Ejemplo.**

| Hora | Qué pasa |
|---|---|
| 10:00 | Ana retiene del 10 al 15 de noviembre hasta las 10:15 |
| 10:05 | Beto ve esas fechas bloqueadas |
| 10:16 | Ana no pagó: Beto intenta reservar, la retención de Ana pasa a `EXPIRED` y se crea la de Beto |
| 10:20 | Ana pulsa "Pagar": ve "Tu tiempo expiró" y vuelve al detalle con sus datos precargados |

---

## D09 · La zona horaria de la ciudad decide qué es "pasado"

**Contexto.** Hay propiedades en distintos países y los huéspedes reservan desde cualquier zona horaria.

**Decisión.** `City.timezone` (por ejemplo `America/Bogota` o `Europe/Madrid`). La fecha mínima de check-in es
la fecha local de la propiedad.

**Ejemplo.** Son las 23:00 del 19 en Lima, que son las 06:00 del 20 en Madrid. Un check-in el 19 se acepta en Bogotá
y se rechaza en Madrid.

---

## D10 · El precio lo calcula el servidor y queda guardado en la reserva

**Decisión.** `pricing.py` calcula noches × precio + limpieza + impuestos del país (modelo `Tax`), con `Decimal`
y redondeo `ROUND_HALF_UP`. El resultado se guarda como `BookingLine`. Nunca se usa un precio enviado por el navegador.

**Ejemplo.** Ana reserva a US$ 120 la noche. Al día siguiente la propiedad sube a US$ 150. La confirmación y el correo
de Ana siguen mostrando US$ 120.

---

## D11 · Pago simulado con interfaz de pasarela e idempotencia

**Contexto.** El PDF no indica una pasarela. El Figma menciona dLocal.

**Decisión.** Una interfaz `PaymentGateway` con un adaptador `SimulatedGateway`. Integrar una pasarela real
(dLocal, Stripe) es agregar otro adaptador.

| Riesgo | Protección |
|---|---|
| Doble clic | Botón deshabilitado al enviar |
| F5 en la página que procesó el pago | Redirección a una página GET de confirmación (patrón PRG) |
| Reintento de red | `Payment.idempotency_key` única: la misma clave devuelve el mismo resultado sin volver a cobrar |
| Dos pestañas pagando a la vez | `select_for_update` sobre la reserva: la segunda petición ve `CONFIRMED` y no cobra |
| Fallo en el código | `UniqueConstraint`: solo un pago `SUCCEEDED` por reserva |

Otras medidas:
- Nunca se guardan ni se registran en logs los datos de tarjeta; solo la marca y los últimos 4 dígitos.
- El monto sale de la reserva.
- Se registra cada intento, también los fallidos.
- Solo el dueño puede pagar o ver su reserva.

**Tarjetas de prueba.** `4242 4242 4242 4242` aprueba. `4000 0000 0000 0002` rechaza; la retención sigue activa y se puede reintentar.

**Con una pasarela real** el flujo sería: crear el pago `PENDING`, llamar a la API con su cabecera de idempotencia
y confirmar al recibir el webhook.

---

## D12 · El checkout tiene dos pasos y el registro se guarda en el primero

**Contexto.** El Figma separa "Registro" de "Pago". El PDF pide registrar al usuario nuevo antes de reservar y pagar.

**Decisión.** Paso 1: crear la cuenta y los datos personales; el usuario inicia sesión y queda asociado a la retención.
Paso 2: el pago. Si el usuario ya tiene sesión, empieza en el paso 2. "¿Ya tienes una cuenta? Iniciar sesión" vuelve
al checkout gracias a un `next` validado. La sesión de Django conserva la retención al iniciar sesión, porque mantiene sus datos.

---

## D13 · Contenido bilingüe con `django-modeltranslation`

**Decisión.** Los campos de contenido tienen columnas `_es` y `_en`. Si falta una traducción, se muestra el español.

**Alternativas descartadas.** `django-parler` normaliza mejor si hay muchos idiomas, pero obliga a usar JOIN en cada
consulta. Para dos idiomas es complejidad innecesaria.

**Ejemplo.** Una propiedad tiene `title_es = "Ático con terraza en Malasaña"` y `title_en = "Penthouse with terrace in Malasaña"`.
`/es/` muestra el primero y `/en/` el segundo.

---

## D14 · Qué significa "nada hardcodeado"

**Decisión.**
- El **contenido** (lo que un administrador cambiaría sin programar) vive en modelos: propiedades, textos e imágenes
  del home, secciones, banners, contactos, redes, enlaces del footer e impuestos.
- Los **textos de la interfaz** ("Buscar", "Huéspedes", mensajes de error) usan `{% translate %}` y archivos `.po`,
  que es el mecanismo estándar de Django.

---

## D15 · CTA "Contáctanos" hacia WhatsApp configurable

**Decisión.** El número y un **mensaje general** están en `SiteSettings`. **Todo** enlace de WhatsApp del sitio
(el botón del banner y los números del footer) genera `https://wa.me/<número>?text=<mensaje en el idioma activo>`,
así el chat nunca se abre vacío. Un banner puede tener su **propio mensaje** (`Banner.cta_message`): el de larga
estancia pregunta por "estadías largas" y los demás usan el general. Un formulario de contacto queda como extra.

**Ejemplo.** En `/en/`, el número de Colombia del footer abre
`https://wa.me/573238110133?text=Hi%2C%20I%27d%20like%20to%20know%20more%20about%20staying%20with%20Wynwood%20House.`

---

## D16 · Imágenes optimizadas al guardar

**Decisión.** Un campo propio, `OptimizedImageField`, reemplaza a `ImageField` en todos los modelos con imágenes:
fotos de propiedades, hero, banners, secciones y destinos. Su archivo (`OptimizedImageFieldFile.save`) llama a
`optimize_image()`, que:
1. corrige la orientación con `ImageOps.exif_transpose`;
2. reduce con `thumbnail((1200, 1200))`, sin agrandar nunca una imagen chica;
3. guarda en WebP con calidad 80, conservando la transparencia si existe.

La optimización vive en el **archivo del campo** y no en `Model.save()` ni en una señal. Así pasa por ahí cualquier
escritura: las subidas del admin y de formularios (las confirma `pre_save` del campo), el seed y las llamadas directas
a `instancia.imagen.save(...)`. Solo se procesa lo que se sube: volver a guardar el modelo no reprocesa la imagen.
Los límites salen de los settings `IMAGE_MAX_DIMENSION` e `IMAGE_WEBP_QUALITY` y se leen al guardar, no quedan
congelados en las migraciones.

**Alternativas descartadas.**
- Una señal `post_save`: escribe el archivo dos veces y es fácil de saltarse.
- Procesar en `PropertyImage.save()`: no cubre las demás imágenes del sitio.

**Ejemplo.** Un JPG de 4000×3000 se guarda como `.webp` de 1200×900. Un PNG transparente de 300×300 queda en 300×300
con su transparencia.

---

## D17 · El correo se envía al confirmar la transacción, en el idioma de la reserva

**Decisión.** Se usa `transaction.on_commit` para no enviar correos de reservas que luego se revierten.
`translation.override(booking.language)` define el idioma. Se envía HTML y texto plano.
Para el envío se usa `django-anymail`: Mailpit en local y la API HTTP de Brevo en producción, lo que evita los puertos SMTP bloqueados.

---

## D18 · Bootstrap 5.3 sin herramientas de Node

**Decisión.** El enunciado pide "Bootstrap 3+". Bootstrap 5.3 lo cumple, no depende de jQuery y se personaliza con
variables CSS. Los archivos de Bootstrap, flatpickr y Leaflet se incluyen versionados en `static/vendor`, sin build de Node.
Hay un CSS por componente y un JS por comportamiento.

---

## D19 · Tipografía normalizada

**Contexto.** El Figma usa Helvetica en pesos 400, 500 y 700, además de Inter, Arial y Roboto en algunos frames.
Solo disponemos de Acumin Pro ExtraCondensed Bold y Helvetica Neue LT Std Roman.

**Decisión.**
- Acumin se usa para los títulos y Helvetica Roman para todo lo demás.
- El peso 500 se renderiza como 400, porque la diferencia es mínima.
- El 700 (totales) usa la negrita que genera el navegador.

---

## D20 · Diseño adaptable definido por nosotros

**Contexto.** El Figma solo tiene diseños a 1440 px.

**Decisión.** Se definió una matriz de anchos de 375 a 2560 px (plan maestro, sección 4). En monitores grandes el
contenido tiene un ancho máximo y la tipografía de títulos es fluida con `clamp()`.

---

## D21 · Despliegue gratuito: Render + Neon + Cloudinary + Brevo

**Contexto.** El presupuesto es cero y no hubo acceso a un VPS gratuito.

**Decisión.** Render ejecuta la imagen Docker, Neon aloja PostgreSQL (no caduca), Cloudinary guarda los archivos media
(el disco de Render es efímero) y Brevo envía los correos. El script de arranque migra, ejecuta el seed si la base está
vacía y crea el superusuario desde variables de entorno.

**Alternativas descartadas.**
- Un PC personal con túnel: disponibilidad incierta durante la revisión.
- Infraestructura de terceros: no es propia.

**Contras asumidos.** El servicio se duerme tras 15 minutos sin tráfico; se mitiga con UptimeRobot.

---

## D22 · Fuentes y fotos propietarias en un repositorio público

**Decisión.** Se incluyen porque WH las entregó para la prueba y sin ellas el sitio no se ve como el diseño.
El README aclara que son propiedad de sus autores, que se usan solo para la evaluación y que no las cubre la licencia del repositorio.

---

## D23 · Contenido único del sitio como modelos singleton

**Contexto.** Textos como el título del hero o el número de WhatsApp existen una sola vez, pero deben editarse desde el admin.

**Decisión.** `SingletonModel` abstracto: `save()` fija siempre `pk=1` y `load()` devuelve la única fila (la crea si no
existe). En el admin, la lista abre directamente esa fila y no se puede borrar ni duplicar.

**Alternativas descartadas.** `django-solo`: es una dependencia para unas 15 líneas de código propio.

---

## D24 · Íconos y banderas se eligen de una lista, no se suben

**Decisión.** Los íconos de comodidades y redes sociales salen de Bootstrap Icons, y las banderas de flag-icons
(ambos con licencia MIT, incluidos en `static/vendor`). El modelo guarda una clave de una lista de opciones
(por ejemplo `wifi` o `pe`).

**Por qué.** Un SVG subido por un usuario puede contener JavaScript, lo que abre la puerta a ataques XSS. Además,
una lista cerrada garantiza que nunca aparezca un ícono roto. Los íconos de comodidades del Figma no se podían
exportar porque están aplanados dentro de una imagen.

---

## D25 · Datos de prueba con un cargador idempotente

**Decisión.** `seed_data` separa los **datos** (`apps/core/seeding/data.py`, tuplas ES/EN) de la **carga**
(`loader.py`). Cada registro se busca por una clave natural (slug, código, `key`) con `update_or_create`,
así que ejecutar el comando dos veces no duplica nada. Las fotos se adjuntan solo si el registro no tiene,
y pasan por el mismo optimizador que el admin.

**Opciones.** `--flush` borra el contenido sembrado sin tocar los usuarios. `--properties N` carga solo N propiedades.
`--skip-images` lo hace más rápido.

Las fotos del seed se guardan en el repo a 1600 px como máximo: superan el límite de 1200, así que el seed demuestra
el redimensionado, sin inflar el repositorio. Las de España vienen de Wikimedia Commons con su licencia registrada
en `seed/images/CREDITS.md`.

---

## D26 · `makemessages` sin coincidencias aproximadas

**Contexto.** Al extraer textos nuevos, `msgmerge` adivina traducciones a partir de textos parecidos y las marca
como *fuzzy* (por ejemplo "country" → "Cuentas"). `compilemessages` ignora esas entradas, así que el texto queda
en inglés sin ningún aviso.

**Decisión.** El proyecto sobrescribe el comando `makemessages` y agrega `--no-fuzzy-matching`: los textos nuevos
empiezan vacíos y se traducen a conciencia.

---

## D27 · Mapas con Leaflet y OpenStreetMap, y ubicación aproximada antes de reservar

**Contexto.** Ver la ubicación es esencial para decidir una reserva. El Figma tiene un mapa en los resultados y otro
en el detalle ("Ubicación").

**Decisión.**
- **Leaflet** (JS, licencia BSD) con mapas de **OpenStreetMap**, con atribución. No requieren clave ni tarjeta y no
  tienen costo para el tráfico de esta demo. Los mapas se tiñen en gris con CSS para acompañar el diseño sobrio del Figma.
- **"Abrir en Google Maps"**: un enlace `https://www.google.com/maps/search/?api=1&query=lat,lng`, que no necesita clave.
  Así el huésped usa la app que ya conoce para llegar.
- **Privacidad, como Airbnb:**
  - **antes de reservar**, el detalle muestra un círculo de unos 300 m sobre la zona, no el edificio exacto,
    y la dirección sin número;
  - **después de pagar**, la confirmación y el correo muestran la dirección exacta.
- Las coordenadas viven en la propiedad (latitud y longitud con 6 decimales, unos 10 cm de precisión). Las del seed
  se verificaron con geocodificación inversa: las 12 caen en su barrio.
- **Coordenadas públicas:** fuera de la confirmación, el mapa recibe `Property.public_coordinates`, redondeadas a 3
  decimales (~100 m). Así el código de la página nunca contiene la ubicación exacta antes del pago.
- **Agrupamiento:** con resultados en varios países, los marcadores de una misma ciudad se superponían. Se agrupan
  (Leaflet.markercluster, MIT) en un círculo con la cantidad; un clic acerca el mapa y, a nivel de calle, cada
  propiedad muestra su precio.
- **Gestos:** el mapa de resultados ocupa media pantalla y es la herramienta principal, así que la rueda hace zoom
  directamente (como Airbnb). El mapa del detalle está dentro de la página: con `leaflet-gesture-handling` (MIT)
  la rueda sola sigue bajando la página, **Ctrl/⌘ + rueda** hace zoom, se arrastra con el mouse y en pantallas
  táctiles se mueve con dos dedos, con un aviso traducido por Django (como los mapas de Google embebidos).
- **Seguridad:** el texto de los marcadores y de la mini tarjeta se inserta con `textContent`, nunca como HTML,
  porque los títulos vienen del admin (evita XSS).

**Alternativas descartadas.** La API de Google Maps exige una cuenta de facturación con tarjeta, incluso para el
plan gratuito, y una clave expuesta en el navegador que hay que restringir. Para la demo es costo y riesgo sin beneficio;
cambiar de proveedor de mapas solo toca un componente de plantilla y su JS.

---

## D28 · Componentes de plantilla y mejora progresiva

**Decisión.** Cada pieza visual que se repite es un componente en `templates/components/` con su propio CSS:
`search_bar` (variantes `hero` y `footer`), `property_card` (`overlay` y, en la Fase 4, `stacked`),
`feature_grid` (`tiles` y `cards`), `banner` (tres diseños) y `carousel_controls`.
"Servicios" y "Por qué viajar a España" son el mismo componente con otra variante.

**Mejora progresiva.** Todo funciona sin JavaScript, y el JS solo mejora:
| Sin JS | Con JS |
|---|---|
| Dos campos de fecha nativos | Un selector de rango (flatpickr) que escribe en esos mismos campos |
| Distritos agrupados por ciudad (`<optgroup>`) | Solo los distritos de la ciudad elegida |
| Carruseles con scroll nativo (táctil, trackpad, teclado) | Flechas anterior y siguiente |
| Contenido visible | Aparición al hacer scroll (desactivada con "reducir movimiento") |

El servidor siempre recibe los mismos campos y valida igual (por ejemplo, que el distrito pertenezca a la ciudad).

---

## D29 · Header y footer con un context processor perezoso

**Decisión.** `apps.core.context_processors.site` expone menús, contactos, redes, destinos y el buscador del footer
a todas las páginas, envueltos en `SimpleLazyObject`. Solo se consultan si la plantilla los usa: el admin, que no
pinta el footer del sitio, no hace esas consultas.

**Garantía.** Un test comprueba que el número de consultas del home no crece con la cantidad de propiedades
(sin N+1). Otro recopila los estáticos con el almacenamiento de producción y renderiza las páginas, para detectar
rutas de `{% static %}` que solo fallarían en el servidor.

---

## D30 · El modelo `Booking` se adelanta a la Fase 4

**Contexto.** El PDF pide que los resultados obedezcan el filtro de fechas. Para saber qué está ocupado hace falta
el modelo de reservas, que el plan ubicaba en la Fase 5.

**Decisión.** La Fase 4 crea `Booking` con sus estados, restricciones (`check_out > check_in`, `guests >= 1`) y dos
consultas reutilizables:
- `blocking()`: reservas confirmadas o retenciones `PENDING` con `expires_at` en el futuro (la expiración es
  perezosa, D08);
- `overlapping(check_in, check_out)`: intervalo semiabierto (D06).

La búsqueda las combina con `~Exists(...)`, una subconsulta, sin traer reservas a Python. La Fase 5 reutiliza esas
mismas consultas en el servicio de reservas, así que **la búsqueda y la validación de una reserva no pueden discrepar**.

**Detalles.** La referencia (`WH-7K3M9QX2`) es aleatoria, no secuencial, y sin caracteres ambiguos (0/O, 1/I/L).
`--flush` del seed se niega a borrar si existen reservas que no sean de demo.

---

## D31 · Un filtro inválido no anula la búsqueda

**Decisión.** Si un campo del buscador es inválido (por ejemplo, la salida antes de la llegada), la página muestra
el error y aplica igual los filtros válidos (la ciudad, los huéspedes). Django ya deja fuera de `cleaned_data` los
campos con error, así que la vista usa solo lo que pasó la validación.

**Por qué.** Es mejor que mostrar cero resultados o ignorar el error en silencio: el usuario ve qué corregir y
mientras tanto sigue viendo propiedades relevantes.

---

## D32 · Reservas en línea de hasta 30 noches; las más largas, por contacto

**Contexto.** El Figma muestra en la tarjeta de reserva dos pestañas, "Diario" y "Mensual", y el home tiene un banner
de "Alquileres a largo plazo" con "Contáctanos". El PDF no fija límites de duración.

**Decisión (suposición documentada).** La pestaña "Diario" reserva en línea hasta `BOOKING_MAX_NIGHTS` noches
(30 por defecto). "Mensual" explica las tarifas especiales y abre WhatsApp con un mensaje que nombra la propiedad.
Las reservas se aceptan hasta `BOOKING_MAX_DAYS_AHEAD` días de anticipación (365). Ambos valores son configurables
por variable de entorno.

**Por qué.** Separa el flujo automático (estadías cortas, precio por noche) del comercial (estadías largas con
tarifa negociada), como sugiere el diseño, y evita retener un calendario durante meses desde un formulario anónimo.

---

## D33 · Detalle con `FormMixin` + `DetailView` y precio en vivo desde el servidor

**Decisión.**
- La misma URL de la propiedad muestra la página (GET) y crea la retención (POST). Es el patrón que documenta Django
  para combinar un formulario con un `DetailView`: si hay errores, la página se vuelve a mostrar con los mensajes
  junto a los campos, sin perder la galería ni el contexto.
- El desglose se recalcula en el servidor (`GET .../quote/`, JSON) cada vez que cambian las fechas o los huéspedes.
  El navegador nunca calcula precios: muestra lo que devuelve el servidor, con `textContent`.
- Si la URL trae fechas (desde la búsqueda, o al volver de un checkout vencido), el formulario se completa con ellas
  y la página muestra disponibilidad y precio sin JavaScript.
- Las fechas ocupadas viajan al calendario como rangos de noches (`check_in` a `check_out - 1`): el día de salida de
  una estadía queda libre para la siguiente llegada. flatpickr deshabilita días sueltos pero permite marcar un rango
  por encima de ellos, así que el JS rechaza los rangos que cruzan una noche ocupada; el servidor valida igual.

**Limitación conocida.** Como el calendario deshabilita las noches ocupadas, no permite elegir como salida el día
en que empieza otra reserva, aunque el servidor lo acepta (intervalo semiabierto). Para la demo es aceptable;
resolverlo requiere un componente de calendario propio.
