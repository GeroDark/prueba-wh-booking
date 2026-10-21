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

**Decisión.**
- El servidor aplica los validadores de Django (longitud mínima de 8, contraseña común, solo números) y tres propios
  en `apps/accounts/validators.py`: **al menos un número o símbolo**, **no contener el nombre ni el correo** (por
  ejemplo, rechaza `torres-2026!` para Ana Torres) y **no ser una palabra común con números o símbolos**
  (`contraseña123`, `Password2026!`; la lista de Django es en inglés y solo busca coincidencias exactas).
- `PersonalInfoValidator` **reemplaza** al `UserAttributeSimilarityValidator` de Django: detecta si la contraseña
  *contiene* el dato (no solo si se parece entera) y así el usuario ve un único mensaje por problema.
- La contraseña se valida contra lo escrito en el formulario aunque el correo o el nombre tengan errores.
- Medidor: "fuerte" exige 12+ caracteres y 3 tipos de carácter (minúsculas, mayúsculas, números, símbolos).
- Como en el Figma, hay **un solo campo** de contraseña, con botón para mostrar u ocultar (en lugar de un segundo campo
  de confirmación) y una lista de requisitos que se marca mientras se escribe.
- La lista del navegador es solo una guía: el servidor siempre valida, y además rechaza las contraseñas comunes, que
  el JS no puede conocer.
  - **Se avisa de antemano (agregado después):** al probar la recuperación en producción, la lista marcó todo en verde
    y el servidor rechazó la contraseña por ser una palabra común con números, sin que el usuario supiera por qué. La
    lista ahora incluye una línea fija, sin ✓: "Tampoco se aceptan palabras comunes con números, como
    “Contraseña2026!”". Un test comprueba que el ejemplo de cada idioma es uno que el servidor rechaza de verdad.
- Tras un error, la contraseña no se vuelve a escribir en la página (Django no re-renderiza `PasswordInput`).

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

**La búsqueda aplica la misma regla (corregido después, D42).** Con una ciudad elegida usa la fecha de esa ciudad; sin
ciudad, la más temprana entre las ciudades, y los resultados excluyen las ciudades donde la llegada ya pasó. Antes
usaba la fecha del servidor (Lima): de noche aceptaba una llegada en Madrid que la reserva rechazaba, y pasada la
medianoche rechazaba una en Ciudad de México que la reserva aceptaba.

**Y el calendario del buscador también (D42).** Cada página envía la primera llegada posible de cada ciudad
(`#arrival-min-by-city`), y el calendario la usa y la actualiza al cambiar de ciudad o de distrito, en vez de tomar
"hoy" del dispositivo. Si la llegada elegida ya pasó en el nuevo destino, se borran las fechas.

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
- La pasarela simulada solo aprueba o rechaza las tarjetas de prueba documentadas; cualquier otra se rechaza con un
  aviso de demo, así nadie "paga" con una tarjeta real ni en apariencia.
- El cobro ocurre con la fila de la reserva bloqueada. Con una pasarela real la llamada se haría igual, dentro del
  bloqueo, y la clave de idempotencia de la pasarela cubriría los reintentos de red.
- Un rechazo muestra el motivo y un formulario nuevo (otra clave, campos de tarjeta vacíos): reintentar es un intento
  nuevo. La misma clave enviada otra vez devuelve el mismo resultado, sin cobrar.
- La página de pago no se guarda en caché (`never_cache`) y los campos de tarjeta y contraseña se ocultan en los
  reportes de error de Django (`sensitive_post_parameters`). El código de seguridad nunca se vuelve a escribir en la página.
- Nunca se guardan ni se registran en logs los datos de tarjeta; solo la marca y los últimos 4 dígitos (PCI DSS
  permite conservar como máximo los primeros 6 y los últimos 4, y prohíbe guardar el código de seguridad).
- **Tarjetas reales en la demo.** Un número no se puede clasificar como "real" o "de prueba" por su forma: cualquier
  número que pase Luhn podría existir. Por eso se usa una lista blanca: las tarjetas de prueba públicas (las de
  Stripe, que no pertenecen a nadie). Con JavaScript, cualquier otro número se detiene en el navegador y no se
  envía; sin JavaScript, el servidor lo rechaza, lo descarta y no lo guarda.
- **En producción** el número no debería pasar por nuestro servidor: la pasarela (Stripe Elements, dLocal Smart Fields)
  lo captura en un iframe propio y devuelve un *token*. Así el sitio queda fuera de casi todo el alcance de PCI DSS
  (SAQ A). Es el siguiente paso al integrar una pasarela real.

**Límite conocido: la pasarela cobra y la respuesta se pierde.** Las protecciones de arriba evitan un segundo cobro
mientras la aplicación sabe lo que pasó. El caso que no resuelven es una pasarela real que cobra y cuya respuesta no
llega (corte de red, *timeout*, el proceso muere):

