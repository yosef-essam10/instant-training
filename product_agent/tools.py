import os
import re
import json
import time
from tavily import TavilyClient
from groq import Groq, RateLimitError


def search_products(query, max_results=4):
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_raw_content=True,
    )
    results = []
    for item in response.get("results", []):
        content = item.get("raw_content") or item.get("content") or ""
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": content,
        })
    return results


def scrape_product(item, max_retries=3):
    content = item.get("content", "")
    if not content or len(content.strip()) < 50:
        return None
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = (
        "Extract the product name, price in numeric USD, cpu, ram, storage, "
        "display size, and battery life from this page content. "
        "Return strict JSON only with keys: name, price, cpu, ram, storage, display, battery. "
        "Use null for any field you cannot find. If this page is not about a specific "
        "product for sale, return all fields as null.\n\n"
        f"Page title: {item.get('title', '')}\n"
        f"Page content:\n{content[:3000]}"
    )
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            data = json.loads(completion.choices[0].message.content)
            break
        except RateLimitError:
            if attempt == max_retries - 1:
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            return None
    if not data.get("name"):
        return None
    data["source_url"] = item.get("url", "")
    return data


def scrape_all(items):
    products = []
    for item in items:
        data = scrape_product(item)
        if data:
            products.append(data)
        time.sleep(1)
    return products


def clean_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[\d,]+\.?\d*", str(value))
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def clean_ram(value):
    if not value:
        return None
    match = re.search(r"(\d+)\s*GB", str(value), re.IGNORECASE)
    if match:
        return f"{match.group(1)}GB"
    return str(value)


def clean_storage(value):
    if not value:
        return None
    return str(value).upper().replace(" ", "")


def clean_cpu(value):
    if not value:
        return None
    return str(value).strip()


def clean_products(products):
    cleaned = []
    for product in products:
        cleaned.append({
            "name": product.get("name", "Unknown"),
            "price": clean_price(product.get("price")),
            "cpu": clean_cpu(product.get("cpu")),
            "ram": clean_ram(product.get("ram")),
            "storage": clean_storage(product.get("storage")),
            "display": product.get("display"),
            "battery": product.get("battery"),
            "source_url": product.get("source_url"),
        })
    return cleaned