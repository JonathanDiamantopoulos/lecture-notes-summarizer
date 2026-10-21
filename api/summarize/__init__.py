import json
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.data.tables import TableServiceClient

TABLE_NAME = "summaries"
MAX_CHARS = 5000  # keeps each request inside one Free-tier transaction


def get_language_client():
    return TextAnalyticsClient(
        endpoint=os.environ["LANGUAGE_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["LANGUAGE_KEY"]),
    )


def get_summary(client, text, sentence_count):
    """Extractive summary. Returns None if the region doesn't support it."""
    try:
        poller = client.begin_extract_summary([text], max_sentence_count=sentence_count)
        for result in poller.result():
            if not result.is_error:
                return " ".join(s.text for s in result.sentences)
    except Exception:
        pass
    return None


def get_key_phrases(client, text):
    result = client.extract_key_phrases([text])[0]
    return [] if result.is_error else result.key_phrases[:10]


def save_result(entry):
    service = TableServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    table = service.create_table_if_not_exists(TABLE_NAME)
    table.create_entity({
        "PartitionKey": entry["course"],
        "RowKey": str(uuid.uuid4()),
        "createdAt": entry["createdAt"],
        "summary": entry["summary"] or "",
        "keyPhrases": json.dumps(entry["keyPhrases"]),
    })


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return error("Request body must be JSON.", 400)

    text = (body.get("text") or "").strip()
    course = (body.get("course") or "General").strip()[:50]
    length = {"short": 2, "medium": 4, "long": 6}.get(body.get("length"), 4)

    if not text:
        return error("Please paste some notes first.", 400)
    text = text[:MAX_CHARS]

    client = get_language_client()
    entry = {
        "course": course,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": get_summary(client, text, length),
        "keyPhrases": get_key_phrases(client, text),
    }

    try:
        save_result(entry)
    except Exception as e:  # still return the result even if saving fails
        entry["saveError"] = str(e)

    return func.HttpResponse(json.dumps(entry), mimetype="application/json")


def error(message, status):
    return func.HttpResponse(json.dumps({"error": message}), status_code=status, mimetype="application/json")
