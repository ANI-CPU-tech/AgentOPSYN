# integrations/handshakes.py
import requests


def verify_github(token: str) -> bool:
    """Makes a lightweight request to GitHub to verify the Personal Access Token."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        response = requests.get(
            "https://api.github.com/user", headers=headers, timeout=5
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def verify_jira(domain: str, email: str, token: str) -> bool:
    """Verifies Jira credentials by requesting the user's profile."""
    # Ensure domain doesn't end with a trailing slash
    clean_domain = domain.rstrip("/")
    url = f"{clean_domain}/rest/api/3/myself"

    try:
        response = requests.get(url, auth=(email, token), timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def verify_slack(webhook_url: str) -> bool:
    """
    Slack webhooks cannot be easily pinged without sending a message.
    Instead, we verify it matches the strict Slack Webhook URL format.
    """
    if not webhook_url:
        return False
    return webhook_url.startswith("https://hooks.slack.com/services/")


def verify_notion(token: str) -> bool:
    """
    Verifies a Notion Internal Integration Secret by fetching the
    bot user information associated with the token.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",  # Standard stable Notion API version
    }
    try:
        # This endpoint is specifically designed to check the identity/validity of the token
        response = requests.get(
            "https://api.notion.com/v1/users/me", headers=headers, timeout=5
        )
        # Returns 200 if the token is valid and authorized for the workspace
        return response.status_code == 200
    except requests.RequestException:
        return False
