import asyncio
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from backend.shared.exceptions import ExportError
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class PDFExporter:
    """
    Generates a professional PDF requirement-to-user-story traceability document.
    """
    async def export(
        self, 
        stories: List[Dict[str, Any]], 
        validation_results: Dict[str, Any], 
        output_path: str
    ) -> None:
        """
        Builds and structures the report PDF using reportlab document builder flow.
        """
        logger.info(f"Generating PDF document report at {output_path}...")
        
        try:
            def build_pdf():
                doc = SimpleDocTemplate(
                    output_path,
                    pagesize=letter,
                    rightMargin=36,
                    leftMargin=36,
                    topMargin=36,
                    bottomMargin=36
                )
                
                styles = getSampleStyleSheet()
                
                # Custom Styles
                title_style = ParagraphStyle(
                    "DocTitle",
                    parent=styles["Heading1"],
                    fontName="Helvetica-Bold",
                    fontSize=22,
                    leading=26,
                    textColor=colors.HexColor("#1F4E78"),
                    spaceAfter=15
                )
                
                section_style = ParagraphStyle(
                    "DocSection",
                    parent=styles["Heading2"],
                    fontName="Helvetica-Bold",
                    fontSize=14,
                    leading=18,
                    textColor=colors.HexColor("#2C5282"),
                    spaceBefore=12,
                    spaceAfter=8
                )

                body_style = ParagraphStyle(
                    "DocBody",
                    parent=styles["BodyText"],
                    fontName="Helvetica",
                    fontSize=10,
                    leading=14,
                    textColor=colors.HexColor("#2D3748")
                )

                story_style = ParagraphStyle(
                    "DocStory",
                    parent=styles["BodyText"],
                    fontName="Courier",
                    fontSize=9,
                    leading=13,
                    textColor=colors.HexColor("#1A202C")
                )

                story = []

                # Header
                story.append(Paragraph("BA Accelerator: Agile Requirement Report", title_style))
                story.append(Paragraph("Generated Requirement-to-User-Story Traceability Summary", body_style))
                story.append(Spacer(1, 15))

                # Validation Scorecard section
                story.append(Paragraph("Quality Validation scorecard", section_style))
                q_score = validation_results.get("quality_score", 0.0)
                is_app = "APPROVED" if validation_results.get("is_approved", False) else "AWAITING REVIEW / REJECTED"
                
                meta_text = (
                    f"<b>Overall Quality Rating:</b> {q_score}/100<br/>"
                    f"<b>Pipeline Status:</b> {is_app}<br/>"
                    f"<b>Requirements Covered Count:</b> {len(validation_results.get('coverage_verified', []))}<br/>"
                )
                story.append(Paragraph(meta_text, body_style))
                story.append(Spacer(1, 15))

                # User Stories Table
                story.append(Paragraph("Traceable User Stories Map", section_style))
                
                # Column labels
                table_data = [[
                    Paragraph("<b>ID</b>", body_style),
                    Paragraph("<b>Title & Description</b>", body_style),
                    Paragraph("<b>Acceptance Criteria (Gherkin)</b>", body_style),
                    Paragraph("<b>Trace Mappings</b>", body_style)
                ]]

                for s in stories:
                    ac_p = []
                    for ac in s.get("acceptance_criteria", []):
                        ac_p.append(f"• <i>{ac.get('scenario')}</i>:<br/>Given {ac.get('given')}<br/>When {ac.get('when')}<br/>Then {ac.get('then')}")
                    ac_text = "<br/>".join(ac_p)
                    
                    desc_text = f"<b>{s.get('title')}</b><br/>{s.get('user_story_text')}"
                    
                    table_data.append([
                        Paragraph(s.get("id", ""), body_style),
                        Paragraph(desc_text, body_style),
                        Paragraph(ac_text, story_style),
                        Paragraph(", ".join(s.get("trace_mappings", [])), body_style)
                    ])

                # Layout table widths
                t = Table(table_data, colWidths=[50, 160, 250, 80])
                t.setStyle(TableStyle([
                    ("ALIGN", (0,0), (-1,-1), "LEFT"),
                    ("VALIGN", (0,0), (-1,-1), "TOP"),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDF2F7")),
                    ("TOPPADDING", (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ]))
                story.append(t)

                doc.build(story)
                logger.info("PDF document compilation complete.")

            await asyncio.to_thread(build_pdf())
        except Exception as e:
            logger.error(f"PDF creation failure: {str(e)}")
            raise ExportError(f"PDF export failed: {str(e)}")

# INTEGRATION NOTE
# SimpleDocTemplate formats margins to letter page borders.
# Wrap raw string values in Paragraph layout flow elements to enforce auto line breaks.