- **Hoy:** el registro `Payment` y la llamada a la pasarela están en la misma transacción. Si la llamada falla
  después de cobrar, la transacción se revierte: no queda rastro del intento y la reserva sigue pendiente.
  - Si el huésped reintenta **con el mismo formulario** (misma clave), una pasarela real con idempotencia devuelve el
    cobro original: un solo cobro y la reserva se confirma.
  - Si no reintenta, o recarga la página (clave nueva), puede quedar **dinero cobrado sin reserva confirmada**.
  - Con la pasarela simulada no ocurre, porque no tiene red, pero con una real sí.
- **Diseño para una pasarela real:**
  1. Guardar el `Payment` como `PROCESSING` **en su propia transacción, antes** de llamar a la pasarela, con su clave
     de idempotencia: el intento existe aunque todo lo demás falle.
  2. Una restricción parcial única: como mucho un pago `PROCESSING` o `SUCCEEDED` por reserva, así otra pestaña no
     puede iniciar un segundo cobro mientras hay uno en curso.
  3. Llamar a la pasarela con esa clave y actualizar el estado con la respuesta.
  4. Si la respuesta se pierde, el pago queda `PROCESSING`. Se resuelve con los **webhooks** de la pasarela (la señal
     principal) y un comando de **conciliación** de respaldo, que consulta el estado real por la clave:
     - cobrado y las fechas siguen libres → se confirma;
     - cobrado pero la retención venció y otro reservó → **reembolso automático** y aviso al huésped;
     - no cobrado → se marca fallido.
- No se implementó porque la pasarela simulada no puede perder respuestas y no habría forma honesta de probarlo. Es
  el primer trabajo al integrar dLocal o Stripe.
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

**Implementación.** Los dos pasos viven en una sola URL (`/checkout/<referencia>/`); la vista decide el paso según el
visitante: sin sesión → registro completo; con sesión y perfil incompleto → solo los datos que faltan; perfil
completo → pago. Cada POST correcto redirige a la misma URL (PRG). Al registrarse o iniciar sesión, la retención
pasa a ser del usuario (`assign_guest`), solo si aún no tenía dueño.

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

**Salida el día en que empieza otra reserva (resuelto después, D42).** Al principio el calendario deshabilitaba los
días de las noches ocupadas tanto para la llegada como para la salida, así que no dejaba irse el día en que llega otro
huésped, aunque el servidor lo acepta (intervalo semiabierto). Ahora qué días están deshabilitados depende de qué se
está eligiendo:
- **llegada:** las noches ocupadas;
- **salida:** los días cuya estadía cruzaría una noche ocupada; el día en que empieza otra reserva queda libre.

---

## D34 · Autenticación sin filtrar información

**Decisión.**
- **Sin enumeración de cuentas:** el login responde "El correo o la contraseña no son correctos" tanto si el correo
  no existe como si la contraseña es incorrecta. Así no se puede averiguar quién tiene cuenta.
  (El registro sí avisa "ya existe una cuenta con este correo", porque es necesario para el usuario; es el equilibrio
  habitual entre usabilidad y privacidad.)
- **Cerrar sesión solo por POST** (Django 5): un enlace o una imagen en otra web no pueden cerrar la sesión de nadie (CSRF).
- **`next` validado** con `url_has_allowed_host_and_scheme`: después de iniciar sesión solo se vuelve a páginas de
  este sitio (evita *open redirects*).
- **La sesión sobrevive al login:** Django cambia la clave de la sesión al iniciar sesión (contra la fijación de
  sesión) pero conserva sus datos. Una retención hecha antes de registrarse sigue perteneciendo al visitante (test incluido).
- Login con email sin distinguir mayúsculas y quien ya tiene sesión no ve los formularios de acceso.

**Agregado después.** El límite de intentos de login (D41) y la recuperación de contraseña (D43).

---

## D35 · Validación de formularios en dos capas y mensajes propios

**Contexto.** Una prueba manual mostró errores que quedaban visibles tras corregir el campo, un nombre con números
aceptado y mensajes de Django en "usted" ("Introduzca una fecha válida").

**Decisión.**
- **Servidor = autoridad.** Todo se valida en Django. Nombre completo (`validate_full_name`, en el modelo): letras de
  cualquier idioma, espacios, `-`, `'`, `’` y `.`, con nombre y al menos un apellido (debe coincidir con el documento en
  el check-in). Se normaliza a NFC y sin espacios repetidos.
- **Navegador = ayuda** (`form-feedback.js`, formularios con `data-validate`): el error se borra al editar, cada campo
  se revisa al salir y todos al enviar; si algo falla no se envía (no se pierde la contraseña) y el foco va al primer
  error. Los mensajes llegan desde el formulario (`data-error-required`, `data-error-invalid`) con el filtro
  `accessible`: una sola fuente de textos, traducidos.
- **Mensajes propios en todos los formularios** (`FriendlyErrorsMixin`): tono "tú", dicen qué corregir y no repiten el
  valor enviado. En la búsqueda, cada error indica su campo ("Llegada: Ingresa una fecha válida.").

**Límite.** No se puede distinguir un nombre real de letras al azar sin verificar un documento.

