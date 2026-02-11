# Python Multi-Module Template

Template de projeto Python com arquitetura multimódulo usando UV workspace, MyPy strict mode, Ruff, Pytest e Docker.

## Estrutura

```
├── pyproject.toml              # Workspace UV root
├── ruff.toml                   # Configuração compartilhada do Ruff
├── mypy.ini                    # MyPy strict mode
├── docker-compose.yml          # Ambiente de desenvolvimento
│
├── packages/                   # Módulos compartilhados
│   └── common/                 # Código de uso comum
│       └── src/shared/
│
├── apps/                       # Aplicações
│   └── compras_divididas/      # App principal
│       ├── Dockerfile          # Multi-stage build
│       └── src/compras_divididas/
│
└── tests/                      # Testes de integração
```

## Requisitos

- Python >= 3.12
- [UV](https://docs.astral.sh/uv/) - Gerenciador de pacotes
- Docker & Docker Compose (opcional)

## Primeiros Passos

```bash
# Clonar ou usar como template
git clone <repo> myproject
cd myproject

# Instalar dependências
uv sync

# Verificar se tudo funciona
uv run pytest
```

## Comandos

### Desenvolvimento

```bash
# Sincronizar ambiente
uv sync

# Rodar testes
uv run pytest
uv run pytest -v                    # Verbose
uv run pytest packages/common       # Só um pacote

# Lint e formatação
uv run ruff check .                 # Checar código
uv run ruff check . --fix           # Auto-corrigir
uv run ruff format .                # Formatar código

# Type checking (strict)
uv run mypy .

# Rodar uma app
uv run python -m compras_divididas.cli healthcheck
```

### Docker

```bash
# Build da imagem
docker build -f apps/compras_divididas/Dockerfile -t compras-divididas:latest .

# Rodar container
docker run --rm compras-divididas:latest

# Dev environment com PostgreSQL
docker-compose up

# Parar
docker-compose down
```

## Adicionar um Novo Módulo

### Package compartilhado

```bash
mkdir -p packages/newmodule/src/newmodule
touch packages/newmodule/src/newmodule/__init__.py
touch packages/newmodule/src/newmodule/py.typed
```

Criar `packages/newmodule/pyproject.toml`:

```toml
[project]
name = "newmodule"
version = "0.1.0"
requires-python = ">=3.12"
description = "New shared module"
dependencies = ["shared"]

[tool.uv.sources]
shared = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/newmodule"]
```

### Nova Aplicação

```bash
mkdir -p apps/myapp/src/myapp
touch apps/myapp/src/myapp/__init__.py
touch apps/myapp/Dockerfile
```

Criar `apps/myapp/pyproject.toml`:

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.12"
description = "My application"
dependencies = ["shared"]

[tool.uv.sources]
shared = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/myapp"]
```

Atualizar `pyproject.toml` raiz:

```toml
[dependency-groups]
dev = [
    "...",
    "newmodule",
    "myapp",
]

[tool.uv.sources]
newmodule = { workspace = true }
myapp = { workspace = true }
```

Atualizar `mypy.ini`:

```ini
mypy_path = packages/common/src:packages/newmodule/src:apps/compras_divididas/src:apps/myapp/src
```

Rodar `uv sync` para instalar.

## Configuração das Ferramentas

### Ruff (`ruff.toml`)

- Line length: 88 (estilo Black)
- Target Python: 3.12
- Regras: E, F, W, I, UP, B, SIM, N, RUF

### MyPy (`mypy.ini`)

- `strict = True`
- Namespace packages habilitado
- Todos os paths de src configurados

### Pre-commit Hook

O hook em `.git/hooks/pre-commit` roda automaticamente:
- `ruff check --fix` nos arquivos staged
- `pytest` (todos os testes)

Para pular: `git commit --no-verify`

## Docker

O Dockerfile usa multi-stage build:
1. **Builder**: Instala UV, resolve dependências, builda wheels
2. **Runtime**: Apenas o `.venv`, sem ferramentas de build

Benefícios:
- Imagem final pequena (~60MB)
- Layer caching eficiente
- Sem código fonte no runtime

## Workflow de Desenvolvimento

1. **Criar feature branch**
   ```bash
   git checkout -b feature/minha-feature
   ```

2. **Desenvolver**
   - Código em `src/` dos respectivos módulos
   - Testes em `tests/` de cada módulo

3. **Antes de commitar**
   - Pre-commit hook roda automaticamente
   - Ou manualmente: `uv run ruff check . && uv run pytest`

4. **Testar no Docker**
   ```bash
   docker build -f apps/compras_divididas/Dockerfile -t compras-divididas:test .
   docker run --rm compras-divididas:test
   ```

## Comandos de Manutenção

```bash
# Atualizar todas as dependências
uv sync --upgrade

# Limpar cache
rm -rf .venv .pytest_cache .mypy_cache .ruff_cache
uv sync

# Verificar lockfile
uv lock --check
```

## VSCode

Recomendado instalar extensões:
- Ruff
- BasedPyright (já configurado no `opencode.json`)

## Licença

MIT
