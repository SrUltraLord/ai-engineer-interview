"""El dominio y la aplicación no deben importar frameworks ni adaptadores."""
import pathlib

ROOT = pathlib.Path(__file__).parents[2] / "src" / "agent_api"
FRAMEWORKS = ("fastapi", "langchain", "pydantic", "mcp", "jwt", "openai", "azure", "dotenv", "starlette")
FORBIDDEN = {
    "domain": FRAMEWORKS + ("agent_api.adapters", "agent_api.application", "agent_api.bootstrap"),
    "application": FRAMEWORKS + ("agent_api.adapters", "agent_api.bootstrap"),
}


def _imported_modules(path: pathlib.Path) -> list[str]:
    modules = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if line.startswith("import "):
            modules.append(parts[1])
        elif line.startswith("from "):
            modules.append(parts[1])
    return modules


def test_dependency_rule():
    for layer, banned in FORBIDDEN.items():
        for path in (ROOT / layer).rglob("*.py"):
            for module in _imported_modules(path):
                root = module.split(".")[0]
                assert root not in banned and not any(module.startswith(b) for b in banned if "." in b), (
                    f"{layer}/{path.name} importa {module}"
                )
