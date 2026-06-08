# pyrefly: ignore [missing-import]
import fitz
import json

from pathlib import Path


# Page label vocabulary — used by tasks for routing and by the agent for focus hints.
LABEL_SPEC_OVERVIEW = "spec_overview"   # 特記仕様書 / 仕様表
LABEL_SLD           = "sld"             # 単線結線図
LABEL_BREAKER_LIST  = "breaker_list"    # 低圧配電盤リスト / ブレーカリスト
LABEL_UNKNOWN       = "unknown"

_LABEL_DESCRIPTIONS = {
    LABEL_SPEC_OVERVIEW: "Specification / overview sheet (特記仕様書・仕様表)",
    LABEL_SLD:           "Single-line diagram (単線結線図)",
    LABEL_BREAKER_LIST:  "Low-voltage panel / breaker list (配電盤リスト)",
    LABEL_UNKNOWN:       "Unclassified page",
}


def _classify_page(page: fitz.Page) -> str:
    """
    Classify a PDF page using vector drawing statistics.

    Text is encoded as tiny filled paths in these CAD PDFs — get_text() returns
    nothing. Three signals derived from empirical analysis of all 5 PDFs:

    h25 : wide hairlines (width > 25% of page, height < 3pt) ABOVE the title-block
          strip (top 75% of page). Breaker-list tables produce 100+; other pages < 15.

    large : paths with bounding-box area > 50pt². SLD circuit symbols are larger
            graphics (150+). Spec pages and plain breaker pages have very few.

    total : total path count. Used as tie-breaker for moderate-complexity SLD pages
            that have fewer large symbols (e.g. 見積② 単線結線図: total=19k, large=65).

    Decision tree (order matters):
      1. h25 >= 100  → breaker_list   (dense table rows dominate)
      2. large >= 150 → sld           (rich circuit symbols present)
      3. total > 15 000 AND large > 40 → sld   (moderate SLD, fewer symbols)
      4. total >= 5 000  → spec_overview
      5. unknown
    """
    drawings = page.get_drawings()
    if not drawings:
        return LABEL_UNKNOWN

    pw, ph = page.rect.width, page.rect.height
    total = len(drawings)

    h25 = sum(
        1 for d in drawings
        if (d["rect"].x1 - d["rect"].x0) > pw * 0.25   # spans >25% of page width
        and (d["rect"].y1 - d["rect"].y0) < 3            # hairline thin
        and d["rect"].y0 < ph * 0.75                     # above title-block strip
    )
    large = sum(
        1 for d in drawings
        if (d["rect"].x1 - d["rect"].x0) * (d["rect"].y1 - d["rect"].y0) > 50
    )

    if h25 >= 100:
        return LABEL_BREAKER_LIST
    if large >= 150:
        return LABEL_SLD
    if total > 15_000 and large > 40:
        return LABEL_SLD
    if total >= 5_000:
        return LABEL_SPEC_OVERVIEW
    return LABEL_UNKNOWN


def pdf_to_images(
    pdf_path: str, output_dir: Path, dpi: int
) -> tuple[list[Path], list[dict]]:
    """Convert PDF pages to PNG images, classifying each page.

    Returns:
        outputs   : list of saved PNG paths
        page_info : list of dicts {path, page_number, label}
                    Also written to <output_dir>/page_labels.json for caching.
    Base64 encoding happens at agent level (agent.py:_image_message) only.
    """
    doc = fitz.open(pdf_path)
    outputs: list[Path] = []
    page_info: list[dict] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        label = _classify_page(page)

        pix = page.get_pixmap(dpi=dpi)
        output = output_dir / f"page_{page_num + 1}.png"
        pix.save(str(output))
        outputs.append(output)

        info = {
            "path": str(output),
            "page_number": page_num + 1,
            "label": label,
        }
        page_info.append(info)
        print(
            f"Saved: {output} at {dpi} DPI "
            f"({pix.width}x{pix.height} px) → [{label}]"
        )

    (output_dir / "page_labels.json").write_text(
        json.dumps(page_info, indent=2, ensure_ascii=False)
    )
    doc.close()
    print("conversion complete")
    return outputs, page_info



if __name__ == '__main__':

    path = Path('workspace/__scratch')
    images = pdf_to_images(pdf_path='data/__originals/見積④.pdf', output_dir=path, dpi=300)

    print(images)