**Auditoría de todas las entradas (Fase 8).** Se atacaron todos los formularios y parámetros (búsqueda, detalle,
cotización, reserva, registro, login, checkout, pago, cambio de idioma, `next`) con fechas imposibles, números
negativos o no numéricos, textos enormes, HTML, caracteres nulos, redirecciones externas y campos extra
(`is_staff`). Huecos encontrados y cerrados:
- La búsqueda aplica ahora las mismas reglas de fechas que la reserva (`date_errors`: no pasadas, hasta 365 días,
  1 a 30 noches): no muestra estadías que luego no se pueden reservar.
- `?page=abc` o una página inexistente abren la primera o la última página en vez de un 404.
- El modelo `User` valida teléfono (y lo normaliza) y fecha de nacimiento, también al editar desde el admin.
- `Booking.clean()` valida capacidad y solapamiento en el admin con un mensaje claro, en vez del error de la base.

---

## D36 · Datos personales del checkout

**Contexto.** El Figma pide nombre completo, nacionalidad, indicativo y teléfono, y fecha de nacimiento.

**Decisión.**
- **Nacionalidad** con `django-countries`: los ~250 países con nombres traducidos al español y al inglés; los países
  donde opera Wynwood House aparecen primero (`COUNTRIES_FIRST`).
- **Teléfono** con `phonenumbers` (libphonenumber de Google): cada país tiene sus propias longitudes y prefijos, algo
  que una expresión regular no puede validar. Se guarda como indicativo (`+51`) + número nacional (`987654321`).
  Si el número se escribe con su propio `+`, manda ese indicativo. Se rechazan letras (libphonenumber convertiría
  "1-800-FLOWERS" en dígitos). El indicativo sigue a la nacionalidad mientras el usuario no lo cambie.
- **Fecha de nacimiento:** en el pasado, como máximo 120 años y **mayor de edad** (`BOOKING_MIN_GUEST_AGE = 18`):
  quien reserva y paga firma el alquiler. La edad se calcula con la fecha local del sitio.
- **Términos:** como en el Figma, se aceptan al pulsar el botón ("Al seleccionar Continuar, aceptas…"). Los enlaces
  vienen de `SiteSettings` (admin); sin URL se muestran como texto.
- **Boletín con consentimiento explícito.** El Figma usa "No deseo suscribirme" (suscripción por defecto), pero el
  GDPR (España) y la Ley 29733 (Perú) piden consentimiento libre e inequívoco. La casilla es "Quiero recibir…",
  **desmarcada**, está **antes** del botón y se guarda la fecha del consentimiento (`marketing_consent_at`) como
  prueba; retirarlo la borra. Se aplica a todos los países: una sola regla, la más estricta.
- **El indicativo nunca se duplica.** Se guarda aparte del número; `987654321`, `+51 987654321`, `51987654321` y
  `0051 987654321` quedan como `+51` + `987654321`. Si se escribe dos veces (`+51 51 987…`), el mensaje lo dice.

**Fuera de alcance (documentado).** Servicios adicionales, datos de facturación, cuotas, Wynwood Points y
Apple Pay/Google Pay (requieren una pasarela real).

---

## D37 · Correo de confirmación

**Decisión.**
- **Cuándo:** con `transaction.on_commit`, solo cuando el pago aprobado ya está guardado. Si algo falla y la
  transacción se revierte, no sale ningún correo.
- **Tres estados:** pendiente → enviándose (`confirmation_claimed_at`) → enviado (`confirmation_sent_at`).
  - **Reclamar:** un `UPDATE` condicional sobre las reservas pendientes; dos procesos no pueden enviar el mismo correo
    a la vez.
  - **Marcar como enviado:** **solo después** de que el proveedor aceptó el mensaje. Cualquier fallo posterior al
    reclamo (leer la reserva, armar el correo, llamar al proveedor) libera el reclamo y la reserva vuelve a pendiente.
  - *Corrección tras una revisión externa:* antes la marca de enviado se escribía primero y la lectura de la reserva
    quedaba fuera del manejo de errores, así que un fallo ahí dejaba un correo "enviado" que nunca salió.
- **Si el proceso muere mientras envía:** el reclamo queda "viejo". Después de 10 minutos, `send_booking_confirmations`
  lo retoma. La entrega es **al menos una vez**: un corte justo después de que el proveedor aceptó puede producir una
  copia repetida, que es preferible a una reserva sin confirmación. En el admin hay una acción para reenviarlo a pedido.
- **Idioma:** el de la reserva (`Booking.language`), con `translation.override`: asunto, textos, montos, fechas y
  enlaces (`/es/` o `/en/`). Se fija **al pagar**, no al retener las fechas: si el huésped cambia de idioma en el
  checkout, todo sigue al idioma en que terminó (también su idioma preferido).
- **El enlace del correo sin sesión** (otro dispositivo) pide iniciar sesión y vuelve a la reserva, en vez de un 404.
  Se responde igual para cualquier referencia, exista o no, así que no revela nada; otra cuenta sigue recibiendo 404.
