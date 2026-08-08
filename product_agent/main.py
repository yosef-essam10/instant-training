import os
import json
from dotenv import load_dotenv
from tools import search_products, scrape_all, clean_products
from crew import run_comparison_and_report

load_dotenv()


def load_company_context(path="config/company.json"):
    with open(path, "r") as f:
        return json.load(f)


def run_pipeline(query, company_context):
    search_results = search_products(query)
    raw_products = scrape_all(search_results)
    products = clean_products(raw_products)
    ranking, html_report = run_comparison_and_report(products, company_context)
    return products, ranking, html_report


if __name__ == "__main__":
    context = load_company_context()
    query = f"Best {context['product']} under {context['budget']} dollars"
    products, ranking, html_report = run_pipeline(query, context)

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/products.json", "w") as f:
        json.dump(products, f, indent=2)
    with open("outputs/ranking.json", "w") as f:
        json.dump(ranking, f, indent=2)
    with open("outputs/report.html", "w") as f:
        f.write(html_report)

    print("Pipeline finished. Check the outputs folder.")