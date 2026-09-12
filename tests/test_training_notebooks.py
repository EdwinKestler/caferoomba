"""Notebook wiring stays thin, executable Python and free of embedded credentials."""
import ast
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("name", ["01_prepare_and_annotate", "02_train_and_evaluate",
                                  "03_export_and_replay"])
def test_notebook_setup_and_code_contract(name):
    notebook = json.loads((Path("notebooks") / f"{name}.ipynb").read_text())
    cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    for cell in cells:
        ast.parse("".join(cell["source"]))
        assert cell["outputs"] == []
    code = "\n".join("".join(c["source"]) for c in cells)
    assert "CAFEROOMBA_REVISION" in code and "CAFEROOMBA_WORKSPACE" in code
    assert "build_synthetic_clips" not in code
    assert "NVIDIA_API_KEY" not in code
    if name.startswith("02"):
        assert "train_run(" in code and "evaluate_run(" not in code
    if name.startswith("03"):
        assert "train_steps" not in code and "train_run(" not in code
        assert "evaluate_run(" in code and "export_run(" in code
