"""The model download's integrity check: it must catch a missing, tampered or symlinked file."""

import hashlib
from pathlib import Path

import pytest

from shaidago.retrieval import fetch_embedding_model as fetch
from shaidago.retrieval.fetch_embedding_model import ModelIntegrityError, main, verify
from shaidago.retrieval.local_embeddings import ONNX_FILE


@pytest.fixture
def model_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A directory of tiny stand-in files whose digests replace the real pins for this test."""
    contents = {name: f"content of {name}".encode() for name in fetch.FILE_DIGESTS}
    for name, data in contents.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(data)
    monkeypatch.setattr(
        fetch, "FILE_DIGESTS", {n: hashlib.sha256(d).hexdigest() for n, d in contents.items()}
    )
    return tmp_path


def test_a_complete_matching_directory_verifies(model_dir: Path) -> None:
    verify(model_dir)


def test_a_missing_file_is_refused(model_dir: Path) -> None:
    (model_dir / "tokenizer.json").unlink()
    with pytest.raises(ModelIntegrityError, match=r"tokenizer\.json"):
        verify(model_dir)


def test_a_tampered_file_is_refused_by_its_digest(model_dir: Path) -> None:
    (model_dir / ONNX_FILE).write_bytes(b"replaced by an attacker")
    with pytest.raises(ModelIntegrityError, match=r"model_qint8_avx512_vnni\.onnx does not match"):
        verify(model_dir)


def test_a_symlink_is_refused_even_when_its_target_is_correct(
    model_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """A symlink's target is not the file that was verified, so it is refused."""
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "model.onnx"
    elsewhere.write_bytes((model_dir / ONNX_FILE).read_bytes())
    (model_dir / ONNX_FILE).unlink()
    (model_dir / ONNX_FILE).symlink_to(elsewhere)
    with pytest.raises(ModelIntegrityError, match="not a regular file"):
        verify(model_dir)


def test_the_pins_cover_every_file_the_model_needs_and_are_real_digests() -> None:
    assert {ONNX_FILE, "tokenizer.json", "config.json"} <= set(fetch.FILE_DIGESTS)
    assert fetch.REPOSITORY == "intfloat/multilingual-e5-small", "the publisher's own repository"
    for digest in fetch.FILE_DIGESTS.values():
        assert len(digest) == 64
        int(digest, 16)  # raises unless it is hexadecimal
    assert len(fetch.REVISION) == 40, "an exact commit, never a moving branch name"


def test_verify_only_reports_success_and_failure_through_the_exit_code(
    model_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--dest", str(model_dir), "--verify-only"]) == 0
    assert "verified" in capsys.readouterr().out
    (model_dir / "config.json").write_bytes(b"tampered")
    assert main(["--dest", str(model_dir), "--verify-only"]) == 1
    assert "config.json" in capsys.readouterr().err
