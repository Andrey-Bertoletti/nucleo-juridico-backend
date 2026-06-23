"""Extração de texto dos documentos do Storage (PDF / Word / imagem).

Estratégia (Fase 1):
  - PDF com texto selecionável  -> pypdf;
  - DOC/DOCX                     -> python-docx;
  - imagem ou PDF escaneado      -> nota indicando necessidade de OCR
    (o OCR real depende do provedor: externo lê a imagem direto; local usa
    Tesseract). A nota não quebra o fluxo — vira o `extracted_text`.

A função degrada com elegância: se uma biblioteca opcional não estiver
instalada, devolve uma nota em vez de levantar exceção.
"""

import io
import logging

from app.core.settings import settings
from app.modules.documents.models import Document
from app.services.supabase_client import get_admin_client

logger = logging.getLogger("nucleo_juridico")


_OCR_NOTE = (
    "[Não foi possível extrair texto automaticamente: o documento é uma imagem "
    "ou um PDF escaneado. É necessário OCR — disponível com provedor multimodal "
    "(externo) ou Tesseract (local).]"
)


def _download(storage_path: str) -> bytes:
    sb = get_admin_client()
    return sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET).download(storage_path)


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf não instalado — extração de PDF indisponível.")
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao ler PDF.")
        return ""


def _docx_text(data: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        logger.warning("python-docx não instalado — extração de Word indisponível.")
        return ""
    try:
        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao ler DOCX.")
        return ""


def extract_document_text(doc: Document) -> str:
    """Extrai (best-effort) o texto de um documento e aplica o corte de tamanho."""
    name = (doc.file_name or doc.storage_path or "").lower()

    try:
        data = _download(doc.storage_path)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Não foi possível baixar o arquivo do Storage: {exc}"
        ) from exc

    if name.endswith(".pdf"):
        text = _pdf_text(data)
    elif name.endswith((".docx", ".doc")):
        text = _docx_text(data)
    elif name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        text = ""  # imagem -> OCR
    else:
        # tenta PDF como palpite padrão
        text = _pdf_text(data)

    text = (text or "").strip()
    if not text:
        text = _OCR_NOTE

    max_chars = settings.AI_MAX_INPUT_CHARS
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "\n[...documento truncado por tamanho...]"
    return text
