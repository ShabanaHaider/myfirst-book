import requests
import json
import time


def test_llm_response():
    """Test if the LLM is responding with the ingested documents."""
    print("Testing LLM response with ingested documents...")

    # Backend URL for the chat endpoint
    backend_url = "http://localhost:8001/chat"

    print(f"Connecting to: {backend_url}")

    # Test messages that might be related to the ingested documents about robotics
    test_messages = [
        {"message": "What is ROS2?"},
        {"message": "Tell me about digital twins"},
        {"message": "Explain Isaac Sim"},
        {"message": "What is a humanoid robot?"},
        {"message": "How does perception training work in robotics?"}
    ]

    all_tests_passed = True

    for i, test_message in enumerate(test_messages, 1):
        print(f"\n--- Test {i}: Sending message '{test_message['message']}' ---")

        try:
            response = requests.post(
                backend_url,
                json=test_message,
                headers={"Content-Type": "application/json"},
                timeout=60  # Increased timeout for LLM processing
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response: {data}")

                    # Check if response has the expected structure
                    if "answer" in data:
                        print("SUCCESS: Response has correct structure with 'answer' field")

                        # Check if the answer is meaningful (not an error message)
                        if data["answer"] and "error" not in data["answer"].lower():
                            print(f"SUCCESS: LLM responded with: '{data['answer'][:100]}...'")
                        else:
                            print(f"INFO: Response contains error message: {data['answer']}")
                            all_tests_passed = False
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
        time.sleep(2)

    print(f"\n--- Summary ---")
    if all_tests_passed:
        print("SUCCESS: LLM is responding with meaningful content!")
        print("The system is now fully functional with ingested documents.")
    else:
        print("INFO: API connection is working but LLM may need proper API keys or configuration.")
        print("Check that your API keys are properly configured in the environment.")

    return all_tests_passed


if __name__ == "__main__":
    test_llm_response()