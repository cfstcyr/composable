# composable

Programmatically generate Docker Compose files using Python and Jinja2 templates.

**composable** lets you write modular, reusable Docker Compose configurations that are dynamically assembled at runtime. Instead of maintaining monolithic `docker-compose.yml` files, you can split your configuration into fragments, use templates with variables, and even define services using Python functions.

## Quick Start

1. Install the package:

```bash
pip install -e .
```

2. Create a config file `composable.yaml` (Optional, defaults shown):

```yaml
src:
  dir: ./compose
  glob: "**/*.*"
  exclude_patterns:
    - "\/_"                     # Exclude files/dirs starting with underscore
  version_spec: ">=0"           # Semver specifier for version selection
```

3. Create a compose fragment `compose/web.yml`:

```yaml
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
```

4. Run it:

```bash
composable compose up -d
```

That's it! composable discovers all files in `./compose`, merges them, and runs `docker compose up -d` with the generated configuration.

## Installation

composable is not yet published to PyPI. Install it locally:

```bash
# Using pip
pip install -e .

# Using uv
uv pip install -e .
```

## Core Concepts

### File Discovery & Merging

composable scans a source directory for compose fragments and merges them into a single Docker Compose configuration. Files are discovered using glob patterns and can be filtered by version or exclude patterns.

```
compose/
  web.yml          # Merged
  database.yml     # Merged
  redis.yml        # Merged
  _partials/       # Excluded (underscore prefix)
    labels.yml
```

All discovered files are deep-merged in order. Later files override earlier ones for conflicting keys.

### Providers

composable supports two types of compose file providers:

**YAML/Jinja2 Provider** handles `.yml`, `.yaml`, `.yml.jinja`, and `.yaml.jinja` files. Jinja2 templates have access to all data variables and can include other templates. Jinja2 will be used regardless of the file extension.

**Python Provider** handles `.py` files. Define a `compose` function that returns a dictionary, and it will be merged into the final configuration.

### Data Injection

Pass variables to your templates via:

- The `data` section in `composable.yaml`
- Data files (YAML/JSON) via `data_files`
- CLI flags with `-d key=value`

Data is available in Jinja2 templates and passed as keyword arguments to Python `compose` functions.

## Configuration

Create a `composable.yaml` (or `composable.yml`, `c.yaml`) in your project root:

```yaml
# Source file configuration
src:
  dir: ./compose                # Directory containing compose fragments
  glob: "**/*.*"                # Glob pattern (default: all files)
  exclude_patterns:             # Regex patterns to exclude
    - "\/_"                     # Exclude files/dirs starting with underscore
  version_spec: ">=0"           # Semver specifier for version selection

# Data available to templates
data:
  environment: production
  domain: example.com

# Load data from external files (defaults shown)
data_files:
  - data.yaml
  - globals.yaml
  - values.yaml
```

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `composable compose <args>` | Generate compose file and run `docker compose <args>` |
| `composable output` | Output the generated compose file without running docker |

### Common Options

| Option | Description |
|--------|-------------|
| `-c, --config PATH` | Path to config file(s) |
| `--src-dir PATH` | Override source directory |
| `-d, --data KEY=VALUE` | Pass data (supports dot notation: `db.host=localhost`) |
| `--dry-run` | Show the docker command without executing |
| `-f, --format FORMAT` | Output format: `yaml` (default) or `json` |

### Examples

```bash
# Start services in detached mode
composable compose up -d

# Pass data via CLI
composable compose up -d -d domain=example.com -d replicas=3

# View generated compose file
composable output

# Output as JSON
composable output --format json

# Dry run (show command without executing)
composable compose up -d --dry-run

# Use a specific config file
composable compose -c production.yaml up -d
```

## Examples

### YAML Fragment

The simplest approach - just write standard Docker Compose YAML:

```yaml
# compose/database.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Jinja2 Template

Use Jinja2 for dynamic configuration:

```yaml
# compose/web.yml.jinja
services:
  web:
    image: nginx:{{ nginx_version | default('latest') }}
    ports:
      - "{{ web_port | default('80') }}:80"
    environment:
      DOMAIN: {{ domain }}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web.rule=Host(`{{ domain }}`)"
