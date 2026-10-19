# Plan maestro — WH Booking

Plan de trabajo de la prueba técnica *Fullstack Developer Python* de Wynwood House (WH):
alcance, arquitectura, fases con criterios de aceptación y forma de trabajo.
Las decisiones técnicas y su justificación están en [DECISIONS.md](DECISIONS.md).

- **Entrega:** martes 20 de octubre de 2026, 10:00 (hora de Perú).
- **Repositorio:** https://github.com/GeroDark/prueba-wh-booking
- **Fuentes de verdad:** el PDF del enunciado define el **alcance obligatorio**; el Figma define la **guía visual**.
  Si se contradicen, manda el PDF y la diferencia se documenta en `DECISIONS.md`.

---

## 1. Alcance

### 🟥 Núcleo obligatorio (PDF)

| # | Requisito | Dónde se resuelve |
|---|---|---|
| 1 | Home con buscador (ciudad/distrito, fechas, huéspedes) | Fase 2 |
| 2 | Login y registro manual: email único, contraseña segura | Fase 6 |
| 3 | Resultados de búsqueda según los filtros | Fase 4 |
| 4 | Detalle de la propiedad con formulario de reserva y disponibilidad. Valida: fechas no pasadas, check-in < check-out, sin reservas solapadas | Fase 5 |
| 5 | Checkout de usuario nuevo: registro antes de reservar y pagar | Fase 7 |
| 6 | Vista de confirmación después del pago | Fase 7 |
| 7 | Correo de confirmación (SMTP local o API) | Fase 8 |
| 8 | Imágenes optimizadas automáticamente: WebP, máximo 1200 px | Fase 1 |
| — | Secciones del home: header con logo y selector ES/EN, buscador, destacadas, "Por qué viajar a España", banner de larga estancia con CTA "Contáctanos", footer | Fase 2 |
| — | CBV, querysets, DTL, Bootstrap 3+, JS/CSS para interacciones, componentes reutilizables, diseño adaptable, Acumin + Helvetica | Todas |
| — | README (PostgreSQL **y** SQLite), comando de datos de prueba, repo en GitHub, despliegue, ES/EN | Fases 0, 1, 3 y 9 |

### 🟧 Incluir: el Figma lo muestra y cuesta poco

Distritos por ciudad · tarifa de limpieza · comodidades en el detalle · impuestos por país (modelo) ·
migas de pan · tarjeta de resumen de la reserva como componente · lista de requisitos de la contraseña en vivo ·
datos personales en el registro del checkout (nombre, nacionalidad, teléfono, fecha de nacimiento) ·
aceptación de términos y casilla de boletín · pestaña "Mensual" que lleva al CTA de larga estancia ·
**mapas al estilo Airbnb** (Leaflet + OpenStreetMap, ver D27):
- en los resultados: lista y mapa lado a lado, con marcadores que muestran el precio y se resaltan al pasar sobre la tarjeta;
- en el detalle: zona aproximada antes de reservar;
- en la confirmación: ubicación exacta y botón "Abrir en Google Maps".

### 🟨 Extras, solo si el núcleo y el 🟧 están cerrados (en este orden)

1. Servicios adicionales simples (agregar/quitar, precio fijo) como líneas de la reserva.
2. Filtros de rango de precio y comodidades.
3. Datos de facturación en el pago.
4. Carrusel de destinos, barra de promoción con cuenta regresiva y banners de eventos, inversión y Casa Wynwood.
5. Cron para `expire_holds` y límite de intentos en el login.
6. Buscar al mover el mapa ("buscar en esta zona").

### ⬜ Fuera de alcance (documentado)

Wynwood Points · códigos de descuento · Apple Pay / Google Pay · pago en cuotas ·
formularios propios de transporte y early check-in · idioma italiano · logos de prensa.

---

## 2. Stack

