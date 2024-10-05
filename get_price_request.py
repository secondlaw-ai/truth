import requests
import os
from dotenv import load_dotenv

"""Graph endpoints dont work..."""

load_dotenv()
api_key = os.environ["GRAPH_API_KEY"]


# Define the endpoint (replace {api-key} with your actual API key)
endpoint = f"https://gateway.thegraph.com/api/{api_key}/subgraphs/id/8pZ6FngVvxRY8PcHWcVLmgx713jnFsoF3kMCfBfxZ6y7"

# Define the GraphQL query
query = """
{
  users(first: 5) {
    id
    address
    votingTokenHolder {
      id
    }
    votesCommited {
      id
    }
  }
  votingTokenHolders(first: 5) {
    id
    address
    votingTokenBalance
    votingTokenBalanceRaw
  }
}
"""


def fetch_data():
    try:
        # Send the HTTP request
        response = requests.post(endpoint, json={"query": query})

        # Check for a successful response
        response.raise_for_status()

        # Print the data
        data = response.json()
        print(data)

    except requests.exceptions.RequestException as error:
        print("Error fetching data:", error)


# Fetch the data
fetch_data()
