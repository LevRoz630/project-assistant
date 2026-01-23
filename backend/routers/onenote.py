"""OneNote integration endpoints."""

import re
from datetime import datetime
from html import escape

from ..auth import get_access_token_for_service
from ..config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from ..services.graph import GraphClient
from ..services.vectors import delete_document, ingest_document

router = APIRouter(prefix="/onenote", tags=["onenote"])
settings = get_settings()


def get_graph_client(request: Request) -> GraphClient:
    """Dependency to get authenticated Graph client for OneNote."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = get_access_token_for_service(session_id, "notes")
    if not token:
        raise HTTPException(status_code=401, detail="Session expired")

    return GraphClient(token)


class PageCreate(BaseModel):
    """Request body for creating a page."""

    section_id: str
    title: str
    content: str  # Markdown content - will be converted to HTML


class PageUpdate(BaseModel):
    """Request body for updating a page."""

    content: str  # Markdown content


# ==================== HTML/Markdown Conversion ====================


def markdown_to_html(md: str) -> str:
    """Convert basic markdown to HTML for OneNote."""
    html = escape(md)

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # Lists
    html = re.sub(r"^- \[ \] (.+)$", r"<p data-tag=\"to-do\">\1</p>", html, flags=re.MULTILINE)
    html = re.sub(r"^- \[x\] (.+)$", r"<p data-tag=\"to-do\" data-checked=\"true\">\1</p>", html, flags=re.MULTILINE)
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>\n?)+", r"<ul>\g<0></ul>", html)

    # Paragraphs (lines not already wrapped)
    lines = []
    for line in html.split("\n"):
        if line.strip() and not line.strip().startswith("<"):
            lines.append(f"<p>{line}</p>")
        else:
            lines.append(line)
    html = "\n".join(lines)

    return html


def html_to_markdown(html: str) -> str:
    """Convert OneNote HTML to markdown."""
    md = html

    # Remove HTML structure
    md = re.sub(r"<!DOCTYPE[^>]*>", "", md)
    md = re.sub(r"<html[^>]*>|</html>", "", md)
    md = re.sub(r"<head>.*?</head>", "", md, flags=re.DOTALL)
    md = re.sub(r"<body[^>]*>|</body>", "", md)
    md = re.sub(r"<meta[^>]*>", "", md)

    # Headers
    md = re.sub(r"<h1[^>]*>(.+?)</h1>", r"# \1", md)
    md = re.sub(r"<h2[^>]*>(.+?)</h2>", r"## \1", md)
    md = re.sub(r"<h3[^>]*>(.+?)</h3>", r"### \1", md)

    # Bold and italic
    md = re.sub(r"<strong>(.+?)</strong>", r"**\1**", md)
    md = re.sub(r"<b>(.+?)</b>", r"**\1**", md)
    md = re.sub(r"<em>(.+?)</em>", r"*\1*", md)
    md = re.sub(r"<i>(.+?)</i>", r"*\1*", md)

    # Lists
    md = re.sub(r"<li[^>]*>(.+?)</li>", r"- \1", md)
    md = re.sub(r"<ul[^>]*>|</ul>", "", md)
    md = re.sub(r"<ol[^>]*>|</ol>", "", md)

    # To-do items
    md = re.sub(r'<p[^>]*data-tag="to-do"[^>]*data-checked="true"[^>]*>(.+?)</p>', r"- [x] \1", md)
    md = re.sub(r'<p[^>]*data-tag="to-do"[^>]*>(.+?)</p>', r"- [ ] \1", md)

    # Paragraphs and divs
    md = re.sub(r"<p[^>]*>(.+?)</p>", r"\1\n", md)
    md = re.sub(r"<div[^>]*>(.+?)</div>", r"\1\n", md, flags=re.DOTALL)
    md = re.sub(r"<br[^>]*>", "\n", md)

    # Links
    md = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.+?)</a>', r"[\2](\1)", md)

    # Clean up remaining tags
    md = re.sub(r"<[^>]+>", "", md)

    # Clean up whitespace
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = md.strip()

    return md


# ==================== Notebooks ====================


@router.get("/notebooks")
async def list_notebooks(client: GraphClient = Depends(get_graph_client)):
    """List all OneNote notebooks."""
    try:
        result = await client.list_notebooks()
        notebooks = [
            {
                "id": nb["id"],
                "name": nb["displayName"],
                "created": nb.get("createdDateTime"),
                "modified": nb.get("lastModifiedDateTime"),
                "sections_url": nb.get("sectionsUrl"),
            }
            for nb in result.get("value", [])
        ]
        return {"notebooks": notebooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notebooks")
async def create_notebook(
    name: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new notebook."""
    try:
        result = await client.create_notebook(name)
        return {"success": True, "notebook": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Sections ====================


@router.get("/notebooks/{notebook_id}/sections")
async def list_sections(
    notebook_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """List sections in a notebook."""
    try:
        result = await client.list_sections(notebook_id)
        sections = [
            {
                "id": s["id"],
                "name": s["displayName"],
                "created": s.get("createdDateTime"),
                "modified": s.get("lastModifiedDateTime"),
            }
            for s in result.get("value", [])
        ]
        return {"notebook_id": notebook_id, "sections": sections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/notebooks/{notebook_id}/sections")
async def create_section(
    notebook_id: str,
    name: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new section in a notebook."""
    try:
        result = await client.create_section(notebook_id, name)
        return {"success": True, "section": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Pages ====================


@router.get("/sections/{section_id}/pages")
async def list_pages(
    section_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """List pages in a section."""
    try:
        result = await client.list_pages(section_id)
        pages = [
            {
                "id": p["id"],
                "title": p.get("title", "Untitled"),
                "created": p.get("createdDateTime"),
                "modified": p.get("lastModifiedDateTime"),
            }
            for p in result.get("value", [])
        ]
        return {"section_id": section_id, "pages": pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/pages")
async def list_all_pages(
    limit: int = 50,
    client: GraphClient = Depends(get_graph_client),
):
    """List all recent pages across all notebooks."""
    try:
        result = await client.list_pages(top=limit)
        pages = [
            {
                "id": p["id"],
                "title": p.get("title", "Untitled"),
                "created": p.get("createdDateTime"),
                "modified": p.get("lastModifiedDateTime"),
                "parent_section": p.get("parentSection", {}).get("displayName"),
            }
            for p in result.get("value", [])
        ]
        return {"pages": pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/pages/{page_id}")
async def get_page(
    page_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Get a page's content (returned as markdown)."""
    try:
        metadata = await client.get_page(page_id)
        html_content = await client.get_page_content(page_id)
        md_content = html_to_markdown(html_content)

        return {
            "id": page_id,
            "title": metadata.get("title", "Untitled"),
            "content": md_content,
            "created": metadata.get("createdDateTime"),
            "modified": metadata.get("lastModifiedDateTime"),
        }
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Page not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/pages")
async def create_page(
    page: PageCreate,
    client: GraphClient = Depends(get_graph_client),
):
    """Create a new page (accepts markdown content)."""
    try:
        html_content = markdown_to_html(page.content)
        result = await client.create_page(page.section_id, page.title, html_content)

        # Index in vector store
        source_path = f"onenote://{page.section_id}/{result.get('id')}"
        await ingest_document(
            content=f"# {page.title}\n\n{page.content}",
            source_path=source_path,
            metadata={
                "source": "onenote",
                "title": page.title,
                "page_id": result.get("id"),
            },
        )

        return {
            "success": True,
            "id": result.get("id"),
            "title": page.title,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/pages/{page_id}")
async def update_page(
    page_id: str,
    page: PageUpdate,
    client: GraphClient = Depends(get_graph_client),
):
    """Update a page's content (accepts markdown)."""
    try:
        html_content = markdown_to_html(page.content)
        await client.update_page(page_id, html_content)

        # Re-index
        metadata = await client.get_page(page_id)
        source_path = f"onenote://page/{page_id}"
        await ingest_document(
            content=f"# {metadata.get('title', 'Untitled')}\n\n{page.content}",
            source_path=source_path,
            metadata={
                "source": "onenote",
                "title": metadata.get("title"),
                "page_id": page_id,
            },
        )

        return {"success": True, "id": page_id}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Page not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/pages/{page_id}")
async def delete_page(
    page_id: str,
    client: GraphClient = Depends(get_graph_client),
):
    """Delete a page."""
    try:
        await client.delete_page(page_id)
        await delete_document(f"onenote://page/{page_id}")
        return {"success": True, "deleted": page_id}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Page not found") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Diary Integration ====================


@router.post("/diary/today")
async def create_today_diary(client: GraphClient = Depends(get_graph_client)):
    """Create or get today's diary entry in OneNote."""
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # Find or create PersonalAI notebook
        notebooks_result = await client.list_notebooks()
        notebooks = notebooks_result.get("value", [])
        pai_notebook = next(
            (nb for nb in notebooks if nb["displayName"] == "PersonalAI"),
            None,
        )

        if not pai_notebook:
            pai_notebook = await client.create_notebook("PersonalAI")

        notebook_id = pai_notebook["id"]

        # Find or create Diary section
        sections_result = await client.list_sections(notebook_id)
        sections = sections_result.get("value", [])
        diary_section = next(
            (s for s in sections if s["displayName"] == "Diary"),
            None,
        )

        if not diary_section:
            diary_section = await client.create_section(notebook_id, "Diary")

        section_id = diary_section["id"]

        # Check if today's page exists
        pages_result = await client.list_pages(section_id)
        pages = pages_result.get("value", [])
        today_page = next((p for p in pages if p.get("title") == today), None)

        if today_page:
            html_content = await client.get_page_content(today_page["id"])
            md_content = html_to_markdown(html_content)
            return {
                "exists": True,
                "id": today_page["id"],
                "title": today,
                "content": md_content,
            }

        # Create new diary entry
        template = f"""## Morning

## Tasks for Today
- [ ]

## Notes

## Evening Reflection

"""
        html_template = markdown_to_html(template)
        result = await client.create_page(section_id, today, html_template)

        # Index
        source_path = f"onenote://{section_id}/{result.get('id')}"
        await ingest_document(
            content=f"# {today}\n\n{template}",
            source_path=source_path,
            metadata={
                "source": "onenote",
                "title": today,
                "type": "diary",
                "page_id": result.get("id"),
            },
        )

        return {
            "exists": False,
            "created": True,
            "id": result.get("id"),
            "title": today,
            "content": template,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
