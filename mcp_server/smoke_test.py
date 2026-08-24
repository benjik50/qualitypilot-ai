import asyncio
import json
import os
from typing import Any

from mcp import Client


MCP_URL = os.getenv(
    "MCP_URL",
    "http://localhost:8001/mcp",
)


def display_result(
    title: str,
    value: Any,
) -> None:
    print(f"\n=== {title} ===")

    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


async def main() -> None:
    async with Client(MCP_URL) as client:
        tools_result = await client.list_tools()

        tool_names = [
            tool.name
            for tool in tools_result.tools
        ]

        display_result(
            "OUTILS MCP DÉCOUVERTS",
            tool_names,
        )

        documents_result = await client.call_tool(
            "list_documents",
            {},
        )

        display_result(
            "LISTE DES DOCUMENTS",
            documents_result.structured_content,
        )

        answer_result = await client.call_tool(
            "ask_qualitypilot",
            {
                "question": (
                    "Sous quel délai un fournisseur doit-il "
                    "accuser réception d'une anomalie critique ?"
                ),
                "top_k": 3,
            },
        )

        display_result(
            "RÉPONSE RAG VIA MCP",
            answer_result.structured_content,
        )


if __name__ == "__main__":
    asyncio.run(main())