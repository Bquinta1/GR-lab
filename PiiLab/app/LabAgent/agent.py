import json
import os
from typing import Any

import boto3

from claims import get_claim, send_to_repair_partner
from control import for_storage


MODEL_ID = os.getenv("MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0",)
REGION = os.getenv("AWS_REGION", "us-east-1")
MAX_TOOL_LOOPS = 8

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

TOOLS = [
    {
        "toolSpec": {
            "name": "get_claim",
            "description": "Read a warranty claim from the fake claim system. Use the claim ID WC-2026-0042.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "claim_id": {
                            "type": "string",
                            "description": "Warranty claim identifier.",
                        }
                    },
                    "required": ["claim_id"],
                }
            },
        }
    },
    {
        "toolSpec": {
            "name": "send_to_repair_partner",
            "description": "Send the minimum information needed to a simulated repair partner for a warranty inspection. Use the claim ID.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "claim_id": {
                            "type": "string",
                            "description": "Warranty claim identifier.",
                        }
                    },
                    "required": ["claim_id"],
                }
            },
        }
    },
]


def _execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "get_claim":
        return get_claim(arguments["claim_id"])

    if name == "send_to_repair_partner":
        return send_to_repair_partner(arguments["claim_id"])

    return {"error": f"Unknown tool: {name}"}


def _persist_turn(user_message: str, response: str) -> None:
    record = for_storage(
        {
            "user_message": user_message,
            "response": response,
        }
    )

    with open("agent-records.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def run(user_message: str) -> str:
    """Run the Bedrock agent and its tool loop."""
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [{"text": user_message}],
        }
    ]

    system_prompt = """You are a warranty-claim assistant.

You can read a fictional warranty claim and, when requested, send the
claim to a simulated repair partner.

The repair-partner tool enforces its own privacy boundary. Never try to
construct or invent a partner payload yourself; call the tool with the
claim ID.

Answer the user's question using the tool results. Do not reveal
unnecessary personal information from a claim."""

    for _ in range(MAX_TOOL_LOOPS):
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=messages,
            toolConfig={"tools": TOOLS},
            inferenceConfig={"maxTokens": 500},
        )

        output = response["output"]["message"]
        messages.append(output)

        stop_reason = response.get("stopReason")

        if stop_reason != "tool_use":
            text_parts = [
                block["text"]
                for block in output.get("content", [])
                if "text" in block
            ]
            result = "".join(text_parts).strip()

            _persist_turn(user_message, result)
            return result

        tool_results = []

        for block in output.get("content", []):
            if "toolUse" not in block:
                continue

            tool_use = block["toolUse"]

            try:
                result = _execute_tool(
                    tool_use["name"],
                    tool_use.get("input", {}),
                )
            except Exception as exc:
                result = {"error": str(exc)}

            tool_results.append(
                {
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [
                            {"json": result}
                        ],
                    }
                }
            )

        messages.append(
            {
                "role": "user",
                "content": tool_results,
            }
        )

    raise RuntimeError("Tool loop exceeded maximum iterations.")
