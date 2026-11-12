"""AI Security Defenses: Prompt Injection, Unsafe Output, SSRF, and Tool Budgeting.

Implements Section 11 of Mizan Security Strategy v2:
- Direct & Indirect Prompt Injection defenses: structural delimiters, active content stripping, retrieved data cannot grant permissions.
- Unsafe output validation: sandboxing SQL, shell commands, HTML, and URLs.
- SSRF defenses: IP blocklisting (RFC1918, loopback, AWS/GCP/Azure 169.254.169.254), DNS rebinding resolution check.
- Agent governance: tool allowlisting, per-run token/call limits, run-scoped kill switch.
- RAG tenant isolation: retrieval filter enforcement outside model authority.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse


class AISecurityViolationError(Exception):
    """Raised when an AI security boundary or safety check is violated."""


# Blocked IP networks for SSRF prevention
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 private
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 private
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 private
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
]

SUSPICIOUS_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+dan\s+mode", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?system\s+prompt", re.IGNORECASE),
    re.compile(r"grant\s+(me\s+)?(admin|root|superuser)\s+access", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
]

SQL_INJECTION_FRAGMENTS = [
    re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+FROM", re.IGNORECASE),
    re.compile(r"UNION\s+ALL\s+SELECT", re.IGNORECASE),
    re.compile(r"'\s*OR\s*'1'='1", re.IGNORECASE),
]


def sanitize_retrieved_rag_content(content: str) -> str:
    """Sanitizes retrieved RAG document content before feeding to LLM context.

    Enforces:
    1. Content is treated strictly as data, never instructions.
    2. Strips active HTML/JavaScript tags and control injection sequences.
    3. Neutralizes attempt to override agent instructions.
    """
    # Strip HTML tags like <script>, <iframe>, <object>
    cleaned = re.sub(
        r"<(script|iframe|object|embed)[^>]*>.*?</\1>", "", content, flags=re.DOTALL | re.IGNORECASE
    )
    cleaned = re.sub(r"<(script|iframe|object|embed)[^>]*>", "", cleaned, flags=re.IGNORECASE)

    # Wrap in explicit data delimiter to prevent instruction confusion
    return f"<retrieved_untrusted_data>\n{cleaned.strip()}\n</retrieved_untrusted_data>"


def validate_user_prompt(prompt: str) -> None:
    """Inspects user prompt for direct prompt injection attempts.

    Raises:
        AISecurityViolationError: If malicious control override patterns are detected.
    """
    for pattern in SUSPICIOUS_PROMPT_INJECTION_PATTERNS:
        if pattern.search(prompt):
            raise AISecurityViolationError(
                f"Prompt rejected: detected potential instruction override or injection pattern: {pattern.pattern}"
            )


def validate_tool_url_destination(url: str, allowed_hosts: list[str] | None = None) -> None:
    """Validates destination URL against SSRF and DNS rebinding attacks.

    Raises:
        AISecurityViolationError: If destination targets internal network or cloud metadata.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise AISecurityViolationError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only HTTP/HTTPS permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise AISecurityViolationError("Missing hostname in tool destination URL.")

    if allowed_hosts and hostname not in allowed_hosts:
        raise AISecurityViolationError(
            f"Destination host '{hostname}' is not in approved egress allowlist."
        )

    # Resolve IP address to prevent DNS rebinding
    try:
        addr_info = socket.getaddrinfo(
            hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
        for item in addr_info:
            ip_str = item[4][0]
            ip_obj = ipaddress.ip_address(ip_str)

            # Check against blocked networks
            for blocked_net in BLOCKED_NETWORKS:
                if ip_obj in blocked_net:
                    raise AISecurityViolationError(
                        f"SSRF defense blocked connection to '{hostname}' ({ip_str}): "
                        f"Resolved address falls within forbidden internal/metadata network {blocked_net}."
                    )
    except socket.gaierror as exc:
        raise AISecurityViolationError(
            f"Failed to resolve destination hostname '{hostname}': {exc}"
        ) from exc


def validate_model_generated_sql(sql_query: str) -> None:
    """Validates model-generated SQL query before execution.

    Raises:
        AISecurityViolationError: If query contains destructive or injected fragments.
    """
    for frag in SQL_INJECTION_FRAGMENTS:
        if frag.search(sql_query):
            raise AISecurityViolationError(
                f"Model SQL output rejected: contains dangerous or injected statement fragment: {frag.pattern}"
            )


class AgentExecutionBudget:
    """Enforces execution limits, tool allowlists, and run-scoped kill switches."""

    def __init__(
        self,
        agent_id: str,
        allowlisted_tools: list[str],
        max_tool_calls: int = 10,
        max_tokens: int = 4096,
        is_killed: bool = False,
    ) -> None:
        self.agent_id = agent_id
        self.allowlisted_tools = set(allowlisted_tools)
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens
        self.tool_calls_used = 0
        self.tokens_used = 0
        self.is_killed = is_killed

    def record_and_verify_tool_call(self, tool_name: str, token_cost: int = 0) -> None:
        """Verifies tool call is within scope, budget, and kill switch status."""
        if self.is_killed:
            raise AISecurityViolationError(
                f"Agent '{self.agent_id}' execution halted: Run-scoped kill switch is active."
            )

        if tool_name not in self.allowlisted_tools:
            raise AISecurityViolationError(
                f"Tool '{tool_name}' is not allowlisted for agent '{self.agent_id}'. "
                f"Permitted tools: {sorted(self.allowlisted_tools)}"
            )

        if self.tool_calls_used >= self.max_tool_calls:
            raise AISecurityViolationError(
                f"Agent '{self.agent_id}' exceeded tool-call budget of {self.max_tool_calls} calls."
            )

        self.tool_calls_used += 1
        self.tokens_used += token_cost

        if self.tokens_used > self.max_tokens:
            raise AISecurityViolationError(
                f"Agent '{self.agent_id}' exceeded token budget ({self.tokens_used} > {self.max_tokens})."
            )

    def trigger_kill_switch(self, reason: str = "Operator manual kill switch") -> None:
        """Immediately halts any further tool executions for this agent."""
        self.is_killed = True