- **Páginas de error propias:** 404 con el diseño del sitio y en el idioma de la URL; 500 independiente y bilingüe
  (Django la muestra sin contexto, así que no puede depender del header ni de la base de datos).
- **Diseño:** el frame "Correo confirmación" del Figma, como tabla de 600 px con estilos en línea, fuentes seguras
  y versión de texto plano. Los iconos y el logo van en PNG (Gmail no muestra SVG).
- **Fotos:** el sitio guarda WebP (requisito 8), pero cerca de un cuarto de los clientes de correo (Outlook para
  Windows, entre otros) no lo muestra. Para el correo se genera una copia JPEG la primera vez y se reutiliza.
- **Envío:** Mailpit por SMTP en local; Brevo por API HTTP en producción (`django-anymail`), porque los planes
  gratuitos de hosting bloquean los puertos SMTP. El PDF permite "SMTP local o API".
- **Enlaces absolutos** con `SITE_URL`: un correo no tiene petición de la que sacar el dominio.

**Mejora futura.** El envío ocurre dentro de la petición, después del pago (unos cientos de milisegundos con la
API). Con más volumen iría a una cola (Celery o RQ) para que el huésped no espere al proveedor de correo.

---

## D38 · Protección de los datos de producción

**Contexto.** Antes del despliegue se acordó cómo trabajar sin poner en riesgo la base de producción, también cuando
el desarrollo lo hace un asistente de IA.

**Decisión (capas).**
1. **Sin acceso directo:** la URL de la base solo existe en las variables de entorno de Render; ni en el repositorio,
   ni en `.env` locales, ni en conversaciones. El desarrollo usa la base local de Docker.
2. **Un solo camino a producción:** rama → pull request → CI → revisión → merge → despliegue. En esta demo cada
   despliegue fue manual (*Manual Deploy* en Render, después de cada merge), porque el repositorio se conectó por su
   URL pública; con Render conectado a GitHub sería automático (`autoDeploy` en `render.yaml`).
3. **Migraciones revisadas:** un test falla si una migración incluye `RemoveField`, `DeleteModel`, `RunSQL` o
   `RunPython` sin declarar `reviewed_data_safety` con el motivo. La justificación queda visible en el pull request.
4. **Comandos destructivos bloqueados** en producción (`flush`, `seed_data --flush`) salvo con una bandera explícita.
5. **Respaldos:** restauración de Neon a un momento reciente, ramas de Neon para probar migraciones y `pg_dump` manual
   antes de cambios delicados. Nunca en GitHub (repositorio público, datos personales).

**Correcciones de datos en producción:** una migración de datos o un comando, revisado en un pull request, que ejecuta
una persona después de un respaldo.

---

## D39 · Despliegue en Render (Blueprint)

**Decisión.**
- **`render.yaml`:** el servicio se describe en el repositorio (Docker, plan gratuito, Virginia, `/health/`); los
  secretos van con `sync: false` y Render los pide en un formulario. Es la misma imagen de desarrollo y CI.
- **Arranque idempotente:** migraciones → `ensure_superuser` (crea el admin desde variables de entorno si no existe;
  el plan gratuito no tiene consola) → `seed_data --if-empty` (solo si no hay propiedades, para que un reinicio no pise
  las ediciones del admin) → gunicorn.
- **Fotos en Cloudinary** (`CloudinaryMediaStorage`, un adaptador corto sobre el SDK oficial): el disco de Render se
  borra en cada despliegue y reinicio. `django-cloudinary-storage` se descartó por no actualizarse desde 2020.
