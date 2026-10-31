from dotenv import load_dotenv
import os
from backend.services.tinyfish import TinyFishClient

load_dotenv()

if not os.getenv("TINYFISH_API_KEY"):
    print("ERROR: API key was not loaded from .env")
    raise SystemExit(1)

client = TinyFishClient()

queries = [
    "site:github.com/issues Python good first issue",
    "GitHub Python beginner friendly open source issues",
]

for query in queries:
    print("\nQUERY:", query)

    try:
        data = client.search(query)

        print("Response type:", type(data).__name__)
        print("Response keys:", list(data.keys()) if isinstance(data, dict) else "Not a dictionary")

        results = data.get("results", []) if isinstance(data, dict) else []

        print("Result count:", len(results))

        for item in results[:5]:
            print({
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": (item.get("snippet") or "")[:150]
            })

    except Exception as error:
        print("ERROR:", type(error).__name__, str(error))
