import tempfile
from pathlib import Path
import pymupdf4llm
import pymupdf
import logging

logger = logging.getLogger(__name__)


class PDFConverter:
    """Converts PDF files to Markdown using pymupdf4llm."""

    def __init__(self):
        """Initialize the PDF converter."""
        logger.info("PDF converter initialized with pymupdf4llm")

    async def convert_to_markdown(self, pdf_bytes: bytes, file_name: str) -> str:
        """
        Convert PDF bytes to Markdown text.

        Args:
            pdf_bytes: Raw PDF file bytes
            file_name: Original filename (for context)

        Returns:
            Markdown text extracted from the PDF

        Raises:
            Exception: If PDF conversion fails
        """
        try:
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".pdf"
            ) as temp_pdf:
                temp_pdf.write(pdf_bytes)
                temp_pdf_path = Path(temp_pdf.name)

            logger.info(f"Converting PDF to markdown: {file_name}")

            # Open PDF document
            doc = pymupdf.open(temp_pdf_path)

            # Convert to markdown using pymupdf4llm
            markdown_text = pymupdf4llm.to_markdown(doc)

            # Close document and clean up
            doc.close()
            temp_pdf_path.unlink()

            logger.info(
                f"Successfully converted {file_name} to markdown "
                f"({len(markdown_text)} characters)"
            )

            return markdown_text

        except Exception as e:
            logger.error(f"Failed to convert PDF {file_name}: {str(e)}")
            raise Exception(f"PDF conversion failed: {str(e)}")