- **Host automático:** `RENDER_EXTERNAL_HOSTNAME` alimenta `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y `SITE_URL`.
- **Sonda de salud primero:** `HealthCheckMiddleware` responde las rutas de salud antes de validar el host y de
  redirigir a HTTPS, porque la sonda del proveedor puede llegar con un host interno (`localhost:10000`) y por HTTP.
- **`/health/` no consulta la base; `/health/db/` sí.** Render llama a `/health/` cada 5 segundos y UptimeRobot cada 5
  minutos. Si esa ruta consultara la base, Neon (gratis: se duerme tras 5 minutos sin actividad, unas 100 horas de
  cómputo al mes) nunca se dormiría y agotaría su cuota a mitad de mes, lo que suspendería la base y el sitio. Que la
  comprobación de "la app está viva" no dependa de servicios externos es además la práctica habitual. `/health/db/`
  queda para revisiones manuales.
- **Conexiones no persistentes en producción** (`CONN_MAX_AGE=0`): cada petición cierra su conexión para que Neon
  pueda dormirse entre visitas. Cuesta unos milisegundos de conexión por petición.
- **Límites aceptados del plan gratuito:** el servicio se duerme tras 15 minutos sin visitas. UptimeRobot lo evita y lo
  mantiene encendido 24/7, unas 744 de las 750 horas mensuales del espacio de trabajo: alcanza solo si es el único
  servicio gratuito. No hay tareas programadas (las retenciones vencidas ya no bloquean fechas por sí solas, D08).

---

## D40 · Revisión externa: correcciones y límites reconocidos

**Contexto.** Una revisión externa del commit `bf35b71` (con pruebas y reproducciones en una copia local) señaló
problemas reales. Se comprobó cada uno antes de actuar.

**Corregido:**

| Hallazgo | Corrección |
|---|---|
| **XSS almacenado:** `MenuLink.url` y `Banner.cta_url` aceptaban `javascript:alert(1)` y las plantillas lo ponían en `href`. El escape de HTML no lo evita | Lista blanca en el modelo (`apps/core/links.py`): `https://` y `http://` con host, rutas internas (`/…`, no `//…`), anclas, `mailto:` y `tel:`. Filtro `safe_link` en las plantillas como segunda barrera. Tests con trucos de navegador (`java\tscript:`, espacios delante, `//host`, `/\host`, `data:`) |
| **Correo marcado "enviado" sin enviarse** | Estados reales y recuperación de envíos interrumpidos (D37) |
| **Prueba de concurrencia que pasaba aunque un hilo fallara** | Los hilos recogen sus excepciones y la prueba exige los dos resultados |
| **Fallos con SQLite** (3 fallidas y 2 errores) | El bloqueo de `flush` (D38) no reconocía la base de pruebas de SQLite. Además, SQLite no tiene bloqueo de filas: ahora usa transacciones `IMMEDIATE` (serializan las escrituras) y CI corre toda la suite también con SQLite |
| **Garantías demasiado absolutas** en la documentación ("nunca cobra dos veces") | Redactadas con sus límites; el caso "la pasarela cobra y la respuesta se pierde" está explicado en D11 |

**Atendido después (D41):** límite de intentos de login por cuenta + red y límite de retenciones activas por red.

**Reconocido y pendiente (antes de operar con dinero y usuarios reales):**
- **MFA para el admin** y vigilancia de intentos (alertas).
- **Desafío anti-bots** (por ejemplo, Cloudflare Turnstile): los límites por red frenan a una persona con un script,
  no a una red de bots con muchas IPs.
- **Verificación del correo** al registrarse (la **recuperación de contraseña** se agregó después, D43): hoy cualquiera puede registrar un correo
  ajeno y hacer que reciba la confirmación de una reserva. No se agregó a último momento porque exigir verificar el
  correo en medio del checkout cambiaría el flujo que pide el PDF (y ese correo puede caer en Spam).
- **Content-Security-Policy** como protección adicional contra XSS.
- **Pago `PROCESSING` + conciliación** para pasarelas reales (D11).

---

## D41 · Límites contra el abuso: intentos de login y retenciones por red

**Contexto.** La revisión externa (D40) reprodujo 25 intentos fallidos seguidos de un login correcto, y tres sesiones
independientes reteniendo fechas a la vez.

**Decisión.**
- **IP real del visitante** (`apps/core/ip.py`): Render está detrás de Cloudflare (se comprobó en las cabeceras de
  producción: `server: cloudflare`, `cf-ray`). Se usa `CF-Connecting-IP`, que Cloudflare fija y sobrescribe si el
  cliente la envía. `X-Forwarded-For` se ignora: cualquiera puede mandarla, y Render solo agrega a ella. Sin proxy
  (local, tests) se usa `REMOTE_ADDR`. Configurable con `CLIENT_IP_HEADER`.
- **Login** con `django-axes`: 5 fallos de una **cuenta desde una red** → pausa de 15 minutos (página propia, HTTP
  429, sin revelar si la cuenta existe). La clave es cuenta + red:
  - si fuera solo la red, una persona bloquearía a toda su oficina;
  - si fuera solo la cuenta, un atacante podría dejar a un huésped sin acceso a su cuenta.

  Un login correcto reinicia la cuenta de fallos. Aplica también al admin.
- **Dos huecos que encontraron los tests** al configurarlo:
  1. `django-axes` buscaba el usuario en el campo `email` (el `USERNAME_FIELD`), pero el formulario lo envía como
     `username`. Los fallos se guardaban sin cuenta y **la contraseña correcta entraba durante el bloqueo**. Se
     corrigió con `AXES_USERNAME_FORM_FIELD`.
  2. `ANA@mail.com` contaba como otra cuenta que `ana@mail.com`: cada forma de escribirlo daba 5 intentos nuevos. Se
     normaliza igual que el login (`AXES_USERNAME_CALLABLE`).
- **Retenciones:** como máximo `BOOKING_MAX_HOLDS_PER_IP` (5) activas por red. Más de una, porque una familia, una
  oficina o una universidad comparten IP.
  - La IP se guarda como **hash con clave** (HMAC con `SECRET_KEY`), nunca en claro, y se borra al pagar la reserva.
  - Las retenciones vencidas o pagadas no cuentan.

