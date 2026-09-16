#!/usr/bin/env python3
"""Create report V3 from V2 and add the next security-testing objective."""

from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "GROUPE-12" / "Rapport-DVWA-V2.docx"
TARGET = ROOT / "GROUPE-12" / "Rapport-DVWA-V3.docx"
PARAGRAPH = (
    "L’objectif est de tester aussi les autres niveaux de sécurité et d’ajouter "
    "les résultats au rapport. Les méthodes d’envoi varient selon le niveau ; la "
    "prochaine étape est d’adapter les essais, de les exécuter et de documenter les "
    "résultats."
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
ET.register_namespace("w", W)


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))


with ZipFile(SOURCE) as source_zip:
    document = ET.fromstring(source_zip.read("word/document.xml"))
    body = document.find("w:body", NS)
    if body is None:
        raise RuntimeError("Corps du document Word introuvable")

    for text_node in document.findall(".//w:t", NS):
        if text_node.text:
            text_node.text = text_node.text.replace("Version V2", "Version V3")

    paragraphs = body.findall("w:p", NS)
    anchor = next(
        (p for p in paragraphs if paragraph_text(p).startswith("Nous devons compléter T06")),
        None,
    )
    if anchor is None:
        raise RuntimeError("Paragraphe d’insertion introuvable")

    new_paragraph = ET.Element(f"{{{W}}}p")
    properties = anchor.find("w:pPr", NS)
    if properties is not None:
        new_paragraph.append(deepcopy(properties))
    run = ET.SubElement(new_paragraph, f"{{{W}}}r")
    text = ET.SubElement(run, f"{{{W}}}t")
    text.text = PARAGRAPH
    body.insert(list(body).index(anchor) + 1, new_paragraph)

    updated_xml = ET.tostring(document, encoding="utf-8", xml_declaration=True)
    with NamedTemporaryFile(suffix=".docx", delete=False, dir=TARGET.parent) as temp:
        temp_path = Path(temp.name)
    try:
        with ZipFile(temp_path, "w", ZIP_DEFLATED) as target_zip:
            for entry in source_zip.infolist():
                payload = updated_xml if entry.filename == "word/document.xml" else source_zip.read(entry.filename)
                target_zip.writestr(entry, payload)
        temp_path.replace(TARGET)
    finally:
        if temp_path.exists():
            temp_path.unlink()

print(TARGET)
