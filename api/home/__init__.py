import os

import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    # Serve the web page from the same Function App as the API
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, encoding="utf-8") as f:
        return func.HttpResponse(f.read(), mimetype="text/html")
