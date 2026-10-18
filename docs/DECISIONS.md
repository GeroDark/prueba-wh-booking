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
| Base de datos | `CheckConstraint(check_out > check_in)` y `ExclusionConstraint` (PostgreSQL) sobre el rango de fechas en `PENDING`/`CONFIRMED` | Garantía final, aunque fallara el código |

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

**Decisión.** El número y el mensaje están en `SiteSettings`. El botón genera
`https://wa.me/<número>?text=<mensaje en el idioma activo>`. Un formulario de contacto queda como extra.

---

## D16 · Imágenes optimizadas al guardar

**Decisión.** `PropertyImage.save()` llama a `optimize_image()` solo cuando el archivo cambia. Ese método:
1. corrige la orientación con `ImageOps.exif_transpose`;
2. reduce con `thumbnail((1200, 1200))`;
3. guarda en WebP con calidad 80.

El mismo camino lo usan el admin y el seed, así que las fotos del diseño también se optimizan.

**Ejemplo.** Un JPG de 4000×3000 y 3,1 MB se guarda como WebP de 1200×900 y unos 150 KB.

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