```

With `composable.yaml`:

```yaml
src:
  dir: ./compose
data:
  domain: example.com
  nginx_version: "1.25"
  web_port: 8080
```

### Jinja2 with Includes

Use partials (prefixed with `_`) for reusable snippets:

```yaml
# compose/_traefik-labels.yml.jinja
- "traefik.enable=true"
- "traefik.http.routers.{{ service }}.rule=Host(`{{ domain }}`)"
- "traefik.http.routers.{{ service }}.entrypoints=websecure"
- "traefik.http.routers.{{ service }}.tls.certresolver=letsencrypt"
```

```yaml
# compose/api.yml.jinja
services:
  api:
    image: myapp/api:latest
    labels:
      {% filter trim | indent(6) %}
        {% with service="api" %}
          {% include('_traefik-labels.yml.jinja') %}
        {% endwith %}
      {% endfilter %}
```

### Python Provider

Define compose configurations as Python functions:

```python
# compose/workers.py
def compose(replicas: int = 1, environment: str = "development"):
    return {
        "services": {
            "worker": {
                "image": "myapp/worker:latest",
                "deploy": {
                    "replicas": replicas,
                },
                "environment": {
                    "ENV": environment,
                },
            }
        }
    }
```

The function receives data as keyword arguments. You can also use a `COMPOSE` constant:

```python
# compose/networks.py
COMPOSE = {
    "networks": {
        "frontend": {"driver": "bridge"},
        "backend": {"driver": "bridge", "internal": True},
    }
}
```

## Advanced Usage

### Version Selection

composable supports semantic versioning for compose files. Add a version suffix to filenames:

```
compose/
  database.yml        # No version (always included with >=0)
  cache@1.0.0.yml     # Version 1.0.0
  cache@2.0.0.yml     # Version 2.0.0
```

Select versions in your config:

```yaml
src:
  dir: ./compose
  version_spec: ">=1.0.0,<2.0.0"  # Use cache@1.0.0.yml
```

Or per-file:

```yaml
src:
  dir: ./compose
  version_spec_mapping:
    cache: ">=2.0.0"  # Use cache@2.0.0.yml for this file only
```

### Custom Exclude Patterns

By default, files and directories starting with `_` are excluded. Customize this:

```yaml
src:
  dir: ./compose
  exclude_patterns:
    - "\/_"           # Underscore prefix (default)
    - "\.dev\."       # Files with .dev. in the name
    - "test"          # Files containing "test"
```

### File References in Data

Load data from external files using the `@` prefix:

```yaml
# globals.yaml
database:
  host: localhost
  credentials: "@secrets/db-credentials.yaml"  # Loaded from file
  literal_at: "@@not-a-file"                   # Escaped: becomes "@not-a-file"
```

```yaml
# secrets/db-credentials.yaml
username: admin
password: supersecret
```

The resulting data will have `database.credentials.username` and `database.credentials.password` populated.

### Programmatic Usage

Use composable as a library:

```python
from composable import load_compose
from composable.libs.schemas.src import Src

# Configure source
src = Src(dir="./compose", glob="**/*.yml")

# Load and merge compose files
compose_model = load_compose(
    src=src,
    data={"environment": "production", "domain": "example.com"},
)

# Access the merged configuration
print(compose_model.model_dump())
```

## Project Structure Example

A typical project using composable:

```
my-project/
  composable.yaml            # Main configuration
  globals.yaml              # Shared data/variables
  compose/
    _partials/              # Reusable Jinja2 snippets (excluded)
      traefik-labels.yml.jinja
      logging.yml.jinja
    web.yml.jinja           # Web service (Jinja2)
    api.py                  # API service (Python)
    database.yml            # Database (plain YAML)
    cache@1.0.0.yml         # Redis v1
    cache@2.0.0.yml         # Redis v2 (cluster mode)
```

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Run linting: `ruff check . && pyright`
6. Commit your changes: `git commit -m "Add my feature"`
7. Push to the branch: `git push origin feature/my-feature`
8. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/composable.git
cd composable

# Install with development dependencies
uv sync --all-groups

# Run tests
pytest

# Run linting
ruff check .
pyright
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