| Capa | Elección |
|---|---|
| Lenguaje y framework | Python 3.13 (imagen Docker) · Django 5.2 LTS |
| Base de datos | PostgreSQL 17 (principal) · SQLite (alternativa documentada) |
| Frontend | DTL · Bootstrap 5.3 (incluido en `static/vendor`, sin Node) · JS vanilla · flatpickr · Leaflet |
| Contenido bilingüe | `django-modeltranslation` (columnas `_es` / `_en`) |
| Imágenes | Pillow → WebP, lado mayor ≤ 1200 px |
| Email | `django-anymail` (Brevo en producción) · Mailpit en local |
| Estáticos y servidor | WhiteNoise · gunicorn |
| Configuración | `django-environ`: todo por variables de entorno |
| Calidad | pytest + pytest-django + factory_boy + time-machine + pytest-cov · ruff · GitHub Actions |
| Capturas para revisión visual | Playwright (herramienta de desarrollo; no va en las dependencias de la app) |

---

## 3. Arquitectura

### 3.1 Estructura

```
config/                    settings (por variables de entorno), urls (i18n_patterns), wsgi
apps/
  core/                    contenido del sitio: SiteSettings, HomePage, Banner, FeatureSection/Item,
                           ContactChannel, SocialLink, FooterLinkGroup/Link; context processor; /health/
  accounts/                User (email como login), formularios, vistas de auth, validadores
  core/ (además)           fields.py (OptimizedImageField) · images.py (optimizador WebP) · constants.py (íconos y banderas)
                           seeding/ (datos y cargador de seed_data) · management/commands/seed_data.py
  properties/              Country, City, District, Amenity, Property, PropertyImage, Tax
                           querysets.py · pricing.py
  bookings/                Booking, BookingLine, Payment
                           services.py (hold_dates, release_hold, pay_booking, expire_holds)
                           payments.py (PaymentGateway, SimulatedGateway) · emails.py
templates/                 base.html, components/, pages/, emails/
static/                    css/ (tokens + un archivo por componente), js/, img/, fonts/, vendor/
seed/images/               fotos del Figma, que el seed pasa por el optimizador
docs/                      PLAN_MAESTRO.md, DECISIONS.md
```

### 3.2 Modelos (`*` = campo traducido ES/EN)

**core**
- `SiteSettings` (singleton): email de contacto, número de WhatsApp para el CTA, mensaje del CTA*, enlaces a las tiendas de apps.
- `HomePage` (singleton): título* y subtítulo* del hero, imagen del hero, título* de destinos, título* y texto* de destacadas.
- `Banner`: `key` (por ejemplo `long-stay`), título*, texto*, imagen, `layout` (imagen a la izquierda, a la derecha o de fondo),
  texto del botón*, acción del botón (enlace o WhatsApp de `SiteSettings`), URL, orden, activo.
- `FeatureSection` + `FeatureItem`: secciones con cuadrícula de ítems con imagen. Se usa para "Servicios en WH" y para "Por qué viajar a España".
- `MenuGroup` + `MenuLink`: el menú del header y las columnas del footer (un solo par de modelos con `placement`).
- `ContactChannel` (WhatsApp, teléfono, email; bandera; orden; genera su enlace `wa.me` / `tel:` / `mailto:`) · `SocialLink`.

**properties**
- `Country` (nombre*, código ISO, imagen) → `City` (nombre*, slug, **zona horaria**, imagen) → `District` (nombre*, slug).
- `Amenity` (nombre*, ícono, orden).
- `Property`: título*, slug, descripción*, distrito, dirección, latitud y longitud, `max_guests`, dormitorios, camas, baños,
  `price_per_night`, `cleaning_fee` (Decimal), `is_featured`, `is_active`, comodidades (M2M), fechas de creación y actualización.
- `PropertyImage`: propiedad, imagen (se optimiza al guardar), texto alternativo*, orden.
- `Tax`: país, nombre*, porcentaje, activo.

**bookings** (se crean en la Fase 5, junto con el servicio de reservas y sus tests)
- `Booking`: `reference` (código aleatorio, no secuencial), propiedad (PROTECT), `guest` (nulo hasta el checkout),
  `hold_token`, `status` (`PENDING`, `CONFIRMED`, `EXPIRED`, `CANCELLED`), `check_in`, `check_out`, `guests`, `expires_at`,
  `subtotal`, `total`, moneda, idioma, fechas de creación y confirmación.
  - Restricciones: `check_out > check_in`, `guests >= 1` y, solo en PostgreSQL, `ExclusionConstraint` sobre el rango de fechas para `PENDING` y `CONFIRMED`.
