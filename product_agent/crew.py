import json
import re
import time
from crewai import Crew, Process
from agents import build_comparison_agent, build_report_agent
from tasks import build_comparison_task, build_report_task


def extract_json(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(0))
    except Exception:
        return []


def extract_html(text):
    match = re.search(r"<!DOCTYPE html.*</html>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0)
    match = re.search(r"<html.*</html>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return "<!DOCTYPE html>\n" + match.group(0)
    return text


def kickoff_with_retry(crew, max_retries=3):
    for attempt in range(max_retries):
        try:
            return str(crew.kickoff())
        except Exception as e:
            is_rate_limit = "rate_limit" in str(e).lower() or "RateLimitError" in type(e).__name__
            if not is_rate_limit or attempt == max_retries - 1:
                raise
            time.sleep(15 * (attempt + 1))


def run_comparison_and_report(clean_products, company_context):
    comparison_agent = build_comparison_agent()
    comparison_task = build_comparison_task(
        comparison_agent,
        json.dumps(clean_products),
        json.dumps(company_context),
    )
    comparison_crew = Crew(
        agents=[comparison_agent],
        tasks=[comparison_task],
        process=Process.sequential,
        verbose=False,
    )
    ranking_raw = kickoff_with_retry(comparison_crew)
    ranking_json = extract_json(ranking_raw)

    report_agent = build_report_agent()
    report_task = build_report_task(
        report_agent,
        json.dumps(ranking_json),
        json.dumps(company_context),
    )
    report_crew = Crew(
        agents=[report_agent],
        tasks=[report_task],
        process=Process.sequential,
        verbose=False,
    )
    report_raw = kickoff_with_retry(report_crew)
    html_report = extract_html(report_raw)

    return ranking_json, html_report