"""Static guards for the local infrastructure definition; no Docker is needed to run them."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

COMPOSE = Path(__file__).parents[5] / "infra" / "docker" / "compose.yml"
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
CREDENTIAL_VARIABLES = {
    "POSTGRES_PASSWORD",
    "MINIO_ROOT_PASSWORD",
    "MINIO_ROOT_USER",
    "REDIS_PASSWORD",
}


@pytest.fixture(scope="module")
def compose() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return loaded


def test_project_is_named_and_defines_the_four_infrastructure_services(
    compose: dict[str, Any],
) -> None:
    assert compose["name"] == "shaidago"
    assert {"postgres", "redis", "minio", "minio-init", "clamav"} == set(compose["services"])


def test_every_image_is_pinned_by_digest(compose: dict[str, Any]) -> None:
    for name, service in compose["services"].items():
        assert DIGEST.search(service["image"]), f"{name} image is not digest-pinned"


def test_every_published_port_is_loopback_by_default(compose: dict[str, Any]) -> None:
    for name, service in compose["services"].items():
        for port in service.get("ports", []):
            assert port.startswith("${INFRA_BIND_ADDRESS:-127.0.0.1}:"), f"{name}: {port}"


def test_no_default_credentials_are_embedded(compose: dict[str, Any]) -> None:
    for name, service in compose["services"].items():
        environment: dict[str, object] = service.get("environment") or {}
        for key, value in environment.items():
            if key in CREDENTIAL_VARIABLES | {"REDISCLI_AUTH"}:
                assert str(value).startswith("${"), f"{name}.{key} is a literal"
                assert ":-" not in str(value), f"{name}.{key} has a default"
    redis_command = " ".join(compose["services"]["redis"]["command"])
    assert "${REDIS_PASSWORD:?" in redis_command


def test_long_running_services_have_health_checks_and_memory_limits(
    compose: dict[str, Any],
) -> None:
    for name in ("postgres", "redis", "minio", "clamav"):
        service = compose["services"][name]
        assert "healthcheck" in service, name
        assert "mem_limit" in service, name


def test_clamav_readiness_is_the_signature_aware_check_and_is_optional(
    compose: dict[str, Any],
) -> None:
    clamav = compose["services"]["clamav"]
    assert clamav["profiles"] == ["scanner"]
    assert "clamdcheck.sh" in " ".join(clamav["healthcheck"]["test"])


def test_state_lives_in_named_volumes_and_the_bucket_is_made_private(
    compose: dict[str, Any],
) -> None:
    assert set(compose["volumes"]) == {"postgres_data", "redis_data", "minio_data", "clamav_db"}
    init = " ".join(compose["services"]["minio-init"]["command"])
    assert "mc anonymous set none" in init
    assert "--ignore-existing" in init
    assert compose["services"]["redis"]["command"].count("everysec") == 1


def test_makefile_infra_targets_use_the_fixed_project_and_guard_destruction() -> None:
    makefile = (Path(__file__).parents[5] / "Makefile").read_text(encoding="utf-8")
    assert "--project-name shaidago" in makefile
    clean = makefile.split("infra-clean: infra-check-env", 1)[1]
    assert 'CONFIRM_DESTROY_SHAIDAGO_DATA)" = "yes"' in clean
    assert clean.index("CONFIRM_DESTROY_SHAIDAGO_DATA") < clean.index("--volumes")
