# -*- coding: utf-8 -*-
"""Minimal DOCX writer (stdlib only) for canopy asset reports."""
import base64
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape


def _w_p(text, bold=False, size_half_points=24, center=False, color=None, underline=False, italic=False):
    """One Word paragraph."""
    ppr = []
    if center:
        ppr.append('<w:jc w:val="center"/>')
    ppr_xml = f'<w:pPr>{"".join(ppr)}</w:pPr>' if ppr else ''
    rpr = []
    if bold:
        rpr.append('<w:b/>')
    if italic:
        rpr.append('<w:i/>')
    if underline:
        rpr.append('<w:u w:val="single"/>')
    if size_half_points:
        rpr.append(f'<w:sz w:val="{size_half_points}"/>')
        rpr.append(f'<w:szCs w:val="{size_half_points}"/>')
    if color:
        rpr.append(f'<w:color w:val="{color}"/>')
    rpr_xml = f'<w:rPr>{"".join(rpr)}</w:rPr>' if rpr else ''
    safe = escape(text or '')
    return f'<w:p>{ppr_xml}<w:r>{rpr_xml}<w:t xml:space="preserve">{safe}</w:t></w:r></w:p>'


def _w_image_paragraph(rel_id, cx_emu=5486400, cy_emu=4114800):
    return (
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/>'
        '<wp:docPr id="1" name="Canopy Image"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="0" name="Canopy"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        '<a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r></w:p>'
    ) % (cx_emu, cy_emu, rel_id, cx_emu, cy_emu)


def _w_page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def _canopy_body_paragraphs(canopy, image_rel=None):
    """Paragraph XML for one canopy (shared by single and batch export)."""
    shop = (canopy.shop_name or canopy.name or '').upper()
    asset_name = canopy.name or ''
    if canopy.code:
        asset_name = '%s (%s)' % (asset_name, canopy.code)
    county = (canopy.county_id.name or 'N/A').upper()
    sub_county = (canopy.sub_county_id.name or 'N/A').upper()
    location = canopy.google_maps_link or 'N/A'
    contacts = canopy.contact_phone or 'N/A'
    installed = str(canopy.allocated_date) if canopy.allocated_date else 'N/A'
    renovated = str(canopy.last_renovation_date) if canopy.last_renovation_date else 'N/A'

    body = []
    body.append(_w_p('CANOPY ASSET REPORT', bold=True, italic=True, underline=True, center=True, size_half_points=48))
    body.append(_w_p(shop, bold=True, center=True, size_half_points=56, color='A52A2A'))
    body.append(_w_p(asset_name.upper(), size_half_points=40))
    body.append(_w_p('COUNTY: %s' % county, bold=True, italic=True, size_half_points=32))
    body.append(_w_p('SUB-COUNTY: %s' % sub_county, bold=True, italic=True, size_half_points=32))
    body.append(_w_p('LOCATION: %s' % location, bold=True, italic=True, size_half_points=32))
    body.append(_w_p('CONTACTS: %s' % (contacts or 'N/A').upper(), bold=True, italic=True, size_half_points=32))
    body.append(_w_p('DATE INSTALLED: %s' % installed, bold=True, italic=True, size_half_points=32))
    body.append(_w_p('DATE RENOVATED: %s' % renovated, bold=True, italic=True, size_half_points=32))
    if image_rel:
        body.append(_w_image_paragraph(image_rel))
    return body


def build_canopy_asset_docx(canopies):
    """Build a DOCX byte string mirroring the canopy PDF report content."""
    if hasattr(canopies, 'ensure_one'):
        canopies = canopies if len(canopies) != 1 else canopies
    if not hasattr(canopies, '__iter__'):
        canopies = [canopies]
    canopies = list(canopies)

    body = []
    images = []
    for idx, canopy in enumerate(canopies):
        if idx:
            body.append(_w_page_break())
        image_bytes = None
        if canopy.image_report:
            try:
                image_bytes = base64.b64decode(canopy.image_report)
            except Exception:
                image_bytes = None
        image_rel = None
        if image_bytes:
            image_rel = 'rIdImg%d' % (idx + 1)
            images.append((image_rel, image_bytes))
        body.extend(_canopy_body_paragraphs(canopy, image_rel=image_rel))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<w:body>%s<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        '</w:sectPr></w:body></w:document>'
    ) % ''.join(body)

    content_types = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
    ]
    if images:
        content_types.append(
            '<Default Extension="png" ContentType="image/png"/>'
        )
        for i, (_rel, _data) in enumerate(images, start=1):
            content_types.append(
                '<Override PartName="/word/media/image%d.png" ContentType="image/png"/>' % i
            )
    content_types.append('</Types>')
    content_types_xml = ''.join(content_types)

    rels_root = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        '</Relationships>'
    )

    doc_rels = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
    ]
    for i, (rel_id, _data) in enumerate(images, start=1):
        doc_rels.append(
            '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            'Target="media/image%d.png"/>' % (rel_id, i)
        )
    doc_rels.append('</Relationships>')
    document_rels_xml = ''.join(doc_rels)

    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types_xml)
        zf.writestr('_rels/.rels', rels_root)
        zf.writestr('word/document.xml', document_xml)
        zf.writestr('word/_rels/document.xml.rels', document_rels_xml)
        for i, (_rel, data) in enumerate(images, start=1):
            zf.writestr('word/media/image%d.png' % i, data)
    return buf.getvalue()