- `BookingLine`: líneas guardadas en el momento de la reserva (noches, limpieza, impuestos y, si se hacen, servicios), con etiqueta* y monto.
- `Payment`: reserva, `idempotency_key` (única), monto, moneda, `status` (`PENDING`, `SUCCEEDED`, `FAILED`), proveedor,
  referencia del proveedor, marca y últimos 4 dígitos de la tarjeta, motivo del rechazo.
  - Restricción: solo un `SUCCEEDED` por reserva.

**accounts**
- `User(AbstractUser)` sin `username`: `email` único sin distinguir mayúsculas (`UniqueConstraint(Lower("email"))`),
  nombre completo, nacionalidad, prefijo y número de teléfono, fecha de nacimiento, idioma preferido, `marketing_opt_in`.

### 3.3 Reglas de negocio

- **Solapamiento:** intervalo semiabierto `[check_in, check_out)`. Dos reservas chocan si `A.in < B.out` y `A.out > B.in`.
- **"Fecha en el pasado":** se compara con la fecha local de la ciudad de la propiedad (`City.timezone`).
- **Retención temporal:** al pulsar "Reservar" se crea una reserva `PENDING` con `expires_at = ahora + BOOKING_HOLD_MINUTES` (15 por defecto).
  - Una retención vencida no bloquea fechas: la expiración es perezosa y no requiere un proceso en segundo plano.
  - Hay una sola retención activa por sesión.
- **Precio:** lo calcula el servidor (`pricing.py`): noches × precio + limpieza + impuestos del país.
  Se usa `Decimal` con redondeo `ROUND_HALF_UP` y queda guardado en `BookingLine`.
- **Pago:** `pay_booking()` bloquea la reserva (`select_for_update`) y luego:
  1. devuelve el resultado guardado si la clave de idempotencia ya existe;
  2. no cobra si la reserva no está `PENDING` o si venció;
  3. cobra mediante el gateway;
  4. confirma y envía el email con `transaction.on_commit`.

### 3.4 Rutas y vistas (todas CBV)

| URL (bajo `/es/` o `/en/`) | Vista | Tipo |
|---|---|---|
| `/` | `HomeView` | TemplateView |
| `/search/` | `PropertySearchView` | ListView + formulario por GET |
| `/properties/<slug>/` | `PropertyDetailView` | DetailView |
| `/properties/<slug>/hold/` | `CreateHoldView` | FormView (POST) |
| `/checkout/<reference>/` | `CheckoutAccountView` (registro y datos; se salta si hay sesión) | FormView |
| `/checkout/<reference>/payment/` | `CheckoutPaymentView` | FormView |
| `/bookings/<reference>/` | `BookingConfirmationView` | LoginRequiredMixin + DetailView |
| `/accounts/login/` · `signup/` · `logout/` | Login, registro y logout | Vistas de auth + CreateView |
| `/i18n/setlang/` · `/health/` · `/<ADMIN_URL>/` | Cambio de idioma · health check · admin | — |

### 3.5 Componentes de plantilla

`components/`: `header`, `footer`, `search_bar` (home, resultados y footer), `property_card` (destacadas y resultados),
`booking_summary` (checkout y confirmación), `feature_grid` (servicios y España), `banner` (larga estancia y extras),
`breadcrumb`, `form_field` (Bootstrap + errores + `aria-describedby`), `pagination`, `messages`, `hold_countdown`.

El CSS sigue la misma división: `static/css/tokens.css` + un archivo por componente.
El JS es vanilla, con un archivo por comportamiento: `date-range.js`, `guests-stepper.js`, `hold-countdown.js`,
`password-checklist.js`, `prevent-double-submit.js` y `district-select.js`.

---

## 4. Sistema visual (extraído del Figma)

