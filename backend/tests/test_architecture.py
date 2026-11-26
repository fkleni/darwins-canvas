from pathlib import Path

SIM_DIR = Path(__file__).parent.parent / "app" / "sim"
HIGHER_LAYERS = ("app.ai", "app.catalog")


def test_the_simulation_never_imports_the_layers_above_it():
    for path in SIM_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for layer in HIGHER_LAYERS:
            assert layer not in text, f"{path.name} mentions {layer}"