from uuid import UUID, uuid4

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hypothesis import given
from hypothesis import strategies as st

from shaidago.shared.crypto import (
    FORMAT_VERSION,
    DataKey,
    DecryptionError,
    EnvironmentKekWrapper,
    FieldCipher,
    KeyUnavailableError,
    field_context,
)

ROW = UUID("018f0000-0000-7000-8000-000000000042")
KEY = DataKey(uuid4(), b"k" * 32)
CANARY = b"contact: reporter.canary@example.test / +234 803 555 0142"
CONTEXT = field_context("private_reports", ROW, "description", 1)


def test_the_aes_gcm_primitive_matches_the_published_256_bit_known_answer() -> None:
    """McGrew and Viega, GCM test case 16 vector for AES-256 (no additional data)."""
    key = bytes.fromhex("feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308")
    nonce = bytes.fromhex("cafebabefacedbaddecaf888")
    plaintext = bytes.fromhex(
        "d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a72"
        "1c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b391aafd255"
    )
    sealed = AESGCM(key).encrypt(nonce, plaintext, None)
    assert sealed[:-16].hex() == (
        "522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa"
        "8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662898015ad"
    )
    assert sealed[-16:].hex() == "b094dac5d93471bdec1a502270e3cc6c"


def test_the_envelope_is_version_nonce_then_ciphertext_and_tag_over_the_bound_context() -> None:
    nonce = bytes(range(12))
    cipher = FieldCipher(random_bytes=lambda n: nonce[:n])
    envelope = cipher.encrypt(KEY, CANARY, CONTEXT)
    assert envelope[:1] == FORMAT_VERSION
    assert envelope[1:13] == nonce
    assert envelope[13:] == AESGCM(KEY.key).encrypt(nonce, CANARY, CONTEXT)
    assert len(envelope) == 1 + 12 + len(CANARY) + 16
    assert cipher.decrypt(KEY, envelope, CONTEXT) == CANARY


def test_every_encryption_uses_a_fresh_nonce_and_hides_the_plaintext() -> None:
    cipher = FieldCipher()
    envelopes = [cipher.encrypt(KEY, CANARY, CONTEXT) for _ in range(50)]
    assert len({e[1:13] for e in envelopes}) == 50
    assert len(set(envelopes)) == 50
    assert all(CANARY not in e and b"canary" not in e for e in envelopes)


@given(st.binary(max_size=4000))
def test_any_plaintext_round_trips(plaintext: bytes) -> None:
    cipher = FieldCipher()
    assert cipher.decrypt(KEY, cipher.encrypt(KEY, plaintext, CONTEXT), CONTEXT) == plaintext


@pytest.mark.parametrize(
    "wrong",
    [
        field_context("other_table", ROW, "description", 1),
        field_context("private_reports", uuid4(), "description", 1),
        field_context("private_reports", ROW, "contact_value", 1),
        field_context("private_reports", ROW, "description", 2),
        b"",
    ],
)
def test_ciphertext_moved_to_another_table_row_field_or_version_fails(wrong: bytes) -> None:
    cipher = FieldCipher()
    envelope = cipher.encrypt(KEY, CANARY, CONTEXT)
    with pytest.raises(DecryptionError):
        cipher.decrypt(KEY, envelope, wrong)


def test_a_different_key_fails_and_the_error_reveals_nothing() -> None:
    cipher = FieldCipher()
    envelope = cipher.encrypt(KEY, CANARY, CONTEXT)
    with pytest.raises(DecryptionError) as raised:
        cipher.decrypt(DataKey(uuid4(), b"z" * 32), envelope, CONTEXT)
    assert str(raised.value) == "decryption failed"
    assert raised.value.__cause__ is None
    assert CANARY.decode() not in repr(raised.value)


def test_flipping_any_single_byte_or_truncating_is_detected() -> None:
    cipher = FieldCipher()
    envelope = cipher.encrypt(KEY, CANARY, CONTEXT)
    for index in range(len(envelope)):
        tampered = envelope[:index] + bytes([envelope[index] ^ 0x01]) + envelope[index + 1 :]
        with pytest.raises(DecryptionError):
            cipher.decrypt(KEY, tampered, CONTEXT)
    for cut in (0, 1, 12, 28, len(envelope) - 1):
        with pytest.raises(DecryptionError):
            cipher.decrypt(KEY, envelope[:cut], CONTEXT)
    with pytest.raises(DecryptionError):
        cipher.decrypt(KEY, envelope + b"\x00", CONTEXT)
    with pytest.raises(DecryptionError):
        cipher.decrypt(KEY, b"\x02" + envelope[1:], CONTEXT)


def test_data_keys_never_show_their_key_material() -> None:
    assert "6b6b" not in repr(KEY)
    assert KEY.key.decode() not in repr(KEY)


def test_field_context_is_unambiguous_across_components() -> None:
    assert field_context("a", ROW, "b", 1) != field_context("a", ROW, "b", 11)


def test_the_kek_wrapper_round_trips_uses_the_active_version_and_reads_retired_ones() -> None:
    old = EnvironmentKekWrapper({"kek-1": b"1" * 32}, "kek-1")
    ring = {"kek-1": b"1" * 32, "kek-2": b"2" * 32}
    new = EnvironmentKekWrapper(ring, "kek-2")
    dek = b"d" * 32
    old_version, old_wrapped = old.wrap(dek, b"ctx")
    assert old_version == "kek-1"
    assert new.unwrap("kek-1", old_wrapped, b"ctx") == dek, "a retired KEK still unwraps"
    new_version, new_wrapped = new.wrap(dek, b"ctx")
    assert (new_version, new.active_version) == ("kek-2", "kek-2")
    assert new.unwrap("kek-2", new_wrapped, b"ctx") == dek
    assert dek not in new_wrapped


def test_the_kek_wrapper_rejects_wrong_context_unknown_versions_and_bad_input() -> None:
    wrapper = EnvironmentKekWrapper({"kek-1": b"1" * 32}, "kek-1")
    version, wrapped = wrapper.wrap(b"d" * 32, b"ctx")
    with pytest.raises(DecryptionError):
        wrapper.unwrap(version, wrapped, b"other")
    with pytest.raises(KeyUnavailableError):
        wrapper.unwrap("kek-9", wrapped, b"ctx")
    with pytest.raises(DecryptionError):
        wrapper.unwrap(version, wrapped[:20], b"ctx")
    with pytest.raises(ValueError, match="active KEK"):
        EnvironmentKekWrapper({"kek-1": b"1" * 32}, "kek-2")
