"""Write the OpenAPI document so the frontend can generate its types.

Run via `make types`. The generated file is committed, so a schema change
shows up as a diff in the frontend rather than a runtime surprise.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.main import create_app  # noqa: E402

if __name__ == "__main__":
    target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(create_app().openapi(), indent=2))
    print(f"wrote {target}")
