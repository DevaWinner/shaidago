"""Download the embedding model into a plain directory (``make embedding-model``).

Run as ``python -m shaidago.retrieval.fetch_embedding_model --dest DIR``.

Run at image build time (and once by a developer), never at request time. It fetches one exact
Hugging Face revision and then verifies every file against a SHA-256 digest recorded here, so a
compromised or silently updated upstream repository cannot change what runs in the API.

The files must land as real files in ``--dest``: a symlink's target is not the file that was
verified, so a symlink is treated as an integrity failure. (The larger model this replaced also
needed real files because ONNX Runtime rejects an external-data file that resolves outside the model
directory; the small model is a single file, but the rule is kept.)
"""

import argparse
import hashlib
import importlib
import sys
from pathlib import Path
from typing import Any, Final

# The publisher's own repository (MIT), not a third-party re-export: an alternative int8 export
# declares no licence at all.
REPOSITORY: Final = "intfloat/multilingual-e5-small"
REVISION: Final = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
CHUNK_BYTES: Final = 16 * 1024 * 1024

FILE_DIGESTS: Final[dict[str, str]] = {
    "onnx/model_qint8_avx512_vnni.onnx": (
        "dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88"
    ),
    "tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    "config.json": "69137736cab8b8903a07fe8afaafdda25aac55415a12a55d1bffa9f581abf959",
    "tokenizer_config.json": "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b",
    "special_tokens_map.json": "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7",
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
