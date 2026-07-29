import json
from groq import Groq
from secret_config import GROQ_API_KEY
import knowledge_base as kb

MODEL_NAME = "openai/gpt-oss-120b"
MAX_TOOL_ITERATIONS = 5

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """
You are Instant AI Agent, a helpful assistant for an online courses and diplomas platform called Instant.
You answer questions about courses, diplomas, tracks, prices, free content and comparisons between tracks.

Language rule:
- Detect the language the user is writing in for their current message.
- If the user writes in Arabic, reply fully in Arabic (Egyptian conversational tone, friendly and clear).
- If the user writes in English, reply fully in English.
- If the user mixes both languages, reply in whichever language dominates their last message.
- Never mix languages in a single reply.

Behavior rules:
- Always use the provided tools to fetch course and pricing information instead of guessing.
- Never invent prices, durations or course names that are not returned by the tools.
- If no matching course is found, tell the user clearly and suggest they check the available tracks.
- When comparing two tracks, present the comparison in a clear structured way.

Answer scope rules:
- Never paste the raw tool output back to the user. Read it, then answer only what was actually asked.
- If the user asks for a list of course or track names only, give names only, no prices, no durations, no descriptions.
- If the user asks about a price, give the price for the relevant course only.
- If the user asks about one specific course or diploma, talk about that one only, not the rest of the catalog.
- If the user asks a broad question like "what do you have" or "I want to start learning AI", give a short list of relevant track or course names only, and ask a short follow up question to narrow it down.
- Keep every answer as short as possible while fully answering what was asked.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_all_courses",
            "description": "Get the full list of all available courses, tracks and diplomas with prices",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_courses",
            "description": "Search courses by a keyword matching track name, course name or description",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Keyword to search for"}
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_free_courses",
            "description": "Get the list of free courses or free content available on the platform",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_tracks",
            "description": "Compare two tracks side by side, for example Frontend vs Fullstack",
            "parameters": {
                "type": "object",
                "properties": {
                    "track_a": {"type": "string", "description": "Name of the first track"},
                    "track_b": {"type": "string", "description": "Name of the second track"},
                },
                "required": ["track_a", "track_b"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "get_all_courses": lambda **kwargs: kb.get_all_courses(),
    "search_courses": lambda **kwargs: kb.search_courses(kwargs.get("keyword", "")),
    "get_free_courses": lambda **kwargs: kb.get_free_courses(),
    "compare_tracks": lambda **kwargs: kb.compare_tracks(kwargs.get("track_a", ""), kwargs.get("track_b", "")),
}


def _build_messages(history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def get_agent_reply(history):
    messages = _build_messages(history)

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
            result = function_to_call(**arguments) if function_to_call else {"error": "unknown tool"}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return "Sorry, I could not complete this request right now, please try rephrasing your question."