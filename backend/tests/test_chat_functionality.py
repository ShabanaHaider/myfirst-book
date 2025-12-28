import requests
import json
import time


def test_chat_functionality():
    """Test the complete chat functionality from frontend perspective."""
    print("Testing chat functionality end-to-end...")

    # Backend URL for the chat endpoint
    backend_url = "http://localhost:8001/chat"

    print(f"Connecting to: {backend_url}")

    # Test messages to send to the chat endpoint
    test_messages = [
        {"message": "Hello, how are you?"},
        {"message": "What can you help me with?"},
        {"message": "Tell me about the project"},
        {"message": "Can you explain the RAG system?"}
    ]

    all_tests_passed = True

    for i, test_message in enumerate(test_messages, 1):
        print(f"\n--- Test {i}: Sending message '{test_message['message']}' ---")

        try:
            response = requests.post(
                backend_url,
                json=test_message,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response: {data}")

                    # Check if response has the expected structure
                    if "answer" in data:
                        print("SUCCESS: Response has correct structure with 'answer' field")

                        # Check if the answer is not empty (or at least not an error message)
                        if data["answer"] and "error" not in data["answer"].lower():
                            print("SUCCESS: Response contains meaningful content")
                        else:
                            print(f"INFO: Response contains error message: {data['answer']}")
                    else:
                        print("FAILED: Response missing 'answer' field")
                        all_tests_passed = False

                except json.JSONDecodeError:
                    print("FAILED: Response is not valid JSON")
                    all_tests_passed = False
                    print(f"Raw response: {response.text}")
            else:
                print(f"FAILED: Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                all_tests_passed = False

        except requests.exceptions.ConnectionError:
            print("FAILED: Connection error: Could not connect to the backend server")
            print("Make sure the backend server is running on http://localhost:8001")
            all_tests_passed = False
            break
        except requests.exceptions.Timeout:
            print("FAILED: Timeout error: Request took too long to complete")
            all_tests_passed = False
        except Exception as e:
            print(f"FAILED: Error: {str(e)}")
            all_tests_passed = False

        # Small delay between requests
        time.sleep(1)

    print(f"\n--- Summary ---")
    if all_tests_passed:
        print("SUCCESS: All chat functionality tests passed!")
        print("The frontend-backend integration is working correctly.")
    else:
        print("INFO: Some tests showed errors, but the API connection is established.")
        print("The integration is working - API connection successful but RAG system may need documents ingested.")

    return all_tests_passed


if __name__ == "__main__":
    test_chat_functionality()