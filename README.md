# WH Booking

Flujo de reserva de propiedades para **Wynwood House**, desarrollado como prueba técnica *Fullstack Developer Python*.
Incluye home con buscador, resultados, detalle con disponibilidad, registro, checkout con pago simulado,
confirmación y correo, en español e inglés.

> 🚧 En construcción por fases. El plan y el estado de cada fase están en [docs/PLAN_MAESTRO.md](docs/PLAN_MAESTRO.md),
> y las decisiones técnicas, con sus ejemplos, en [docs/DECISIONS.md](docs/DECISIONS.md).

## Estado

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Docker, PostgreSQL, configuración, usuario con email, ES/EN, CI | ✅ |
| 1 | Modelos de contenido y catálogo, admin bilingüe, imágenes WebP, `seed_data` | ✅ |
| 2 | Home: buscador, destinos, destacadas, servicios, "¿Por qué viajar a España?", banners, header y footer | ✅ |
| 3 | Despliegue | ⏳ |
| 4 | Resultados: filtros por ubicación, fechas y huéspedes; mapa con precios y agrupamiento | ✅ |
| 5 | Detalle de la propiedad: galería, calendario de disponibilidad, precio en vivo y retención de fechas | ✅ |
| 6 | Registro y login con email, contraseñas seguras con requisitos en vivo, logout seguro | ✅ |
| 7 | Checkout: registro con datos personales, pago simulado idempotente y confirmación con la ubicación exacta | ✅ |
| 8 | Correo de confirmación | ⏳ |

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
   de nacimiento (mayor de 18). Con sesión iniciada y el perfil completo, este paso se salta; "Iniciar sesión" vuelve
   al mismo checkout.
5. **Paso 2, pago simulado.** No se cobra nada ni se guardan datos de tarjeta (solo marca y últimos 4 dígitos).
   Las tarjetas de prueba aparecen en la página y se completan con un clic:

   | Tarjeta | Resultado |
   |---|---|
   | `4242 4242 4242 4242` (Visa), `5555 5555 5555 4444` (Mastercard), `3782 822463 10005` (Amex) | Aprobada |
   | `4000 0000 0000 0002` | Rechazada |
   | `4000 0000 0000 9995` | Fondos insuficientes |
   | Cualquier otra tarjeta válida | Rechazada con aviso de demo |

   Vencimiento: cualquier fecha futura. Código de seguridad: 3 dígitos (4 en American Express).
6. **Confirmación** (`/es/bookings/<referencia>/`): solo la ve quien reservó. Muestra la dirección exacta, el mapa con
   el punto preciso y "Abrir en Google Maps".

Un doble clic, recargar la página o pagar desde dos pestañas a la vez nunca cobra dos veces (ver D11).

Reglas que valida el servidor: llegada no pasada (según la zona horaria de la ciudad), salida posterior a la llegada,
capacidad de la propiedad, hasta 30 noches en línea y sin solapamiento con otra reserva o retención vigente,
también ante dos reservas simultáneas (ver D06 a D09 en [docs/DECISIONS.md](docs/DECISIONS.md)).

## Comandos útiles

```bash
docker compose exec web pytest                       # tests
docker compose exec web python manage.py expire_holds # marca como vencidas las retenciones caducadas (opcional, p. ej. con cron)
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

Con SQLite, la protección contra reservas simultáneas queda en la capa de aplicación;
la restricción de exclusión de fechas es exclusiva de PostgreSQL (ver D02 y D07 en las decisiones).

## Configuración

Toda la configuración se lee de variables de entorno. [.env.example](.env.example) lista cada una con su propósito.

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

## Licencias

El código está bajo licencia MIT (ver [LICENSE](LICENSE)). Las fuentes de `static/fonts/` (Acumin Pro y Helvetica Neue)
y las imágenes del diseño son propiedad de sus autores. Wynwood House las proporcionó solo para evaluar esta prueba,
y no están cubiertas por la licencia del repositorio. Bootstrap, Bootstrap Icons y flag-icons (MIT) conservan sus
licencias en `static/vendor/`, igual que flatpickr, Leaflet.markercluster y leaflet-gesture-handling (MIT) y Leaflet (BSD-2).
Los mapas usan teselas de [OpenStreetMap](https://www.openstreetmap.org/copyright) © sus colaboradores.
