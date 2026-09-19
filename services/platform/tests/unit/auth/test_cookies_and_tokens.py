import pytest
from hypothesis import given
from hypothesis import strategies as st

from shaidago.auth.cookies import CookiePolicy
from shaidago.auth.sessions import csrf_matches, csrf_token_for, token_hmac
from shaidago.shared.config import load_settings
from tests.factories import development_environ, production_environ

KEY = b"k" * 32
TOKEN = "T" * 43


def policy(**environ: str) -> CookiePolicy:
    return CookiePolicy.from_settings(load_settings(environ).auth)


def test_production_cookie_is_host_prefixed_secure_httponly_lax_with_no_domain() -> None:
    header = policy(**production_environ()).set_cookie(TOKEN)
    assert (
        header
        == f"__Host-sg_session={TOKEN}; Path=/; Max-Age=28800; Secure; HttpOnly; SameSite=Lax"
    )
    assert "Domain" not in header


def test_staging_uses_the_same_contract_as_production() -> None:
    header = policy(**(production_environ() | {"APP_ENV": "staging"})).set_cookie(TOKEN)
    assert header.startswith("__Host-sg_session=")
    assert "; Secure;" in header


def test_development_cookie_is_plain_named_and_not_secure_so_webkit_accepts_localhost() -> None:
    header = policy(**development_environ()).set_cookie(TOKEN)
    assert header == f"sg_session={TOKEN}; Path=/; Max-Age=28800; HttpOnly; SameSite=Lax"
    assert "Secure" not in header
    assert "__Host-" not in header


def test_clearing_a_cookie_expires_it_immediately_with_the_same_attributes() -> None:
    cleared = policy(**production_environ()).clear_cookie()
    assert cleared == "__Host-sg_session=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax"


def test_lifetime_follows_configuration() -> None:
    env = development_environ() | {"SESSION_ABSOLUTE_HOURS": "2"}
    assert policy(**env).set_cookie(TOKEN).count("Max-Age=7200") == 1


def test_token_hash_is_keyed_deterministic_and_hides_the_token() -> None:
    digest = token_hmac(KEY, TOKEN)
    assert digest == token_hmac(KEY, TOKEN)
    assert digest != token_hmac(b"q" * 32, TOKEN)
    assert digest != token_hmac(KEY, TOKEN[:-1] + "U")
    assert len(digest) == 32
    assert TOKEN.encode() not in digest


def test_csrf_token_is_bound_to_the_session_token_and_key_and_differs_from_its_hash() -> None:
    csrf = csrf_token_for(KEY, TOKEN)
    assert csrf == csrf_token_for(KEY, TOKEN)
    assert csrf != csrf_token_for(KEY, "U" * 43)
    assert csrf != csrf_token_for(b"q" * 32, TOKEN)
    assert csrf_matches(KEY, TOKEN, csrf)
    assert not csrf_matches(KEY, "U" * 43, csrf), "a CSRF token from another session is refused"
    assert not csrf_matches(KEY, TOKEN, "")
    assert token_hmac(KEY, TOKEN).hex() not in csrf


@given(st.text(max_size=100))
def test_arbitrary_csrf_input_never_matches_and_never_raises(presented: str) -> None:
    assert csrf_matches(KEY, TOKEN, presented) == (presented == csrf_token_for(KEY, TOKEN))


@pytest.mark.parametrize("bad", ["", "x", "é" * 5])
def test_non_ascii_csrf_values_are_compared_safely(bad: str) -> None:
    assert not csrf_matches(KEY, TOKEN, bad)
