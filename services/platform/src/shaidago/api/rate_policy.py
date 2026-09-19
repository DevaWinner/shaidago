"""Every rate-limit key the API uses, in one reviewable table.

A test scans the source for ``sg:rl:`` keys and fails if one is not listed here, so a new limiter
cannot be added without stating whose budget it spends, how large it is, and what happens when
Redis is down. Keys hold only pseudonymous or internal identifiers: the BFF's rotating client HMAC
(never an IP address), a tracking-code *prefix bucket* (never a code), or a reviewer ID.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Policy:
    prefix: str
    subject: str
    setting: str
    window: str
    on_unavailable: str


# Redis unavailable is ``503 dependency_unavailable`` for every policy: an abuse control that
# silently turns off is worse than a brief outage, and no expensive provider call is ever made
# without its limiter. The browser keeps an unsent report draft, so a valid report is not lost.
POLICIES: Final[tuple[Policy, ...]] = (
    Policy("sg:rl:signin:client:", "client HMAC", "sign_in_per_15_minutes", "15 minutes", "closed"),
    Policy(
        "sg:rl:signin:pair:", "client HMAC and identifier digest", "fixed 5", "15 minutes", "closed"
    ),
    Policy("sg:rl:submit:", "client HMAC", "submission_per_hour", "1 hour", "closed"),
    Policy(
        "sg:rl:track:",
        "client HMAC or code-prefix bucket",
        "tracking_lookup_per_hour",
        "1 hour",
        "closed",
    ),
    Policy(
        "sg:rl:handle:",
        "client HMAC or handle bucket",
        "handle_verify_per_hour",
        "1 hour",
        "closed",
    ),
    Policy("sg:rl:qa:client:", "client HMAC", "qa_per_hour", "1 hour", "closed"),
    Policy(
        "sg:rl:qa:global", "everyone (provider budget)", "qa_global_per_hour", "1 hour", "closed"
    ),
    Policy(
        "sg:rl:discovery:reviewer:",
        "reviewer ID",
        "discovery_reviewer_per_hour",
        "1 hour",
        "closed",
    ),
    Policy("sg:rl:discovery:", "client HMAC", "discovery_per_hour", "1 hour", "closed"),
    Policy("sg:rl:reviewer:read:", "reviewer ID", "reviewer_read_per_minute", "1 minute", "closed"),
    Policy(
        "sg:rl:reviewer:write:", "reviewer ID", "reviewer_write_per_minute", "1 minute", "closed"
    ),
)
