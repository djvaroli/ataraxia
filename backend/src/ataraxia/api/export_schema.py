"""Print the OpenAPI contract without a running server or external credentials."""

import json

from ataraxia.api.main import create_app

if __name__ == "__main__":
    print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))
