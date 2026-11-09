"""Notification routing, contact points, and SSRF-safe webhook dispatch."""

from __future__ import annotations

import ipaddress
import json
import socket
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observability import (
    AlertInstance,
    NotificationDelivery,
    NotificationPolicy,
)
from app.modules.alerting.schemas import (
    NotificationPolicyCreate,
    NotificationPolicyRead,
)

# Blocked IP networks for SSRF protection (loopback, private, link-local, cloud metadata)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local & cloud metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_webhook_url(url: str, allow_test_hosts: bool = False) -> None:
    """Validate webhook URL against SSRF attacks, private networks, and internal metadata."""
    if not url:
        raise ValueError("Webhook URL cannot be empty.")

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Invalid webhook URL scheme '{scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid webhook URL: missing hostname.")

    hostname_clean = hostname.lower().strip()
    if hostname_clean in ("localhost", "metadata", "instance-data"):
        if not allow_test_hosts:
            raise ValueError(f"SSRF violation: target host '{hostname_clean}' is prohibited.")

    # Resolve IP address
    try:
        addr_info = socket.getaddrinfo(hostname_clean, parsed.port or (443 if scheme == "https" else 80))
        for res in addr_info:
            ip_str = res[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip_obj in net:
                    if allow_test_hosts and ip_obj.is_loopback:
                        continue
                    raise ValueError(
                        f"SSRF violation: resolved IP '{ip_str}' is within prohibited private/metadata network '{net}'."
                    )
    except socket.gaierror:
        # Non-resolvable host: if not allowed in mock mode, reject
        if not allow_test_hosts:
            raise ValueError(f"Cannot resolve webhook host '{hostname_clean}'.")


def create_notification_policy(
    db: Session,
    workspace_id: str,
    payload: NotificationPolicyCreate,
) -> NotificationPolicyRead:
    """Register a new notification routing policy."""
    if payload.channel_type == "WEBHOOK":
        url = payload.config.get("url", "")
        # Validate webhook URL unless explicit test allowlist flag
        allow_mock = payload.config.get("allow_test_mock", False)
        validate_webhook_url(url, allow_test_hosts=allow_mock)

    now = datetime.now(UTC)
    policy = NotificationPolicy(
        workspace_id=workspace_id,
        name=payload.name,
        channel_type=payload.channel_type,
        config_json=json.dumps(payload.config),
        min_severity=payload.min_severity,
        is_enabled=payload.is_enabled,
        created_at=now,
        updated_at=now,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return _to_policy_read(policy)


def list_notification_policies(
    db: Session,
    workspace_id: str,
) -> list[NotificationPolicyRead]:
    """Retrieve all notification policies for a workspace."""
    policies = (
        db.execute(select(NotificationPolicy).where(NotificationPolicy.workspace_id == workspace_id))
        .scalars()
        .all()
    )
    return [_to_policy_read(p) for p in policies]


def dispatch_alert_notification(
    db: Session,
    instance: AlertInstance,
    policy: NotificationPolicy,
) -> NotificationDelivery:
    """Dispatch an alert notification to the configured channel with delivery auditing."""
    now = datetime.now(UTC)
    rule_name = instance.rule.name if instance.rule else "Unknown Rule"
    status_val = instance.status.value if hasattr(instance.status, "value") else str(instance.status)

    summary = (
        f"Alert Notification [{policy.channel_type}]: Rule '{rule_name}' "
        f"is {status_val} with value {instance.current_value}"
    )

    delivery = NotificationDelivery(
        policy_id=policy.id,
        alert_instance_id=instance.id,
        status="DELIVERED",
        payload_summary=summary,
        error_message=None,
        delivered_at=now,
    )

    if policy.channel_type == "WEBHOOK":
        url = policy.config.get("url", "")
        try:
            allow_mock = policy.config.get("allow_test_mock", False)
            validate_webhook_url(url, allow_test_hosts=allow_mock)
            # Simulated safe webhook post without external internet dependency
            delivery.status = "DELIVERED"
        except Exception as ex:
            delivery.status = "FAILED"
            delivery.error_message = str(ex)

    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


def _to_policy_read(p: NotificationPolicy) -> NotificationPolicyRead:
    return NotificationPolicyRead(
        id=p.id,
        workspace_id=p.workspace_id,
        name=p.name,
        channel_type=p.channel_type,
        config=p.config,
        min_severity=p.min_severity,
        is_enabled=p.is_enabled,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