| Token | Valor |
|---|---|
| `--wh-black` | `#232324` |
| `--wh-gray` | `#979797` |
| `--wh-gray-light` | `#D9D9D9` |
| `--wh-blue` | `#C9E5EA` (footer y barra de promoción) |
| `--wh-yellow` | `#FEAC00` (eventos) |
| `--wh-shadow` | `0 0 17px rgba(0,0,0,.07)` |
| Fuente display | Acumin Pro ExtraCondensed Bold, en mayúsculas: 112 (hero), 66, 55, 45 y 40 px |
| Fuente de texto | Helvetica Neue Roman 16 px; subtítulos en mayúsculas con `letter-spacing: .24em` |
| Botones | Pastilla negra, texto blanco en mayúsculas |

El Figma usa pesos 500 y 700 de Helvetica, además de Inter, Arial y Roboto en algunos frames.
Se normaliza todo a Helvetica Neue Roman, la única disponible (ver DECISIONS).

### Diseño adaptable

El Figma solo tiene diseños a 1440 px; el resto lo definimos nosotros.

| Ancho | Dispositivo de referencia | Comportamiento principal |
|---|---|---|
| 375 | Móvil | Menú hamburguesa, buscador apilado, 1 columna, resumen del checkout arriba y plegable |
| 768 | Tablet | 2 columnas de tarjetas, buscador en 2 filas |
| 1024 | Tablet horizontal / laptop pequeña | Detalle con formulario de reserva fijo al hacer scroll |
| 1366 | Laptop común | Diseño de escritorio |
| 1440 | Diseño Figma | Referencia de fidelidad |
| 1920 / 2560 | Monitores FHD / QHD | Contenido limitado a un ancho máximo; hero e imágenes a ancho completo; tipografía fluida con `clamp()` |

Las capturas de revisión se toman en **375, 768, 1366, 1440 y 1920**.

### Referencias del Figma (archivo `rTqkpmKEpESL6XPvTXGJc2`)

| Pantalla | Nodo |
|---|---|
| Home | `1:1488` |
| Resultados | `1:3569` |
| Detalle (vacío / con fechas) | `1:8372` / `1:8868` |
| Registro (vacío / error / éxito) | `1:18325` / `1:18869` / `1:19427` |
| Servicios adicionales | `1:12948` |
| Pago (tarjeta completa) | `1:15602` |
| Confirmación | `1:18179` |
| Correo | `1:26021` |

---

## 5. Fases

Cada fase se trabaja en su rama (`fase-N-nombre`) y se cierra con un pull request que incluye:
1. capturas en los anchos de referencia junto al frame del Figma;
2. la CI en verde;
3. el checklist de abajo completo.

No se empieza la siguiente fase hasta aprobar la anterior.

### Fase 0 — Cimientos
- Docker Compose (web, db, mailpit), `.env.example`, configuración por entorno, `User` propio.
- i18n (`LocaleMiddleware`, `i18n_patterns`, ES/EN), `base.html` con tokens y fuentes, header y footer vacíos, `/health/`.
- ruff, pytest y workflow de CI.
- [ ] `docker compose up` sirve una página con la tipografía y los colores de WH.
- [ ] El selector ES/EN cambia la URL (`/es/` ↔ `/en/`) y los textos.
- [ ] El admin abre y se puede entrar con email.
- [ ] CI en verde (ruff + pytest + `makemigrations --check` + `check --deploy`).

### Fase 1 — Datos
- Modelos de contenido (`core`) y de catálogo (`properties`) con traducciones y su admin (inlines, filtros, búsqueda).
  Los modelos de reservas y pagos pasan a la Fase 5, donde se construyen junto con su servicio y sus tests.
- Optimizador WebP; imágenes exportadas del Figma a `seed/images/`.
- `seed_data` (repetible sin duplicar; con `--flush`, `--properties N` y `--skip-images`) y usuario de demo.
  Las reservas de ejemplo se agregan al seed en la Fase 5.
- [x] El admin muestra propiedades, ciudades, distritos y contenido del home en ES y EN.
- [x] Las imágenes guardadas son `.webp` y miden 1200 px o menos.
- [x] Tests: optimizador, seed repetible, restricciones de modelos y email único.

### Fase 2 — Home
- Header (logo, navegación, ES/EN; el acceso llega en la Fase 6), hero con buscador, destacadas, "Por qué viajar a España"
  (`feature_grid`), banner de larga estancia (CTA a WhatsApp), footer completo; diseño adaptable y animaciones
  (hover, aparición al hacer scroll, scroll suave).
