"""Print the FastAPI OpenAPI document deterministically (used by `pnpm contracts:generate|check`)."""
import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2, sort_keys=True))
