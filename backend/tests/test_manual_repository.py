from __future__ import annotations

import zipfile
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.mcp.mcp_manual import ManualRepository


def _create_docx(path: Path, text: str) -> None:
    """Create a minimal docx file without external dependencies."""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    doc_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:t>{text}</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>"""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/_rels/document.xml.rels", doc_rels)
        archive.writestr("word/document.xml", document)


@pytest.fixture()
def manual_dir(tmp_path: Path) -> Path:
    base = tmp_path / "manuals"
    base.mkdir()
    (base / "sensor_error_case.txt").write_text(
        "XMEAS 5\n* INCLUDE : feed stream group\n* LLM POINT : composition or flow abnormal → affects whole process\n\n"
        "XMEAS 7\n* INCLUDE : pressure valve issue\n",
        encoding="utf-8",
    )
    (base / "guide.txt").write_text("TXT-GUIDE", encoding="utf-8")
    _create_docx(base / "guide.docx", "DOCX-GUIDE")
    return base


def test_manual_repository_reads_docx_and_txt(manual_dir: Path) -> None:
    repo = ManualRepository(base_path=manual_dir)
    corpus = repo.read_manual(str(manual_dir))
    assert "TXT-GUIDE" in corpus
    assert "DOCX-GUIDE" in corpus


def test_manual_repository_sensor_context_renders_sections(manual_dir: Path) -> None:
    repo = ManualRepository(base_path=manual_dir)
    context = repo.render_sensor_context(["XMEAS 5", "5", "unknown"])
    assert "XMEAS 5" in context
    assert "feed stream group" in context
    assert "composition or flow abnormal" in context