- Se suman, porque los datos ya existían: carrusel de destinos, servicios y los banners de eventos y real estate.
- `SearchForm` compartido (hero, footer y resultados) y rutas provisionales de resultados y detalle,
  que se completan en las fases 4 y 5.
- [x] Coincide con el Figma a 1440 px y se ve bien en 375, 768, 1366 y 1920.
- [x] Un cambio de texto en el admin se refleja en el home, en ambos idiomas.
- [x] Tests: consulta de destacadas, contenido desde modelos, número de consultas acotado.

### Fase 3 — Primer despliegue
- Render (Docker) + Neon (PostgreSQL) + Cloudinary (media) + Brevo (email); el script de arranque migra, ejecuta el seed si la base está vacía y crea el superusuario.
- Despliegue automático en cada push a `main`; UptimeRobot para evitar que el servicio se duerma.
- [x] Preparado y probado en local con la imagen de producción sobre una base vacía: migra, crea el admin, carga el
  seed una sola vez (un reinicio conserva las ediciones), sirve estáticos con hash y bloquea comandos destructivos.
- [x] Protección de datos (D38): CI frena migraciones que pueden perder datos; `flush` bloqueado en producción.
- [ ] El home funciona en la URL pública con HTTPS, en ES y EN.
- [ ] `/health/` responde 200.
- [ ] Un correo de confirmación llega a una bandeja real y una foto subida desde el admin sobrevive a un redeploy.

### Fase 4 — Búsqueda
- `PropertyQuerySet.search()`: país, ciudad, distrito, huéspedes y disponibilidad (`available()` excluye propiedades
  con una reserva confirmada o una retención vigente que se solape).
- **Se adelanta el modelo `Booking`** (campos, estados, restricciones y consultas `blocking()` / `overlapping()`),
  porque filtrar por fechas lo necesita. El servicio de reservas sigue en la Fase 5. El seed agrega 4 reservas de
  demo con fechas relativas a hoy, y `--flush` se niega a correr si hay reservas reales.
- Resultados con `property_card` (variante `stacked`), paginación que conserva los filtros (`{% querystring %}`),
  resumen de filtros y estado vacío con salidas. Un filtro inválido muestra su error sin anular los demás.
- **Mapa de resultados** (como en el Figma): lista a la izquierda y mapa fijo a la derecha.
  - Un marcador por propiedad con su precio; los cercanos se agrupan con su cantidad (Leaflet.markercluster).
  - Pasar el mouse sobre una tarjeta resalta su marcador (o su grupo); un clic muestra una mini tarjeta.
  - En móvil y tablet, botón "Mostrar mapa / Mostrar lista".
- [x] Una búsqueda desde el home lleva a resultados coherentes con los filtros.
- [x] El mapa muestra exactamente las propiedades de la página de resultados.
- [x] Una búsqueda sin coincidencias muestra un estado vacío útil.
- [x] Tests: cada filtro por separado y la exclusión de propiedades ocupadas.

### Fase 5 — Detalle y motor de reservas
- Galería, información, comodidades, sección "Ubicación" con mapa de la zona aproximada (como Airbnb), tarjeta de
  reserva con pestañas Diario y Mensual (estadías largas por WhatsApp), calendario con fechas ocupadas deshabilitadas
  y barra fija "Reservar" en móvil.
- Desglose de precio calculado en el servidor (`pricing.quote_stay`), en vivo por `GET /properties/<slug>/quote/`.
- `services.hold_dates()` con bloqueo de la propiedad, expiración perezosa y una retención por visitante;
  `ExclusionConstraint` en PostgreSQL; `BookingLine` congela el desglose en ES y EN.
- Checkout provisional con resumen, cuenta regresiva y "Cambiar fechas" (libera la retención). El registro y el pago
  llegan en la Fase 7.
- [x] El calendario no deja elegir fechas ocupadas ni pasadas.
- [x] "Reservar" crea la retención y muestra el contador.
- [x] Tests: los 6 casos de solapamiento, fechas pasadas según la zona horaria, capacidad, expiración, una retención por sesión y **concurrencia real con dos hilos**.

