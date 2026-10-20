# WH Booking

Flujo de reserva de propiedades para **Wynwood House**, desarrollado como prueba técnica *Fullstack Developer Python*:
home con buscador, resultados con mapa, detalle con disponibilidad, registro, checkout con pago simulado, confirmación
y correo, en español e inglés.

**Sitio en vivo: https://wh-booking.onrender.com**

> El plan gratuito de Render apaga el servicio tras un rato sin visitas; si la primera carga tarda cerca de un minuto,
> es eso. Un monitor externo lo mantiene despierto.

## Revisión en 5 minutos

1. **Buscar:** en el home, elige *Bogotá* y unas fechas. Los resultados muestran la lista y el mapa con precios.
2. **Detalle:** abre una propiedad. El calendario bloquea días pasados y noches ocupadas, y el precio (noches,
   limpieza, impuestos del país) se calcula en el servidor al cambiar fechas o huéspedes.
3. **Reservar:** las fechas quedan retenidas 15 minutos y se abre el checkout.
4. **Registrarse en el checkout** con un correo real (llega la confirmación) y pagar con la tarjeta de prueba
   `4242 4242 4242 4242`, vencimiento futuro, CVC `123`.
5. **Confirmación:** dirección exacta, mapa con el punto y "Abrir en Google Maps". El correo llega en el idioma en que
   se reservó (revisa Spam: el remitente de la demo es un Gmail).
6. **Cambiar de idioma** (EN / ES, arriba a la derecha) en cualquier página.

| Cuenta o dato de prueba | Valor |
|---|---|
| Huésped con perfil completo (pasa directo al pago) | `demo@wynwoodhouse.test` / `Wynwood-Demo-2026` (su correo no existe: para ver el correo de confirmación, regístrate con uno real) |
| Tarjetas aprobadas | `4242 4242 4242 4242` (Visa), `5555 5555 5555 4444` (Mastercard), `3782 822463 10005` (Amex) |
| Tarjeta rechazada / sin fondos | `4000 0000 0000 0002` / `4000 0000 0000 9995` |

No se cobra nada ni se guardan datos de tarjeta: el pago es simulado y solo acepta tarjetas de prueba.

## Requisitos de la prueba y dónde se cumplen

| Requisito | Dónde |
|---|---|
| Home con buscador | `apps/core` (`HomeView`), componente `search_bar` (país, ciudad, distrito, fechas, huéspedes) |
| Login y registro manual (emails únicos, contraseñas seguras) | `apps/accounts`: email único sin distinguir mayúsculas (también en la base), validadores de contraseña con lista en vivo |
| Resultados de búsqueda | `PropertySearchView` + `PropertyQuerySet.search()` / `available()` |
| Detalle con formulario de reserva: sin fechas pasadas, entrada antes que salida, sin reservas duplicadas | `apps/bookings/services.py` (`validate_stay`, `hold_dates`), bloqueo de fila y restricción de exclusión en PostgreSQL (D06–D09) |
| Checkout de usuario nuevo (registro + pago) | `CheckoutView`: registro con datos personales y pago simulado idempotente (`apps/payments`, D11–D12) |
| Vista de confirmación | `BookingConfirmationView` (solo el huésped; ubicación exacta) |
| Correo de confirmación (SMTP local o API) | `apps/bookings/emails.py`: Mailpit (SMTP) en local, Brevo (API) en producción (D37) |
| Imágenes a WebP, máximo 1200 px | `OptimizedImageField` (`apps/core/fields.py`), al subir desde el admin o el seed |
| Comando de datos de prueba | `python manage.py seed_data` |
| Django + PostgreSQL o SQLite, DTL, Bootstrap, JS, CBV, nada hardcodeado | Contenido editable desde el admin (textos, banners, menús, contactos, impuestos, enlaces legales) |
| Bilingüe ES/EN | `i18n_patterns` (`/es/`, `/en/`) + `django-modeltranslation` para el contenido (D13) |

Calidad: **467 tests** (pytest) más **pruebas de navegador** (Playwright, en `e2e/`) que recorren el flujo completo
ejecutando el JavaScript real. Las pruebas de navegador cubren:
- buscar, elegir fechas en el calendario, registrarse, pago rechazado y reintento, confirmación y correo;
- inglés en móvil;
- retención vencida;
- salida el día que empieza otra reserva.

