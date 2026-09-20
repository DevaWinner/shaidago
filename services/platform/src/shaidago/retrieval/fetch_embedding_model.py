"""Download the embedding model into a plain directory (``make embedding-model``).

Run as ``python -m shaidago.retrieval.fetch_embedding_model --dest DIR``.

Run at image build time (and once by a developer), never at request time. It fetches one exact
Hugging Face revision and then verifies every file against a SHA-256 digest recorded here, so a
compromised or silently updated upstream repository cannot change what runs in the API.

The files must land as real files in ``--dest``. The default Hugging Face cache stores them as
symlinks into a ``blobs/`` directory, and ONNX Runtime 1.30 rejects an external-data file that
resolves outside the model directory ("External data path escapes model directory"), which is why
``local_dir`` is used and why the result is verified rather than trusted.
"""

import argparse
import hashlib
import importlib
import sys
from pathlib import Path
from typing import Any, Final

REPOSITORY: Final = "qdrant/multilingual-e5-large-onnx"
# The Apache-2.0 ONNX conversion (Qdrant) of intfloat/multilingual-e5-large (MIT).
REVISION: Final = "66076b8dc6e367337e3e90e6fb309fb0f3addaf6"
CHUNK_BYTES: Final = 16 * 1024 * 1024

FILE_DIGESTS: Final[dict[str, str]] = {
    "model.onnx": "1c09780c907c8a91a77a6ab1fd231f79e090d2907ca431223703dfebeed3d36c",
    "model.onnx_data": "0cf1883fee81c63819a44e2ba0efa51d4043d9759685a4ebebbde97e0623d15c",
    "tokenizer.json": "f59925fcb90c92b894cb93e51bb9b4a6105c5c249fe54ce1c704420ac39b81af",
    "config.json": "1de8c3be1f344c0eefa4962480a006f8639f416dfafaa95a770e3cf4bceae6a4",
    "tokenizer_config.json": "f90024142df07163e5e6c5b9a6ad7c8c68b22a9112af11e3db4559a9ff90f737",
    "special_tokens_map.json": "8c785abebea9ae3257b61681b4e6fd8365ceafde980c21970d001e834cf10835",
}


class ModelIntegrityError(Exception):
    """A file is missing, is a symlink, or does not match its pinned digest."""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def verify(directory: Path) -> None:
    """Raise unless every pinned file is a regular file with the pinned digest."""
    for name, expected in FILE_DIGESTS.items():
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ModelIntegrityError(f"{name} is missing or is not a regular file")
        if sha256_of(path) != expected:
            raise ModelIntegrityError(f"{name} does not match its pinned SHA-256 digest")


def fetch(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    # Loaded here, and typed as Any, because the package's stubs leave its tqdm types unknown and
    # because the import is heavy and only wanted when actually downloading.
    hub: Any = importlib.import_module("huggingface_hub")
    hub.snapshot_download(
        repo_id=REPOSITORY,
        revision=REVISION,
        local_dir=destination,
        allow_patterns=list(FILE_DIGESTS),
    )
    verify(destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            verify(args.dest)
        else:
            fetch(args.dest)
    except ModelIntegrityError as error:
        sys.stderr.write(f"embedding model: {error}\n")
        return 1
    sys.stdout.write(f"embedding model: {REPOSITORY}@{REVISION[:12]} verified in {args.dest}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
