#!/usr/bin/env python3
"""
Generate a PDF research report from a session's files directory.

Usage:
    python3 scripts/generate_pdf.py <files_dir>
    # or via env var:
    RESEARCH_FILES_DIR=logs/session_.../files python3 scripts/generate_pdf.py
"""

import glob
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _ensure_reportlab() -> None:
    try:
        import reportlab  # noqa: F401
    except ImportError:
        print("Installing reportlab…")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "reportlab", "-q"], check=True
        )


def generate(files_dir: str) -> str:
    _ensure_reportlab()

    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    root = Path(files_dir)
    note_files = sorted(glob.glob(str(root / "research_notes" / "*.md")))
    chart_files = sorted(glob.glob(str(root / "charts" / "*.png")))
    data_summary_path = root / "data" / "data_summary.md"
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not note_files:
        print(f"ERROR: No research notes found in {root / 'research_notes'}", file=sys.stderr)
        return ""

    # ── styles ────────────────────────────────────────────────────────────────
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "BodyJ", parent=base["Normal"],
        fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=4,
    )
    bullet = ParagraphStyle(
        "BulletJ", parent=base["Normal"],
        fontSize=10, leading=14, leftIndent=16, spaceAfter=3,
    )
    code = ParagraphStyle(
        "CodeJ", parent=base["Code"],
        fontSize=8, leading=11, spaceAfter=2,
    )

    # ── output path ───────────────────────────────────────────────────────────
    slug = Path(note_files[0]).stem[:40]
    today = datetime.now().strftime("%Y%m%d")
    pdf_path = str(reports_dir / f"{slug}_report_{today}.pdf")

    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72,
    )

    story: list = []

    # ── title ─────────────────────────────────────────────────────────────────
    title = slug.replace("_", " ").title()
    story.append(Paragraph(f"Research Report: {title}", base["Title"]))
    story.append(Paragraph(datetime.now().strftime("%B %d, %Y"), base["Normal"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=1))
    story.append(Spacer(1, 0.15 * inch))

    # ── executive summary (data_summary.md first 30 lines) ────────────────────
    if data_summary_path.exists():
        story.append(Paragraph("Executive Summary", base["Heading1"]))
        for line in data_summary_path.read_text(encoding="utf-8").splitlines()[:30]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph("• " + line[2:], bullet))
            else:
                story.append(Paragraph(line, body))
        story.append(Spacer(1, 0.15 * inch))

    # ── charts ────────────────────────────────────────────────────────────────
    if chart_files:
        story.append(Paragraph("Data Visualizations", base["Heading1"]))
        for cp in chart_files:
            try:
                story.append(Image(cp, width=5 * inch, height=3 * inch))
                caption = Path(cp).stem.replace("_", " ").title()
                story.append(Paragraph(f"<i>{caption}</i>", base["Normal"]))
                story.append(Spacer(1, 0.15 * inch))
            except Exception as exc:
                print(f"Warning: could not embed {cp}: {exc}", file=sys.stderr)

    # ── research notes (one section per file) ─────────────────────────────────
    story.append(Paragraph("Research Findings", base["Heading1"]))
    for note_path in note_files:
        section = Path(note_path).stem.replace("_", " ").title()
        story.append(Paragraph(section, base["Heading2"]))
        for line in Path(note_path).read_text(encoding="utf-8").splitlines():
            line_s = line.strip()
            if not line_s:
                story.append(Spacer(1, 0.05 * inch))
            elif line_s.startswith("### "):
                story.append(Paragraph(line_s[4:], base["Heading3"]))
            elif line_s.startswith("## "):
                story.append(Paragraph(line_s[3:], base["Heading2"]))
            elif line_s.startswith("# "):
                pass  # skip top-level heading (used as section title already)
            elif line_s.startswith("- ") or line_s.startswith("* "):
                story.append(Paragraph("• " + line_s[2:], bullet))
            elif line_s.startswith("|"):
                story.append(Paragraph(line_s, code))
            else:
                story.append(Paragraph(line_s, body))
        story.append(Spacer(1, 0.1 * inch))

    doc.build(story)
    print(f"PDF saved: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    files_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RESEARCH_FILES_DIR", "files")
    result = generate(files_dir)
    sys.exit(0 if result else 1)
