"""Fase 13 DoD (R16): backend/domain/ no importa FastAPI, el driver de Postgres, ni el SDK
del LLM/embeddings — Python puro. backend/application/ tampoco (depende de domain/ports, no
de implementaciones concretas). Chequeo estático real, no solo revisión manual.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULES = {"fastapi", "starlette", "psycopg", "psycopg2", "jwt", "bcrypt", "pgvector", "openai", "anthropic"}
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def _imported_top_level_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _offenders_in(directory: Path) -> dict[str, set[str]]:
    offenders = {}
    for py_file in directory.rglob("*.py"):
        forbidden_found = _imported_top_level_modules(py_file) & FORBIDDEN_MODULES
        if forbidden_found:
            offenders[str(py_file.relative_to(BACKEND_DIR.parent))] = forbidden_found
    return offenders


def test_domain_layer_never_imports_frameworks_or_drivers():
    offenders = _offenders_in(BACKEND_DIR / "domain")
    assert not offenders, f"backend/domain/ imports forbidden modules: {offenders}"


def test_application_layer_never_imports_frameworks_or_drivers():
    offenders = _offenders_in(BACKEND_DIR / "application")
    assert not offenders, f"backend/application/ imports forbidden modules: {offenders}"


def test_domain_layer_has_the_expected_ports_for_the_strategy_pattern():
    """D010: LLMProvider/EmbeddingProvider/PasswordHasher/TokenService son interfaces
    (Strategy) — un solo proveedor real detrás de cada una, intercambiable sin tocar
    application/ ni presentation/."""
    ports_source = (BACKEND_DIR / "domain" / "ports.py").read_text(encoding="utf-8")
    for expected in ["UserRepository", "MessageRepository", "PasswordHasher", "TokenService", "EmbeddingProvider", "LLMProvider"]:
        assert f"class {expected}(ABC)" in ports_source, f"missing port interface: {expected}"
