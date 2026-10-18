# WH Booking

Flujo de reserva de propiedades para **Wynwood House**, desarrollado como prueba técnica *Fullstack Developer Python*.
Incluye home con buscador, resultados, detalle con disponibilidad, registro, checkout con pago simulado,
confirmación y correo, en español e inglés.

> 🚧 En construcción por fases. El plan y el estado de cada fase están en [docs/PLAN_MAESTRO.md](docs/PLAN_MAESTRO.md),
> y las decisiones técnicas, con sus ejemplos, en [docs/DECISIONS.md](docs/DECISIONS.md).

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

Crear un usuario administrador:

```bash
docker compose exec web python manage.py createsuperuser
```

## Comandos útiles

```bash
docker compose exec web pytest                       # tests
docker compose exec web ruff check . && docker compose exec web ruff format .
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py makemessages -l es --ignore=.venv
docker compose exec web python manage.py compilemessages --ignore=.venv
```

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
apps/core/       contenido del sitio, home, health check
apps/accounts/   usuario con email como identificador
templates/       base.html, components/ (reutilizables), pages/
static/          css/ (tokens + un archivo por componente), fonts/, img/, vendor/
docs/            plan maestro y decisiones técnicas
```

## Licencias

El código está bajo licencia MIT (ver [LICENSE](LICENSE)). Las fuentes de `static/fonts/` (Acumin Pro y Helvetica Neue)
y las imágenes del diseño son propiedad de sus autores. Wynwood House las proporcionó solo para evaluar esta prueba,
y no están cubiertas por la licencia del repositorio.
