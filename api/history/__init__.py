import json
import os

import azure.functions as func
from azure.data.tables import TableServiceClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    service = TableServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    table = service.create_table_if_not_exists("summaries")

    items = []
    for entity in table.list_entities():
        items.append({
            "course": entity["PartitionKey"],
            "summary": entity.get("summary", ""),
            "createdAt": entity.get("createdAt", ""),
        })

    # Newest first
    items.sort(key=lambda x: x["createdAt"], reverse=True)

    return func.HttpResponse(json.dumps(items), mimetype="application/json")