La CI en GitHub Actions corre con PostgreSQL y SQLite, más ruff y `check --deploy`. Hay pruebas de concurrencia con
hilos reales, y la accesibilidad WCAG 2.1 AA está verificada con axe-core. Las decisiones técnicas, con
ejemplos, están en [docs/DECISIONS.md](docs/DECISIONS.md), incluidas las correcciones de una revisión externa y los
límites reconocidos antes de operar con dinero real (D40). El plan por fases está en
[docs/PLAN_MAESTRO.md](docs/PLAN_MAESTRO.md).

## Estado

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Docker, PostgreSQL, configuración, usuario con email, ES/EN, CI | ✅ |
| 1 | Modelos de contenido y catálogo, admin bilingüe, imágenes WebP, `seed_data` | ✅ |
| 2 | Home: buscador, destinos, destacadas, servicios, "¿Por qué viajar a España?", banners, header y footer | ✅ |
| 3 | Despliegue en Render + Neon + Cloudinary + Brevo, protección de datos de producción | ✅ |
| 4 | Resultados: filtros por ubicación, fechas y huéspedes; mapa con precios y agrupamiento | ✅ |
| 5 | Detalle de la propiedad: galería, calendario de disponibilidad, precio en vivo y retención de fechas | ✅ |
| 6 | Registro y login con email, contraseñas seguras con requisitos en vivo, logout seguro | ✅ |
| 7 | Checkout: registro con datos personales, pago simulado idempotente y confirmación con la ubicación exacta | ✅ |
| 8 | Correo de confirmación HTML + texto en el idioma de la reserva (Mailpit en local, Brevo en producción) | ✅ |
| 9 | Cierre: accesibilidad, traducciones, revisión en producción, documentación | ✅ |

## Stack

Python 3.13 · Django 5.2 LTS · PostgreSQL 17 · Bootstrap 5.3 · JavaScript vanilla · Docker · pytest · GitHub Actions

## Inicio rápido (Docker, recomendado)

Requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/) en ejecución.

```bash
git clone https://github.com/GeroDark/prueba-wh-booking.git
cd prueba-wh-booking
docker compose up --build
```

No hace falta configurar nada: `docker-compose.yml` define valores de desarrollo y el contenedor espera
a PostgreSQL y aplica las migraciones al arrancar.

| Servicio | URL |
|---|---|
| Sitio | http://localhost:8000 (redirige a `/es/`) |
| Admin | http://localhost:8000/es/admin/ |
| Bandeja de correo local (Mailpit) | http://localhost:8025 |
| Health check | http://localhost:8000/health/ |

Cargar los datos de prueba y crear un usuario administrador:

```bash
docker compose exec web python manage.py seed_data
docker compose exec web python manage.py createsuperuser
```

> ¿El puerto 8000 u 8025 está ocupado? Usa otros: `WEB_PORT=8001 MAILPIT_PORT=8026 docker compose up`
> (en PowerShell: `$env:WEB_PORT=8001; $env:MAILPIT_PORT=8026; docker compose up`).

## Datos de prueba

`python manage.py seed_data` carga contenido bilingüe (ES/EN) listo para probar el flujo:

- **Catálogo:** 5 países, 7 ciudades con su zona horaria, 19 distritos, 13 comodidades, impuestos por país
  y 12 propiedades (6 destacadas) con sus fotos.
- **Sitio:** textos del home, "Servicios en Wynwood House", "¿Por qué viajar a España?", banners
  (larga estancia, eventos, real estate), menús, canales de contacto y redes sociales.
- **Huésped de demo:** `demo@wynwoodhouse.test` / `Wynwood-Demo-2026` (inicia sesión en `/es/accounts/login/`).
  Tiene el perfil completo, así que en el checkout pasa directo al pago.
- **Reservas de demo:** 4 estadías confirmadas con fechas relativas al día en que se ejecuta el comando
  (por ejemplo, el dúplex de Parque Virrey queda ocupado de hoy + 3 a hoy + 8 días). Busca esas fechas y
  la propiedad desaparece de los resultados.

Las fotos pasan por el mismo optimizador que el admin: se guardan como WebP de 1200 px o menos.
El comando se puede ejecutar varias veces sin duplicar nada.

| Opción | Efecto |
|---|---|
| `--flush` | Borra primero el contenido sembrado y las reservas de demo (no toca a los usuarios). Se niega a correr si hay reservas reales |
| `--properties N` | Carga solo las primeras N propiedades |
| `--skip-images` | No adjunta fotos (más rápido) |

Los textos y las fotos salen del diseño de Figma de la prueba. Los datos de contacto y los impuestos son ilustrativos.
El origen y la licencia de cada imagen están en [seed/images/CREDITS.md](seed/images/CREDITS.md).

