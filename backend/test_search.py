from duckduckgo_search import DDGS
import json

def test_search():
    print("Testing search for 'red dress'...")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(
                "red dress",
                max_results=5,
            ))
            print(f"Found {len(results)} results.")
            if results:
                print("First result:", json.dumps(results[0], indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