**Verificación en producción** (después del despliegue, con un correo inexistente):
- 5 fallos → el 5.º devuelve 429 con la página de pausa.
- Falsificar `X-Forwarded-For`, `True-Client-IP` o `X-Real-IP` no la salta (siguen 429).
- Enviar `CF-Connecting-IP` desde el cliente lo rechaza Cloudflare en su borde (403, error 1000) antes de llegar a la
  aplicación: la única cabecera en la que se confía no se puede falsificar desde fuera.

**Límites.** Frena a una persona con un script, no a una red de bots con muchas IPs: para eso hace falta un desafío
anti-bots. Dos peticiones simultáneas de la misma red podrían superar el límite por una retención; para limitar abuso
es aceptable y no justifica otro bloqueo.

---

## D42 · Segunda revisión: coherencia del flujo y pruebas en navegador

**Contexto.** Una segunda revisión externa, hecha esta vez con el PDF de la prueba, recomendó priorizar el flujo de
reserva sobre funciones nuevas. Encontró dos incoherencias dentro del alcance y la falta de pruebas que ejecuten el
JavaScript.

**Decisión.**
- **Fechas de la búsqueda = fechas de la reserva** (D09): la búsqueda ya no usa la fecha del servidor sino la de la
  ciudad. Tests con `time_machine` reproducen el caso de Madrid y el inverso de Ciudad de México.
- **Salida el día en que empieza otra reserva** (D33): el calendario calcula los días deshabilitados según se esté
  eligiendo la llegada o la salida.
- **Pruebas de navegador** (`e2e/`, Playwright + Chromium contra el `live_server` de Django, job propio en la CI):
  - el flujo completo: buscar, calendario, registro, pago rechazado y reintento, confirmación y correo;
  - inglés en móvil, sin desbordes;
  - retención vencida y vuelta a la propiedad con las mismas fechas;
  - salida el día en que empieza otra reserva.
- **Las pruebas se validan a sí mismas:** con el JavaScript anterior del calendario, la prueba correspondiente falla.
  Una prueba que nunca falla no protege nada.
- **Pago:** el PDF pide "completar el pago" sin indicar una pasarela. El pago simulado con tarjetas de prueba se
  propone como respuesta a ese punto, y se deja planteado a Wynwood House si prefiere una integración real (D11).

**Segunda pasada de la misma revisión.**
- **Calendario del buscador:** el servidor ya validaba con la fecha del destino, pero el calendario seguía tomando
  "hoy" del dispositivo. Pasada la medianoche en Lima, ocultaba una llegada que en Ciudad de México todavía era
  válida. Ahora sigue al destino (D09).
  - La prueba de navegador usa dos ciudades en UTC−12 y UTC+14, que nunca comparten fecha, y un navegador en UTC+14,
    así que reproduce el caso a cualquier hora en que corra la CI.
  - Con el JavaScript anterior, la prueba falla.
  - Detalle encontrado al escribirla: al cambiar el mínimo, flatpickr descarta en silencio las fechas que quedan
    fuera, sin avisar con `onChange`; por eso la llegada se revisa antes de cambiarlo.
- **Instalación de Chromium en Docker:** Playwright guarda los navegadores en la caché de cada usuario. Instalarlo como
  `root` y correr las pruebas como `app` no lo encontraba. El README instala las dependencias del sistema como `root`
  y Chromium como `app`.
- **CI y `DEBUG`:** las pruebas de navegador pasaban en local (`DEBUG=true`) y fallaban en la CI (`DEBUG=false`), que
  redirigía a HTTPS. `SecurityMiddleware` lee el ajuste una vez, al arrancar el servidor de prueba, así que se
  desactiva para toda la sesión antes de arrancarlo.

**Verificado en producción** (noche del 19-oct en Lima, cuando en Madrid ya era el 20), solo con lecturas:
- **Búsqueda:** llegada el 19 rechazada en Madrid y aceptada en Lima; sin ciudad, los resultados no incluyen Madrid
  ni Barcelona.
- **Calendario del buscador** (Chromium con zona horaria UTC+14, donde ya era el 20):
  - en Lima ofrece el 19;
  - al cambiar a Madrid bloquea el 19, deja el 20 y borra la llegada elegida;
  - sin ciudad vuelve a ofrecer el 19.
- **Calendario de la propiedad:** con otra reserva que empieza el 29, llegando el 27 se puede salir el 29; el 30 sigue
  bloqueado.

---

## D43 · Recuperar la contraseña

**Contexto.** Quien olvidaba la contraseña perdía el acceso a sus reservas (D34 la había dejado fuera). Es una
función esperable en cualquier sitio con cuentas, y Django ya trae las piezas seguras: se usan sus vistas y se
cierran los huecos que dejan por defecto.

**Decisión.** Vistas de Django (`PasswordResetView`, `PasswordResetConfirmView`) con formularios y plantillas propios:

