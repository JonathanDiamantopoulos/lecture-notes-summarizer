import json
import os

import azure.functions as func
from azure.data.tables import TableServiceClient

TABLE_NAME = "summaries"


def main(req: func.HttpRequest) -> func.HttpResponse:
    course = req.params.get("course")

    service = TableServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    table = service.create_table_if_not_exists(TABLE_NAME)

    if course:
        safe = course.replace("'", "''")
        entities = table.query_entities(f"PartitionKey eq '{safe}'")
    else:
        entities = table.list_entities()

    items = [{
        "course": e["PartitionKey"],
        "createdAt": e.get("createdAt", ""),
        "summary": e.get("summary", ""),
        "keyPhrases": json.loads(e.get("keyPhrases", "[]")),
    } for e in entities]

    items.sort(key=lambda x: x["createdAt"], reverse=True)
    return func.HttpResponse(json.dumps(items[:50]), mimetype="application/json")
