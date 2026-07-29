"""
agent.py
--------
Multi-agent procurement assistant built with CrewAI.

Two agents run sequentially:
  1. Search Agent   -> passes the user's raw text (Arabic or English) into
                        search_products. All the bilingual/typo-tolerant
                        matching lives in knowledge_base.py, not in the
                        prompt, so the agent never has to translate or
                        guess spelling - it just calls the tool as-is.
  2. Advisor Agent   -> writes the final short reply: a comparison +
                        recommendation if products were found, a brief
                        welcome/explainer if the message was general, or a
                        short "nothing matched, try this" note otherwise.

Kept to two simple agents/tasks (not three+) and short replies on purpose,
to keep token usage - and the chance of hitting rate limits - low.
"""

import json

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

import knowledge_base as kb
from secret_config import GROQ_API_KEY, GROQ_MODEL, validate_config

validate_config()

llm = LLM(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.3)


# ---------------------------------------------------------------------------
# Tools (wrap the local knowledge base - fast, no external calls)
# ---------------------------------------------------------------------------

def _compact(p: dict) -> dict:
    """Trim a product dict to the fields the LLM actually needs (keeps
    prompts small)."""
    top_spec = next(iter(p["specs"].items()), None)
    return {
        "id": p["id"],
        "name": p["name"],
        "category": p["category"],
        "price_usd": p["price_usd"],
        "rating": p["rating"],
        "spec": f"{top_spec[0]}: {top_spec[1]}" if top_spec else "",
    }


@tool("search_products")
def search_products_tool(query: str, max_price: float = None) -> str:
    """Search the local product catalog. Already understands Arabic and
    English, including typos/dialect spelling (e.g. 'لابتويات', 'لابات',
    'laptop' all match the Laptops category) - pass the user's text as-is,
    no translation needed. Optional max_price filters by budget in USD.
    Returns a compact JSON list of matches (may be empty)."""
    results = kb.search_products(query=query, max_price=max_price)
    return json.dumps([_compact(p) for p in results], ensure_ascii=False)


@tool("rank_products")
def rank_products_tool(product_ids_csv: str) -> str:
    """Rank a comma-separated list of product IDs by value (price + rating).
    Returns a compact JSON list ordered from best to worst value."""
    ids = [pid.strip() for pid in product_ids_csv.split(",") if pid.strip()]
    products = kb.get_products_by_ids(ids)
    ranked = kb.rank_by_value(products)
    return json.dumps([{**_compact(p), "value_score": p["value_score"]} for p in ranked], ensure_ascii=False)


@tool("list_categories")
def list_categories_tool(_: str = "") -> str:
    """List all available product categories in the catalog."""
    return json.dumps(kb.get_categories(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

search_agent = Agent(
    role="Product Search Specialist",
    goal="Find matching products for the user's request, if there is one.",
    backstory=(
        "You work for Instant Solutions' procurement team. search_products "
        "already understands Arabic and English (even with typos) - always call "
        "it with the user's raw text, never translate or rewrite it. If the "
        "message is general small talk or asks what the company offers, call "
        "list_categories instead. Never invent products that aren't in the data."
    ),
    tools=[search_products_tool, list_categories_tool],
    llm=llm,
    verbose=False,
    allow_delegation=False,
)

advisor_agent = Agent(
    role="Procurement Advisor",
    goal="Always give the user a short, useful, well-formatted answer.",
    backstory=(
        "You are a friendly procurement advisor for Instant Solutions. You reply "
        "in the same language the user used (Arabic or English), briefly and "
        "clearly. If the previous task found product matches, call rank_products "
        "with their IDs first. You never just say 'no results' - if nothing "
        "matched, briefly mention the available categories and ask the user to "
        "pick one. Keep replies short (3-6 lines), minimal formatting, no big "
        "markdown headers."
    ),
    tools=[rank_products_tool],
    llm=llm,
    verbose=False,
    allow_delegation=False,
)


# ---------------------------------------------------------------------------
# Crew runner
# ---------------------------------------------------------------------------

def run_procurement_agent(user_query: str, chat_history: list = None) -> str:
    """Runs the 2-agent crew sequentially for one user message and returns
    the final reply text."""
    history_snippet = ""
    if chat_history:
        recent = chat_history[-3:]
        history_snippet = " | ".join(f"{m['role']}: {m['content']}" for m in recent)

    search_task = Task(
        description=(
            f"User message: '{user_query}'\n"
            f"Recent context (reference only): {history_snippet}\n\n"
            "If this is a product/procurement request, call search_products with "
            "the user's raw text (plus max_price if a budget was mentioned). If "
            "it's a general message (greeting, 'what do you sell', small talk), "
            "call list_categories instead and say clearly this is a general "
            "message, not a product search."
        ),
        expected_output=(
            "Either a JSON list of matching products, or a short note that this "
            "is a general message plus the list of available categories."
        ),
        agent=search_agent,
    )

    advisor_task = Task(
        description=(
            f"Original user message: '{user_query}'\n\n"
            "Using the previous task's result, write the final reply:\n"
            "- Products found: call rank_products with their IDs, then reply "
            "with the top 2-3 as short bullets (name, price, one key spec), then "
            "one line recommending the best value option and why.\n"
            "- General message: 2-4 warm lines mentioning the available "
            "categories, inviting the user to name what they need.\n"
            "- Product request, no matches: briefly say nothing matched, list "
            "the categories, ask them to rephrase or pick one.\n\n"
            "Reply in the same language the user used. Keep it short (3-6 "
            "lines), plain formatting, no big markdown headers, friendly "
            "professional tone."
        ),
        expected_output="A short, clear final reply in the user's language.",
        agent=advisor_agent,
        context=[search_task],
    )

    crew = Crew(
        agents=[search_agent, advisor_agent],
        tasks=[search_task, advisor_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()
    return str(result)