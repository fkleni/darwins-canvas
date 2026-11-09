from pathlib import Path

SIM_DIR = Path(__file__).parent.parent / "app" / "sim"


def test_the_simulation_never_imports_the_ai_layer():
    for path in SIM_DIR.glob("*.py"):
        assert "app.ai" not in path.read_text(encoding="utf-8"), path.name