"""Export the current FastAPI contract without starting the server."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.main import app

if __name__ == "__main__":
    (root / "frontend/.openapi.generated.json").write_text(
        json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8", newline="\n"
    )
