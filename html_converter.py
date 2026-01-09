from typing import BinaryIO
import markdownify


def convert_html_to_markdown(file: BinaryIO) -> str:
    """
    Convert an HTML file to markdown.

    Args:
        file: A file-like object containing HTML content

    Returns:
        str: The markdown representation of the HTML content
    """
    html_content = file.read()
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')

    markdown_content = markdownify.markdownify(html_content, heading_style="atx")
    return markdown_content
