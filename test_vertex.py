import urllib.request
import json
import subprocess

def get_token():
    result = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, shell=True)
    return result.stdout.strip()

def test_vertex():
    project = "multi-modal-multi-cloud-app"
    location = "us-central1"
    token = get_token()
    
    if not token:
        print("Failed to get gcloud access token. Ensure you are logged in using 'gcloud auth login'.")
        return

    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/gemini-1.5-flash:generateContent"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "contents": [{"role": "user", "parts": [{"text": "Hello! Reply 'Connected to Vertex AI successfully!' if you receive this."}]}]
    }
    
    print(f"Connecting to Vertex AI for project {project}...")
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print("Success!")
            print("Response:", result["candidates"][0]["content"]["parts"][0]["text"])
    except urllib.error.HTTPError as e:
        print(f"Failed with status code: {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_vertex()