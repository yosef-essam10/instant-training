import os
from crewai import Agent, LLM


def get_llm():
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
    )


def build_comparison_agent():
    return Agent(
        role="Procurement Comparison Analyst",
        goal="Rank products based on price, specs, and value according to company requirements",
        backstory="Expert procurement analyst specialized in IT hardware sourcing",
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
    )


def build_report_agent():
    return Agent(
        role="Procurement Report Writer",
        goal="Generate a clean, professional HTML procurement report",
        backstory="Senior technical writer producing executive procurement reports",
        llm=get_llm(),
        verbose=False,
        allow_delegation=False,
    )
