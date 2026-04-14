from .github import GitHubAdapter
from .jira import JiraAdapter
from .slack import SlackAdapter
from .notion import NotionAdapter
from .datadog import DatadogAdapter

ADAPTER_MAP = {
    "github": GitHubAdapter,
    "jira": JiraAdapter,
    "slack": SlackAdapter,
    "notion": NotionAdapter,
    "datadog": DatadogAdapter,
}


def get_adapter(source: str):
    cls = ADAPTER_MAP.get(source)
    if not cls:
        raise ValueError(f"No adapter found for source: {source}")
    return cls()
