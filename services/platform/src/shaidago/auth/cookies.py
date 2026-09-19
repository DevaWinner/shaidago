"""The reviewer session cookie contract.

FastAPI owns session creation and validity and returns the raw token once, to the trusted BFF, in
a ``no-store`` internal response. The BFF sets the final same-origin cookie using the policy
below, so browser JavaScript never sees the token. Deployed environments require the ``__Host-``
prefix (Secure, Path=/, no Domain); development uses a plain name without ``Secure`` because
WebKit rejects Secure cookies on http://localhost.
"""

from dataclasses import dataclass
from typing import Final

from shaidago.shared.config import AuthSettings

HOST_PREFIX: Final = "__Host-"
SAME_SITE: Final = "Lax"


@dataclass(frozen=True)
class CookiePolicy:
    name: str
    secure: bool
    max_age_seconds: int
    http_only: bool = True
    same_site: str = SAME_SITE
    path: str = "/"

    @classmethod
    def from_settings(cls, auth: AuthSettings) -> CookiePolicy:
        return cls(
            name=auth.session_cookie_name,
            secure=auth.session_cookie_secure,
            max_age_seconds=auth.session_absolute_hours * 3600,
        )

    def set_cookie(self, token: str, *, max_age_seconds: int | None = None) -> str:
        """The exact ``Set-Cookie`` value for a new session. No ``Domain`` attribute, ever."""
        age = self.max_age_seconds if max_age_seconds is None else max_age_seconds
        return self._render(token, age)

    def clear_cookie(self) -> str:
        return self._render("", 0)

    def _render(self, value: str, age: int) -> str:
        parts = [f"{self.name}={value}", f"Path={self.path}", f"Max-Age={age}"]
        if self.secure:
            parts.append("Secure")
        parts += ["HttpOnly", f"SameSite={self.same_site}"]
        return "; ".join(parts)