| Riesgo | Protección |
|---|---|
| **Saber quién tiene cuenta** (enumeración) | La página responde lo mismo exista o no la cuenta: "si hay una cuenta con ese correo, le enviamos un enlace". Django además atrapa los errores del proveedor de correo, así que un fallo de envío no se convierte en un 500 que delate la cuenta |
| **Inundar el correo de alguien** | Como máximo un correo por cuenta cada 5 minutos (`password_reset_requested_at`). El turno se toma con un `UPDATE` condicional, como el correo de confirmación (D37): dos peticiones simultáneas no envían dos |
| **Envenenar el enlace** (*password reset poisoning*) | El enlace se arma con `SITE_URL`, no con la cabecera `Host`. Si se usara `Host`, un atacante podría pedir el reset de una víctima con `Host: evil.example` y recibir su token cuando ella hiciera clic |
| **Enlace robado o viejo** | Válido 1 hora (`PASSWORD_RESET_TIMEOUT`; Django usa 3 días) y de un solo uso: el token depende del hash de la contraseña, así que cambiarla lo invalida. Django cambia el token de la URL por uno en la sesión antes de mostrar el formulario, para que no se filtre por la cabecera `Referer` |
| **Sesión robada en otro dispositivo** | Al cambiar la contraseña, las demás sesiones dejan de valer (Django guarda el hash de la contraseña en la sesión) |
| **Bloqueado por intentos fallidos** (D41) | Quien abre el enlace demuestra controlar el correo: se borran sus intentos fallidos en **todas** las redes. Iniciar sesión solo borraba los de la red actual (la laptop bloqueada seguía bloqueada si el cambio se hacía desde el celular) |

- **Contraseña nueva:** el mismo campo del registro, con mostrar/ocultar y la lista de requisitos en vivo. El
  formulario incluye el correo de la cuenta (`autocomplete="username"`) para que los gestores de contraseñas la
  guarden bajo la cuenta correcta, y para la regla "no contiene tu nombre ni tu correo".
- **Después:** inicia sesión directamente y vuelve al inicio con un mensaje.
- **Correo:** HTML y texto con el marco del de confirmación, en el idioma de la página desde la que se pidió.

**Pruebas.** 22 tests más una prueba de navegador (desde el login hasta volver a entrar, con el correo). Dos se
comprobaron rompiendo el código a propósito:
- sin el límite de 5 minutos, el test del límite falla;
- sin el desbloqueo explícito, el test del bloqueo fallaba solo si el cambio se hacía desde otra red. La primera
  versión del test usaba la misma red y pasaba igual, porque iniciar sesión ya borra los intentos de esa red. Se
  reescribió con dos redes (laptop y celular).

**Límites.**
- **Tiempo de respuesta:** el envío es sincrónico, así que la respuesta tarda más cuando la cuenta existe (medido en
  local: 275 ms contra 53 ms, solo en el primer pedido; con el límite de 5 minutos activo, 49 contra 48 ms). No revela
  nada nuevo: el registro ya dice "ya existe una cuenta con este correo" (D34). Cerrar la enumeración exigiría cambiar
  los dos, con una cola de correos y verificación del correo al registrarse (mejoras planificadas).
- **Cuentas distintas:** el límite es por cuenta; alguien que conozca muchos correos registrados podría pedir un
  enlace para cada uno. Lo frenaría el desafío anti-bots pendiente (D40).
- **Paginación de "Mis reservas"** (D44): hoy se cargan todas las reservas de la cuenta, sin N+1. Con un historial
  largo convendría paginar las pasadas (mejora planificada).
- **Entrega:** verificado en producción, Gmail entregó el correo unos 7 minutos después de que Brevo lo enviara
  (estado "Enviado" sin "Entregado" mientras tanto). Sale del dominio compartido de Brevo y es un correo de
  "restablecer contraseña" con un enlace a `onrender.com`: justo lo que los filtros contra el phishing miran más. Un
  dominio propio verificado (SPF, DKIM) lo mejoraría (mejora planificada).

**Tercera revisión externa (sobre el commit 9d58c3d).** Cuatro observaciones, todas comprobadas antes de tocar nada:

| Observación | Comprobación | Arreglo |
|---|---|---|
| La CI de `main` fallaba en las pruebas de navegador | Los campos de tarjeta estaban vacíos: la prueba pulsó la tarjeta de prueba antes de que `checkout.js` (diferido) estuviera listo. Reproducido retrasando ese script 2 s | La prueba espera `DOMContentLoaded`, que ocurre después de los scripts diferidos, y comprueba que el número aparezca antes de pagar. Con el script retrasado, pasa |
| Si el proveedor falla, se gastan igual los 5 minutos | Reproducido con un test: proveedor caído, luego de vuelta, segundo pedido → 0 correos. `get_users()` toma el turno antes de enviar y Django atrapa el error | `send_mail` propio: si el envío falla, registra el error y **devuelve el turno** (solo si sigue siendo el suyo, `UPDATE` condicional). La página responde igual |
| "El formulario no permite saber quién tiene cuenta" era demasiado amplio | Cierto: el tiempo de respuesta sí puede revelarlo | Comentarios y documentación dicen ahora "la página no lo dice; el tiempo puede", como riesgo aceptado (ver Límites) |
| No se avisa del cambio de contraseña | Cierto | Correo aparte "Se cambió la contraseña de tu cuenta" (recomendación de OWASP), sin contraseña ni token: solo "Recuperar mi cuenta" (la página para pedir un enlace) y el contacto. Si falla, se registra y nunca deshace el cambio. Con tests |

