import requests
import json


def test_retrieval_only():
    """Test just the retrieval system without LLM generation."""
    print("Testing retrieval system without LLM generation...")

    # Test the query endpoint to see if it can retrieve documents
    query_url = "http://localhost:8001/api/v1/query"

    # Test query that should match the ingested robotics documents
    test_query = {
        "query": "What is ROS2?",
        "top_k": 3,
        "similarity_threshold": 0.5,
        "include_sources": True
    }

    print(f"Sending query to: {query_url}")
    print(f"Query: {test_query['query']}")

    try:
        response = requests.post(
            query_url,
            json=test_query,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Query endpoint responded with data")
            print(f"Response keys: {list(data.keys())}")

            if "sources" in data and data["sources"]:
                print(f"SUCCESS: Found {len(data['sources'])} source documents")
                for i, source in enumerate(data["sources"][:2]):  # Show first 2 sources
                    print(f"  Source {i+1}: {source.get('source_file_path', 'Unknown')}")
                    print(f"    Similarity: {source.get('similarity_score', 'N/A')}")
                    print(f"    Snippet: {source.get('snippet', '')[:100]}...")
            else:
                print("INFO: No sources found, but API responded successfully")

            if "response" in data:
                print(f"Response preview: {data['response'][:100]}...")
        else:
            print(f"FAILED: Query endpoint returned status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("FAILED: Could not connect to the backend server")
        print("Make sure the backend server is running on http://localhost:8001")
    except Exception as e:
        print(f"FAILED: Error occurred: {str(e)}")


if __name__ == "__main__":
    test_retrieval_only()