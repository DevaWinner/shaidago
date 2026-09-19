"""Private follow-up answers.

Ownership is decided in the database, inside one function that also stores the answer, so a
question that is not the caller's, is already answered, or is withdrawn all look the same: the
function reports ``False`` and nothing is written. The answer text is encrypted under its own data
key before it leaves this module and is never returned, logged, or shown on tracking.
"""

import secrets
from dataclasses import dataclass
from typing import Final, Literal
from uuid import UUID

from sqlalchemy import ARRAY, LargeBinary, Uuid, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from shaidago.shared.clock import Clock
from shaidago.shared.crypto import FieldCipher, field_context
from shaidago.shared.data_keys import DataKeyService
from shaidago.shared.ids import IdGenerator

SCHEMA_VERSION: Final = 1
MAX_ANSWER_CHARS: Final = 2000
OWNER_TABLE: Final = "report_follow_up_answers"
RECEIVED_MESSAGE: Final = "Thank you. Your follow-up answer was received and review has resumed."
AnswerKind = Literal["answered", "skipped", "unsafe"]

_SUBMIT = text(
    "SELECT app.follow_up_submit(:question, :digests, :handle, :answer, :kind, :ciphertext, :key, "
    ":version, :now, :event, :audit, :message)"
).bindparams(
    bindparam("digests", type_=ARRAY(LargeBinary)),
    bindparam("ciphertext", type_=LargeBinary),
    bindparam("handle", type_=Uuid),
    bindparam("key", type_=Uuid),
)
_READ = text(
    "SELECT id, answer_ciphertext, data_key_id FROM app.report_follow_up_answers "
    "WHERE question_id = :question"
)


class InvalidAnswerError(ValueError):
    """The answer content is unusable. The message never repeats it."""


@dataclass(frozen=True)
class Caller:
    """Who is answering: a tracking-code digest list, or a verified handle. Never both."""

    digests: tuple[bytes, ...] = ()
    handle_id: UUID | None = None


@dataclass(frozen=True)
class FollowUpSubmitter:
    session: AsyncSession
    keys: DataKeyService
    cipher: FieldCipher
    clock: Clock
    ids: IdGenerator

    async def submit(
        self, caller: Caller, question_id: UUID, kind: AnswerKind, answer: str | None
    ) -> bool:
        """Record the answer. False means the question is not the caller's to answer."""
        answer_id = self.ids.new()
        ciphertext: bytes | None = None
        key_id: UUID | None = None
        if kind == "answered":
            body = (answer or "").strip()
            if not body or len(body) > MAX_ANSWER_CHARS:
                raise InvalidAnswerError("answer length is not acceptable")
            key = await self.keys.create(OWNER_TABLE, answer_id, "follow_up_answers")
            key_id = key.id
            ciphertext = self.cipher.encrypt(
                key,
                body.encode(),
                field_context(OWNER_TABLE, answer_id, "answer", SCHEMA_VERSION),
            )
        elif answer:
            raise InvalidAnswerError("only an answered question carries text")
        recorded = (
            await self.session.execute(
                _SUBMIT,
                {
                    "question": question_id,
                    "digests": list(caller.digests) or [secrets.token_bytes(32)],
                    "handle": caller.handle_id,
                    "answer": answer_id,
                    "kind": kind,
                    "ciphertext": ciphertext,
                    "key": key_id,
                    "version": SCHEMA_VERSION,
                    "now": self.clock.now(),
                    "event": self.ids.new(),
                    "audit": self.ids.new(),
                    "message": RECEIVED_MESSAGE,
                },
            )
        ).scalar_one()
        return bool(recorded)


async def read_answer(
    session: AsyncSession, keys: DataKeyService, cipher: FieldCipher, question_id: UUID
) -> str | None:
    """Decrypt an answer for an authorised reviewer; None when there is none or it is not text."""
    row = (await session.execute(_READ, {"question": question_id})).one_or_none()
    if row is None or row.answer_ciphertext is None:
        return None
    key = await keys.load(row.data_key_id)
    plaintext = cipher.decrypt(
        key,
        bytes(row.answer_ciphertext),
        field_context(OWNER_TABLE, row.id, "answer", SCHEMA_VERSION),
    )
    return plaintext.decode()
