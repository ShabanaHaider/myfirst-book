import requests
import json

def test_api_connection():
    """Test the connection between frontend and backend"""
    backend_url = "http://localhost:8001/chat"

    print("Testing API connection...")
    print(f"Connecting to: {backend_url}")

    # Test data that matches what the frontend would send
    test_message = {"message": "Hello, this is a test message from frontend"}

    try:
        response = requests.post(
            backend_url,
            json=test_message,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("SUCCESS: API connection successful!")
            try:
                data = response.json()
                print(f"Response data: {data}")
            except:
                print("Response is not JSON format")
        else:
            print(f"FAILED: API connection failed with status {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("FAILED: Connection error: Could not connect to the backend server")
        print("Make sure the backend server is running on http://localhost:8001")
    except requests.exceptions.Timeout:
        print("FAILED: Timeout error: Request took too long to complete")
    except Exception as e:
        print(f"FAILED: Error: {str(e)}")

if __name__ == "__main__":
    test_api_connection()