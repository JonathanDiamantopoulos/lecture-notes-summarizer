import json
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.data.tables import TableServiceClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()
    text = body.get("text", "").strip()
    course = body.get("course", "General").strip()

    if not text:
        return func.HttpResponse(json.dumps({"error": "Please paste some notes first."}), status_code=400)

    # Connect to Azure AI Language
    client = TextAnalyticsClient(
        endpoint=os.environ["LANGUAGE_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["LANGUAGE_KEY"]),
    )

    # Get a summary (up to 4 sentences)
    summary = None
    try:
        result = client.begin_extract_summary([text[:5000]], max_sentence_count=4).result()
        for doc in result:
            summary = " ".join(s.text for s in doc.sentences)
    except Exception:
        pass  # summarization isn't available in every region

    # Get key phrases
    key_phrases = client.extract_key_phrases([text[:5000]])[0].key_phrases[:10]

    # Save to Table Storage
    service = TableServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"])
    table = service.create_table_if_not_exists("summaries")
    table.create_entity({
        "PartitionKey": course,
        "RowKey": str(uuid.uuid4()),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "summary": summary or "",
    })

    return func.HttpResponse(
        json.dumps({"course": course, "summary": summary, "keyPhrases": key_phrases}),
        mimetype="application/json",
    )