### Fase 6 — Cuentas
- Registro (`SignUpView`, `CreateView`), login con email (`LoginView` de Django con un formulario propio) y logout
  solo por POST. Al registrarse, la sesión se inicia sola y vuelve a la página de origen (`next` validado).
- Contraseña: validadores de Django + "número o símbolo" + "no contiene tu nombre ni tu correo", con la lista de
  requisitos en vivo del Figma y botón para mostrar u ocultar.
- Header con "Iniciar sesión" o "Hola, Ana · Cerrar sesión"; en móvil, dentro del menú lateral. Mensajes globales.
- Componentes `form_field` y `password_field`, accesibles (`aria-describedby`, `aria-invalid`).
- [x] Los estados vacío, con error y con éxito coinciden con los frames de registro.
- [x] Tests: email duplicado sin distinguir mayúsculas, contraseñas débiles, `next` seguro.

### Fase 7 — Checkout, pago y confirmación
- Paso 1: registro dentro del checkout y datos personales (se salta si hay sesión; enlace "Iniciar sesión" que vuelve al checkout).
- Paso 2: tarjeta simulada (`4242…` aprueba, `4000 0000 0000 0002` rechaza), idempotencia, bloqueo del doble envío.
- Confirmación protegida (solo el dueño), con la dirección exacta, su mapa y "Abrir en Google Maps"; aviso y vuelta
  al detalle si la retención venció.
- [x] El flujo completo funciona de punta a punta, como usuario nuevo y como usuario con sesión.
- [x] Tests: misma clave = un cobro; dos pestañas = un cobro; rechazo y reintento; pago vencido; otro usuario recibe 404.

### Fase 8 — Correo de confirmación
- Plantilla HTML + texto según el frame del correo, en el idioma de la reserva, enviada con `on_commit`.
- [x] Se ve bien en Mailpit (local): 375 y 700 px; el chequeo de Mailpit deja solo 0,46 % sin soporte.
- [ ] Llega a una bandeja real (producción, con el despliegue de la Fase 3).
- [x] Tests: un solo envío, idioma correcto, contenido de la reserva, fallo del proveedor y reintento.

### Fase 9 — Cierre
- Repaso de traducciones (`makemessages` / `compilemessages`), accesibilidad (etiquetas, foco, contraste, `alt`), diseño adaptable en todos los anchos.
- Páginas 404 y 500 bilingües; configuración de seguridad de producción.
- README completo (Docker, PostgreSQL, SQLite, seed, tests, despliegue, cuentas de demo, tarjetas de prueba) y `DECISIONS.md` final.
- [ ] Recorrido completo en producción, en ES y EN, en escritorio y móvil.
- [ ] Toda la suite en verde.

### Fase 10 — Extras
Lista 🟨 en orden. Cada extra se cierra con la misma revisión visual y su propio test.

---

## 6. Calendario

| Bloque | Fases |
|---|---|
| Sábado 17, noche | 0 y 1 |
| Domingo 18 | 2, 3, 4 y 5 |
| Lunes 19 | 6, 7, 8 y 9 |
| Lunes 19, noche | Margen de seguridad y QA en producción |
| Martes 20, antes de las 09:00 | Solo correcciones y entrega |

**Regla de recorte:** si el domingo por la noche las fases 0 a 5 no están cerradas, se recortan extras, nunca requisitos del núcleo.

---

## 7. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| El servicio gratuito de Render se duerme (~50 s en la primera carga) | Ping de UptimeRobot cada 10 min; avisarlo en el README |
| El disco de Render es efímero | Media en Cloudinary; seed solo si la base está vacía |
| Solo existe Helvetica en peso 400 | Normalización documentada; negrita generada por el navegador solo en totales |
| No hay diseños para móvil | Matriz de anchos definida (sección 4) y capturas en cada fase |
| gettext no está en Windows | Las traducciones se compilan dentro de Docker; los `.mo` también se versionan |
| Fuentes y fotos propietarias en un repo público | Aviso en el README: provistas por WH solo para evaluación |
| Falta de tiempo | Regla de recorte (sección 6) |
