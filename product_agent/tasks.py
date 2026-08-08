from crewai import Task


def build_comparison_task(agent, products_json, company_context_json):
    return Task(
        description=(
            f"Company context: {company_context_json}\n"
            f"Products data (JSON): {products_json}\n"
            "Rank these products based on price, specs, and value using weight_price "
            "and weight_specs from the company context. "
            "Detect whether the company context and product data are written in "
            "Arabic or English, and write the 'reason' field in that same language. "
            "If the language is unclear or mixed, default to English. "
            "Return ONLY a valid JSON array ordered best to worst with fields: "
            "rank, name, price, cpu, ram, score, reason. No extra text."
        ),
        expected_output="A valid JSON array of ranked products",
        agent=agent,
    )


def build_report_task(agent, ranking_json, company_context_json):
    return Task(
        description=(
            f"Company context: {company_context_json}\n"
            f"Ranking result (JSON): {ranking_json}\n"
            "Detect whether the company context and ranking data are written in "
            "Arabic or English, and write all report text (title, headings, "
            "recommendation, reasons) in that same language. If the language is "
            "unclear or mixed, default to English. "
            "Generate a complete, professional, self-contained HTML procurement report. "
            "Include a title, company info, the top recommendation, a full ranking table "
            "with reasons, and modern colorful inline CSS styling. "
            "Set the HTML lang and dir attributes correctly (dir=\"rtl\" for Arabic). "
            "Output ONLY the raw HTML starting with <!DOCTYPE html>."
        ),
        expected_output="A complete standalone HTML document",
        agent=agent,
    )