## Probar una reserva

1. Abre una propiedad (por ejemplo http://localhost:8000/es/properties/modern-duplex-parque-virrey/).
   En el calendario, las noches ocupadas por las reservas de demo y los días pasados están deshabilitados.
2. Elige fechas y huéspedes: el desglose (noches, limpieza, impuestos del país) se calcula en el servidor.
3. "Reservar ahora" retiene las fechas durante `BOOKING_HOLD_MINUTES` minutos (15) y abre el checkout con una
   cuenta regresiva. Mientras tanto, nadie más puede reservarlas. "Cambiar fechas" las libera al instante.
4. **Paso 1, registro:** correo, contraseña, nombre y apellido, nacionalidad, teléfono (validado para el país) y fecha
   de nacimiento (mayor de 18). El boletín es opcional y se activa solo si se marca la casilla. Con sesión iniciada y el perfil completo, este paso se salta; "Iniciar sesión" vuelve
   al mismo checkout.
5. **Paso 2, pago simulado.** No se cobra nada ni se guardan datos de tarjeta (solo marca y últimos 4 dígitos).
   Las tarjetas de prueba aparecen en la página y se completan con un clic:

   | Tarjeta | Resultado |
   |---|---|
   | `4242 4242 4242 4242` (Visa), `5555 5555 5555 4444` (Mastercard), `3782 822463 10005` (Amex) | Aprobada |
   | `4000 0000 0000 0002` | Rechazada |
   | `4000 0000 0000 9995` | Fondos insuficientes |
   | Cualquier otra tarjeta | No se envía: el navegador la detiene con un aviso de demo (sin JavaScript, la rechaza el servidor) |

   Vencimiento: cualquier fecha futura. Código de seguridad: 3 dígitos (4 en American Express).
6. **Confirmación** (`/es/bookings/<referencia>/`): solo la ve quien reservó. Muestra la dirección exacta, el mapa con
   el punto preciso y "Abrir en Google Maps".

Un doble clic, recargar la página o pagar desde dos pestañas a la vez no genera un segundo cobro: clave de
idempotencia, bloqueo de la reserva y una restricción en la base, probados con dos hilos simultáneos. El límite
conocido, que es qué pasa si una pasarela real cobra y su respuesta se pierde, está explicado en D11.

7. **Correo de confirmación:** se envía al confirmarse el pago, en el idioma en que se reservó.
   En local llega a Mailpit (http://localhost:8025), que también muestra la versión de texto y un chequeo de
   compatibilidad con clientes de correo.

## Correo

| Entorno | Cómo se envía | Configuración |
|---|---|---|
| Docker (local) | SMTP a Mailpit | Ya viene en `docker-compose.yml` (`EMAIL_URL=smtp://mailpit:1025`) |
| Sin Docker | Se imprime en la consola | `EMAIL_URL=consolemail://` |
| Producción | API HTTP de Brevo (`django-anymail`) | `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL` (remitente verificado en Brevo) y `SITE_URL` |

Se usa la API y no SMTP porque los planes gratuitos de hosting suelen bloquear los puertos SMTP. Si el proveedor
falla, el pago no se ve afectado y el correo queda pendiente:
`python manage.py send_booking_confirmations` envía los pendientes y retoma los que quedaron a medias si el proceso
murió, y en el admin la acción "Reenviar el correo de confirmación" lo vuelve a mandar a pedido del huésped. La
entrega es "al menos una vez": si el proceso muere justo después de que el proveedor aceptó el correo, puede llegar
una copia repetida, lo que es preferible a que el huésped no reciba la confirmación (D37).

Reglas que valida el servidor: llegada no pasada (según la zona horaria de la ciudad), salida posterior a la llegada,
capacidad de la propiedad, hasta 30 noches en línea y sin solapamiento con otra reserva o retención vigente,
también ante dos reservas simultáneas (ver D06 a D09 en [docs/DECISIONS.md](docs/DECISIONS.md)).

## Comandos útiles

```bash
docker compose exec web pytest                       # tests
# pruebas de navegador (una vez: instalar Chromium; en CI corren solas)
docker compose exec -u root web python -m playwright install --with-deps chromium
docker compose exec web pytest -m e2e
docker compose exec web python manage.py expire_holds # marca como vencidas las retenciones caducadas (opcional, p. ej. con cron)
docker compose exec web python manage.py send_booking_confirmations # envía los correos de confirmación pendientes
docker compose exec web ruff check . && docker compose exec web ruff format .
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py makemessages -l es --ignore=.venv --ignore=staticfiles --no-obsolete
docker compose exec web python manage.py compilemessages --ignore=.venv
```

`makemessages` está personalizado para no generar traducciones aproximadas (*fuzzy*), que Django ignoraría en silencio.

## Base de datos

### PostgreSQL (entorno soportado)

Es la opción por defecto en Docker. Para usar otro servidor, define `DATABASE_URL`:

```
DATABASE_URL=postgres://usuario:clave@host:5432/base
```

### SQLite (alternativa sin Docker)

Útil para una revisión rápida. Requiere Python 3.13:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # luego edita: DEBUG=true y DATABASE_URL=sqlite:///db.sqlite3
python manage.py migrate
python manage.py runserver
```

SQLite no tiene bloqueo de filas: el proyecto lo configura con transacciones `IMMEDIATE`, que hacen esperar a la
segunda de dos reservas simultáneas (probado con hilos). La restricción de exclusión de fechas en la base es
exclusiva de PostgreSQL (ver D02 y D07 en las decisiones). CI corre toda la suite con las dos bases.

## Configuración

Toda la configuración se lee de variables de entorno. [.env.example](.env.example) lista cada una con su propósito.

## Despliegue (Render + Neon + Cloudinary + Brevo)

Todo en planes gratuitos. [render.yaml](render.yaml) describe el servicio, así que el despliegue es:

1. Crear la base en **Neon** (AWS us-east-1) y copiar la conexión **directa** (`postgresql://…sslmode=require`).
2. En **Render**: *New → Blueprint* → este repositorio. Render pide los secretos marcados `sync: false`:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | La conexión de Neon |
   | `CLOUDINARY_URL` | `cloudinary://API_KEY:API_SECRET@CLOUD_NAME` (fotos subidas desde el admin) |
   | `BREVO_API_KEY` | Clave de la API de Brevo |
   | `DEFAULT_FROM_EMAIL` | `Wynwood House <remitente-verificado-en-brevo@…>` |
   | `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` | Cuenta del admin, creada al arrancar |

3. Cada arranque: migraciones → admin (si no existe) → datos de demo (solo si la base está vacía) → gunicorn.
   `SECRET_KEY` la genera Render; el dominio `*.onrender.com` se agrega solo a `ALLOWED_HOSTS`,
   `CSRF_TRUSTED_ORIGINS` y `SITE_URL`.
4. Cada merge a `main` se despliega solo (después de pasar CI en el pull request).

El plan gratuito de Render apaga el servicio tras 15 minutos sin visitas: la primera carga después tarda cerca de un
minuto. Un monitor externo (por ejemplo UptimeRobot cada 5 minutos a `/health/`) lo mantiene despierto.

## Datos en producción: protección y respaldos

- **Nadie trabaja contra la base de producción desde su máquina.** Su URL solo existe en las variables de entorno de
  Render. Los cambios llegan por pull request → CI → revisión → merge.
- **Migraciones que pueden perder datos** (`RemoveField`, `DeleteModel`, `RunSQL`, `RunPython`) hacen fallar CI salvo que
  declaren `reviewed_data_safety = "<por qué es seguro>"`; la frase queda visible en el pull request.
- **Comandos destructivos** (`flush`, `seed_data --flush`) se niegan a correr en producción sin
  `--i-understand-this-deletes-production-data`.
- **Respaldo antes de un cambio delicado** (desde tu máquina, con la conexión de Neon en una variable temporal, nunca
  guardada en el proyecto):

  ```bash
  pg_dump "$NEON_URL" --format=custom --file=wh-backup-$(date +%Y%m%d).dump   # respaldo
  pg_restore --clean --no-owner --dbname "$NEON_URL" wh-backup-AAAAMMDD.dump   # restaurar
  ```

- **Restauración de Neon:** el panel permite volver la base a un momento reciente (*Restore*; la ventana depende del
  plan) o crear una **rama** (copia instantánea) para probar una migración antes de aplicarla.
- Los respaldos tienen datos personales de huéspedes: no se suben a GitHub (el repositorio es público).

## Estructura

```
config/          settings, urls, wsgi
apps/core/       contenido del sitio (home, banners, menús, contacto), optimizador de imágenes, seed_data
apps/accounts/   usuario con email como identificador, registro, login, validadores de contraseña,
                 nombre, teléfono (phones.py) y fecha de nacimiento
apps/properties/ países, ciudades, distritos, comodidades, propiedades, fotos e impuestos; búsqueda
apps/bookings/   reservas: estados, solapamiento, precios (pricing.py), reglas y retenciones (services.py),
                 checkout y confirmación
apps/payments/   pagos: validación de tarjeta (cards.py), pasarela simulada (gateways.py), cobro
                 idempotente (services.py)
templates/       base.html, pages/ y components/ reutilizables: header, footer, search_bar,
                 property_card, feature_grid, banner, carousel_controls, language_switcher
static/          css/ (tokens + un archivo por componente y por página), js/ (mejoras progresivas:
                 rango de fechas, distritos por ciudad, carruseles, aparición al hacer scroll),
                 fonts/, img/, vendor/ (Bootstrap, Bootstrap Icons, flag-icons, flatpickr, Leaflet,
                 Leaflet.markercluster,
                 leaflet-gesture-handling)
seed/images/     fotos de origen para los datos de prueba
docs/            plan maestro y decisiones técnicas
```

## Seguridad y límites contra el abuso

| Protección | Detalle |
|---|---|
| Intentos de login | 5 fallos de una cuenta desde una misma red → pausa de 15 minutos (`django-axes`, también en el admin). Cuenta + red, no solo cuenta: un atacante no puede bloquear a un huésped en su propia cuenta. El correo cuenta igual en cualquier combinación de mayúsculas |
| Retenciones de fechas | Como máximo 5 activas por red a la vez: abrir muchas sesiones no permite acaparar disponibilidad. La IP se guarda solo como hash con clave y se borra al pagar |
| IP real del visitante | Cabecera `CF-Connecting-IP` de Cloudflare (delante de Render), que el cliente no puede falsificar; `X-Forwarded-For` se ignora |
| Enlaces editables en el admin | Solo `https://`, `http://`, rutas del sitio, anclas, `mailto:` y `tel:` (contra XSS con `javascript:`) |
| Formularios, sesiones y cabeceras | CSRF, validación en el servidor, cookies seguras, HSTS, `X-Frame-Options`, redirecciones `next` solo al propio sitio |

**Verificado en producción** (19 de octubre de 2026), con un correo inventado:
- 5 intentos fallidos → el 5.º activa la pausa (HTTP 429).
- Intentos de saltarla falsificando la IP:
  - `X-Forwarded-For`, `True-Client-IP` y `X-Real-IP` → la pausa se mantiene;
  - `CF-Connecting-IP` → Cloudflare rechaza la petición antes de que llegue a la aplicación (403).

Límites reconocidos antes de operar con usuarios reales (D40, D41): verificación del correo al registrarse,
recuperación de contraseña, desafío anti-bots para redes de muchas IPs, MFA para el admin y Content-Security-Policy.

## Mejoras planificadas (fuera del alcance de la prueba)

| Mejora | Cómo |
|---|---|
| Pasarela de pago real (dLocal o Stripe) | Otra clase con la interfaz `PaymentGateway` y campos de tarjeta del proveedor (tokenización: el número nunca pasa por el servidor) |
| Verificación de correo y recuperación de contraseña | Vistas de Django (`PasswordResetView`) y un enlace firmado de verificación; decidir con WH si se verifica antes o después del primer pago |
| Anti-bots y MFA para el admin | Cloudflare Turnstile en el login y al reservar; `django-otp` para el personal |
| Login con Google | `django-allauth`; solo se unen cuentas si Google confirma el correo, y el checkout sigue pidiendo los datos que falten |
| Correos desde una cola | Celery o RQ, para que el huésped no espere al proveedor de correo |
| Dominio propio verificado en Brevo (SPF, DKIM) | Mejor entregabilidad: menos correos en Spam |
| Tareas programadas | `expire_holds` y `send_booking_confirmations` cada pocos minutos (cron) |
| Servicios adicionales, facturación, cuotas, Wynwood Points | Pantallas del Figma fuera del PDF; se agregarían como líneas de la reserva |

## Licencias

El código está bajo licencia MIT (ver [LICENSE](LICENSE)). Las fuentes de `static/fonts/` (Acumin Pro y Helvetica Neue)
y las imágenes del diseño son propiedad de sus autores. Wynwood House las proporcionó solo para evaluar esta prueba,
y no están cubiertas por la licencia del repositorio. Bootstrap, Bootstrap Icons y flag-icons (MIT) conservan sus
licencias en `static/vendor/`, igual que flatpickr, Leaflet.markercluster y leaflet-gesture-handling (MIT) y Leaflet (BSD-2).
Los mapas usan teselas de [OpenStreetMap](https://www.openstreetmap.org/copyright) © sus colaboradores.
