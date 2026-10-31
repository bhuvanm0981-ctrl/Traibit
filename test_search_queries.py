from dotenv import load_dotenv
from backend.services.tinyfish import TinyFishClient

load_dotenv()
client = TinyFishClient()

queries = [
    '"good first issue" Python GitHub',
    'site:github.com "good first issue" Python',
    'Python beginner open source GitHub issues',
    'GitHub Python repositories issues labeled good first issue',
    'site:github.com/*/*/issues Python beginner contribution',
]

for query in queries:
    print("\n" + "=" * 70)
    print("QUERY:", query)

    try:
        data = client.search(query)
        results = data.get("results", [])

        print("RESULT COUNT:", len(results))

        for item in results[:10]:
            print("\nTITLE:", item.get("title"))
            print("URL:", item.get("url"))
            print("SNIPPET:", (item.get("snippet") or "")[:200])

    except Exception as error:
        print("ERROR:", type(error).__name__, str(error))
