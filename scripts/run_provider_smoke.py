"""Read-only PriceInIndia MCP coverage smoke test; requires mcp and outbound network."""
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ENDPOINT = "https://mcp.priceinindia.website/mcp"
QUERIES = {
    "electronics": ["Samsung Galaxy S26 256GB", "Apple Watch", "Apple Watch strap", "Sony WH-1000XM5", "MacBook Air M4 16GB", "iPad Air M3 11 inch", "NVIDIA RTX 5070", "PlayStation 5 Slim Disc Edition", "Samsung 45W USB-C charger", "TP-Link Archer AX55 router", "27 inch 144Hz monitor", "Canon mirrorless camera", "Samsung 55 inch OLED TV", "Logitech wireless mouse", "JBL Bluetooth speaker", "WD 1TB external hard drive"],
    "fashion": ["Nike men's running shoes UK 8", "Levi's men's jeans waist 32", "Zara women's cotton shirt size M", "Titan analog wrist watch"],
    "home_appliances": ["LG 1.5 ton inverter split AC", "Samsung 8kg front load washing machine", "Whirlpool 300 litre refrigerator", "Philips air fryer 4.2 litre"],
    "books_stationery": ["NCERT Class 10 Science textbook English", "HC Verma Concepts of Physics Volume 1", "Operating Systems 4th Edition paperback", "Classmate 200 page notebook pack of 6"],
    "sports_fitness": ["5kg cast iron dumbbell", "Yonex badminton racket", "Nivia football size 5", "Yoga mat 6mm"],
    "furniture_home": ["Wakefit queen size memory foam mattress", "3 seater fabric sofa", "IKEA study table 120cm", "Nilkamal plastic chair"],
}


async def search(session, query):
    result = await session.call_tool("search_products", {"query": query, "sort": "price_asc", "page": 1, "per_page": 20})
    if getattr(result, "isError", False): return {"query": query, "error": "Provider returned a tool error", "offers": []}
    payload = getattr(result, "structuredContent", None)
    if payload is None:
        texts = [item.text for item in (getattr(result, "content", []) or []) if getattr(item, "type", None) == "text"]
        try: payload = json.loads(texts[0]) if texts else {}
        except (IndexError, json.JSONDecodeError): payload = {}
    rows = payload if isinstance(payload, list) else payload.get("products", payload.get("items", [])) if isinstance(payload, dict) else []
    return {"query": query, "mapped_provider_rows": len(rows) if isinstance(rows, list) else 0, "offers": [{"title": row.get("title"), "price": row.get("price"), "store": row.get("store"), "url": row.get("productUrl") or row.get("productPageUrl"), "out_of_stock": row.get("outOfStock", False)} for row in rows[:20] if isinstance(row, dict)]}


async def main():
    async with streamablehttp_client(ENDPOINT, timeout=25) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            for domain, queries in QUERIES.items():
                for query in queries:
                    try: result = await asyncio.wait_for(search(session, query), timeout=30)
                    except Exception as exc: result = {"query": query, "error": type(exc).__name__, "offers": []}
                    print(json.dumps({"domain": domain, **result}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
