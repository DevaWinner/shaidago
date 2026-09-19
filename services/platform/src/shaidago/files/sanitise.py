"""CPU-bound sanitising. These functions are top-level so a process pool can run them.

Images are decoded under a pixel limit and re-encoded to a fresh file, so EXIF, IPTC, XMP, GPS, ICC
and text chunks cannot survive. PDFs are opened without recovery, refused if encrypted or too long,
stripped of metadata, attachments, scripts, actions, forms, and annotations, and rewritten without
compressed object streams so the result can be inspected as plain structure. The output is checked
again and refused if anything dangerous remains.
"""

import io
import warnings
from typing import Final

import pikepdf
from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from shaidago.files.rules import FileLimits, UploadRejectedError, has_active_content

_FORMATS: Final = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
_FORBIDDEN_PDF_TOKENS: Final = (
    b"/JavaScript",
    b"/JS",
    b"/EmbeddedFile",
    b"/OpenAction",
    b"/Launch",
    b"/URI",
    b"/AcroForm",
    b"/AA",
    b"/Metadata",
)
_ROOT_KEYS_TO_DROP: Final = ("/OpenAction", "/AA", "/AcroForm", "/Names", "/Metadata", "/URI")


def sanitise(data: bytes, mime: str, limits: FileLimits) -> bytes:
    """Return a clean derivative of ``data``. Raises ``UploadRejectedError`` with a reason."""
    if mime == "application/pdf":
        return _sanitise_pdf(data, limits)
    return _sanitise_image(data, mime, limits)


def _sanitise_image(data: bytes, mime: str, limits: FileLimits) -> bytes:
    if has_active_content(data):
        raise UploadRejectedError("active_content")
    Image.MAX_IMAGE_PIXELS = limits.max_pixels
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            probe = Image.open(io.BytesIO(data))
            if probe.format != _FORMATS[mime]:
                raise UploadRejectedError("spoofed_type")
            if probe.width * probe.height > limits.max_pixels:
                raise UploadRejectedError("too_many_pixels")
            probe.verify()
            image = Image.open(io.BytesIO(data))
            image.load()
    except Image.DecompressionBombError, Image.DecompressionBombWarning:
        raise UploadRejectedError("too_many_pixels") from None
    except UnidentifiedImageError, OSError, SyntaxError, ValueError:
        raise UploadRejectedError("malformed") from None
    image = ImageOps.exif_transpose(image)
    image.info = {}
    if max(image.size) > limits.max_dimension:
        image.thumbnail((limits.max_dimension, limits.max_dimension))
    if mime == "image/jpeg":
        image = image.convert("RGB")
    elif image.mode not in {"RGB", "RGBA", "L"}:
        image = image.convert("RGBA" if "A" in image.mode else "RGB")
    output = io.BytesIO()
    options = {"optimize": True} if mime == "image/png" else {"quality": 85}
    image.save(output, format=_FORMATS[mime], **options)
    return output.getvalue()


def _sanitise_pdf(data: bytes, limits: FileLimits) -> bytes:
    try:
        with pikepdf.open(io.BytesIO(data), attempt_recovery=False, suppress_warnings=True) as pdf:
            if pdf.is_encrypted:
                raise UploadRejectedError("encrypted_pdf")
            if len(pdf.pages) > limits.max_pdf_pages:
                raise UploadRejectedError("too_many_pages")
            for key in _ROOT_KEYS_TO_DROP:
                if key in pdf.Root:
                    del pdf.Root[key]
            for page in pdf.pages:
                for key in ("/Annots", "/AA", "/Metadata"):
                    if key in page.obj:
                        del page.obj[key]
            if "/Info" in pdf.trailer:
                del pdf.trailer["/Info"]
            pdf.remove_unreferenced_resources()
            output = io.BytesIO()
            pdf.save(output, object_stream_mode=pikepdf.ObjectStreamMode.disable, linearize=False)
    except pikepdf.PasswordError:
        raise UploadRejectedError("encrypted_pdf") from None
    except UploadRejectedError:
        raise
    except pikepdf.PdfError, ValueError, OSError:
        raise UploadRejectedError("malformed") from None
    result = output.getvalue()
    if any(token in result for token in _FORBIDDEN_PDF_TOKENS):
        raise UploadRejectedError("active_content")
    return result
