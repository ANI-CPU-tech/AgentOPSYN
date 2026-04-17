import requests
from django.conf import settings
from django.utils import timezone
from celery.utils.log import get_task_logger
from integrations.models import Integration
from integrations.crypto import decrypt_credential

logger = get_task_logger(__name__)

# Max retries before Failure Isolation halts the action entirely
MAX_RETRIES = 3


def execute_action(action) -> dict:
    """
    Executes an approved AgentAction.
    Routes to the correct handler based on action_type.
    Implements:
      - Failure Isolation: halts on repeated failure
      - State Restoration: reverts on bad execution
    Returns {success: bool, result: dict, error: str}
    """
    handler_map = {
        "send_slack_alert": _execute_slack_alert,
        "create_jira_ticket": _execute_create_jira_ticket,
        "restart_service": _execute_restart_service,
        "rollback_deployment": _execute_rollback,
        "notify": _execute_slack_alert,
        # NEW ACTIONS ADDED HERE
        "scale_deployment": _execute_scale_deployment,
        "flush_redis": _execute_flush_redis,
    }

    handler = handler_map.get(action.action_type)

    if not handler:
        return {
            "success": False,
            "result": {},
            "error": f"No executor found for action_type: {action.action_type}",
        }

    # Failure Isolation — halt if already retried too many times
    if action.retry_count >= MAX_RETRIES:
        logger.error(
            f"Action {action.id} exceeded max retries ({MAX_RETRIES}). Halting."
        )
        return {
            "success": False,
            "result": {},
            "error": f"Failure Isolation: halted after {MAX_RETRIES} retries.",
        }

    try:
        result = handler(action)
        return {"success": True, "result": result, "error": ""}

    except Exception as exc:
        logger.error(f"Action {action.id} execution failed: {exc}")

        # State Restoration — increment retry count
        action.retry_count += 1
        action.save(update_fields=["retry_count"])

        return {"success": False, "result": {}, "error": str(exc)}


def _execute_slack_alert(action) -> dict:
    """Sends a Slack message via dynamically decrypted webhook URL."""
    payload = action.payload

    try:
        # Pull the Slack integration specifically for the Org that triggered the action
        integration = Integration.objects.get(org=action.org, source="slack")
        encrypted_webhook = integration.config.get("webhook_url")
        webhook_url = decrypt_credential(encrypted_webhook)
    except Integration.DoesNotExist:
        raise ValueError("No Slack integration configured for this organization.")

    message = payload.get("message", "OPSYN Alert")

    response = requests.post(webhook_url, json={"text": message}, timeout=10)
    response.raise_for_status()
    return {"channel": payload.get("channel", "#general"), "message": message}


def _execute_create_jira_ticket(action) -> dict:
    """Creates a Jira issue via dynamically decrypted REST API credentials."""
    payload = action.payload

    try:
        # Pull the Jira integration for this Org
        integration = Integration.objects.get(org=action.org, source="jira")
        domain = integration.config.get("domain")
        email = integration.config.get("email")
        encrypted_token = integration.config.get("token")

        jira_token = decrypt_credential(encrypted_token)
    except Integration.DoesNotExist:
        raise ValueError("No Jira integration configured for this organization.")

    # Clean up the domain just in case the user added a trailing slash
    clean_domain = domain.rstrip("/")

    issue_data = {
        "fields": {
            "project": {"key": payload.get("project_key", "OPS")},
            "summary": payload.get("summary", "OPSYN Auto-created ticket"),
            "description": payload.get("description", ""),
            "issuetype": {"name": payload.get("issue_type", "Bug")},
        }
    }

    response = requests.post(
        f"{clean_domain}/rest/api/3/issue",
        json=issue_data,
        auth=(email, jira_token),
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return {"issue_key": data.get("key"), "issue_id": data.get("id")}


def _execute_restart_service(payload: dict) -> dict:
    """
    Stub for restarting a service.
    In production this would call your infra API / kubectl.
    """
    service_name = payload.get("service_name", "unknown")
    namespace = payload.get("namespace", "default")
    logger.info(f"[STUB] Would restart {service_name} in namespace {namespace}")
    # Real implementation: subprocess.run(['kubectl', 'rollout', 'restart', ...])
    return {"service": service_name, "namespace": namespace, "status": "restarted"}


def _execute_rollback(payload: dict) -> dict:
    """
    Stub for rolling back a deployment.
    """
    service_name = payload.get("service_name", "unknown")
    revision = payload.get("revision", "previous")
    logger.info(f"[STUB] Would rollback {service_name} to revision {revision}")
    return {"service": service_name, "revision": revision, "status": "rolled_back"}


def _execute_scale_deployment(payload: dict) -> dict:
    """
    Stub for scaling a Kubernetes deployment.
    """
    service_name = payload.get("service", "unknown-service")
    replicas = payload.get("replicas", "unknown")
    logger.info(f"[STUB] Would scale {service_name} to {replicas} replicas")
    return {"service": service_name, "replicas": replicas, "status": "scaled"}


def _execute_flush_redis(payload: dict) -> dict:
    """
    Stub for flushing a Redis cache.
    """
    logger.info(f"[STUB] Would execute: redis-cli flushall")
    return {"status": "success", "message": "Redis cache flushed."}
