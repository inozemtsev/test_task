import os
import requests
from datetime import datetime, timedelta

api_key = os.environ.get("OPENAI_API_KEY")

# Calculate date range (last 30 days)
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

# Format dates as YYYY-MM-DD
start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

print(f"Fetching usage from {start_str} to {end_str}...")

# Try the usage endpoint
url = "https://api.openai.com/v1/usage"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

params = {
     "date": datetime.now().strftime("%Y-%m-%d")
}

try:
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")