---

## D44 · "Mis reservas" y menú de cuenta

**Contexto.** Una vez pagada, a una reserva solo se llegaba por el enlace del correo. Un huésped con sesión iniciada
no tenía dónde ver sus estadías, ni cómo volver a una retención que dejó a medias.

**Decisión.** Una página `/bookings/` (`MyBookingsView`), solo con sesión iniciada; sin sesión lleva al login y
vuelve.

| Grupo | Qué incluye | Acción |
|---|---|---|
| Pendientes de pago | Retenciones vigentes de la cuenta, con el tiempo que queda | "Continuar con el pago" (checkout) |
| Próximas estadías | Confirmadas que aún no terminan, **incluida una en curso**; la más cercana primero | "Ver reserva" (dirección exacta) |
| Estadías pasadas | Confirmadas que ya terminaron; la más reciente primero | "Ver reserva" |

- **"Pasada" con la fecha de la ciudad** (D09): una estadía que termina el 10 ya es pasada en Madrid cuando en Lima
  todavía es el 9.
- **Fuera:** retenciones vencidas (aunque su estado todavía no se haya actualizado, D08), canceladas y las de otras
  cuentas. Se reutiliza `Booking.objects.blocking()`: las mismas reglas que deciden qué ocupa fechas.
- **Sin N+1:** propiedad, distrito, ciudad y país con `select_related` y fotos con `prefetch_related`. Un test
  compara las consultas con 1 y con 8 reservas: deben ser las mismas.

**Menú de cuenta (y un bug previo).** Al agregar "Mis reservas" al encabezado, la revisión visual con sesión iniciada
mostró que el encabezado **ya se desbordaba** entre 992 y 1100 px (105 px a 992) solo con el saludo y "Cerrar sesión";
las revisiones anteriores del encabezado se habían hecho sin sesión. Con el enlace nuevo el desborde llegaba hasta
1200 px.
- **Arreglo:** un menú desplegable de Bootstrap ("Hola, Walter ▾" → "Mis reservas", "Cerrar sesión"). Entre 992 y
  1199 px muestra solo el ícono; el saludo sigue disponible para lectores de pantalla.
- **Verificado:** sin desborde en 10 anchos (375 a 1920 px), también con un nombre largo. El menú del móvil mantiene
  la lista.

**Pruebas.**
- 8 tests; dos comprobados rompiendo el código: sin `prefetch_related` y con la fecha del servidor en vez de la de la
  ciudad, sus tests fallan.
- La prueba de navegador del flujo completo termina abriendo "Mis reservas" desde el menú de cuenta.
- axe-core: 0 violaciones en "Mis reservas", el menú abierto y las páginas de D43.

**Revisión de seguridad de D43 y D44** (ataques reales, en local con Mailpit y en producción sin tocar datos):

| Ataque | Resultado |
|---|---|
| Saber si un correo tiene cuenta | Misma respuesta (302 a "Revisa tu correo"); la diferencia de tiempo no agrega nada que el registro no diga ya (D43) |
| 20 pedidos seguidos, con mayúsculas variadas | 1 correo |
| Sin token CSRF (pedir enlace, cerrar sesión) | 403 |
| `Host: evil.example` | 400 en local; en producción no llega a la aplicación (403) |
| `X-Forwarded-Host`, `Forwarded`, `X-Original-Host` | El enlace sigue saliendo de `SITE_URL` |
| Variantes Unicode del correo (`mıke@`, `MİKE@`, `exampIe`, carácter invisible), la clase de CVE-2019-19844 | Ningún correo |
| Correo de 10.000 caracteres, inyección de `Bcc`, SQL, `<script>`, byte nulo | Error de formulario o 400, nunca 500; Cloudflare bloquea el intento de SQL (403) |
| Token de otra cuenta, alterado, truncado, uid basura | "Este enlace ya no es válido" |
| La URL `set-password` en otro navegador | Inválida: el token vive en la sesión de quien abrió el enlace |
| Reusar el enlace (también el que se usó en producción) | Inválido |
| Reservas o checkout de otra cuenta por referencia | 404 |
| Sesión inventada en "Mis reservas" | Al login |

- **Hallazgo arreglado:** "Mis reservas" no enviaba `Cache-Control`. En una computadora compartida, el botón
  "atrás" después de cerrar sesión podía mostrar las reservas de otra persona. Ahora usa `never_cache`
  (`no-store, private`), como la confirmación, con su test.
- **Nota sobre Brevo:** si la cuenta tiene activado el conteo de clics, los enlaces del correo pasan por un redirect de
  Brevo. No agrega exposición, porque Brevo ya ve el correo completo para enviarlo, y anymail no permite desactivarlo
  por mensaje.
