"""Joplin REST API client for notes and notebooks."""

import httpx

from config import get_settings


class JoplinClient:
    """Joplin Data API client."""

    def __init__(self, base_url: str | None = None, token: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.joplin_url).rstrip("/")
        self.token = token or settings.joplin_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | list:
        """Make a request to Joplin API."""
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["token"] = self.token

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return {"success": True}

            return response.json()

    # ==================== Health ====================

    async def ping(self) -> bool:
        """Check if Joplin is running and accessible."""
        try:
            url = f"{self.base_url}/ping"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                return response.status_code == 200 and response.text == "JoplinClipperServer"
        except Exception:
            return False

    # ==================== Notebooks (Folders) ====================

    async def list_notebooks(self) -> list[dict]:
        """List all notebooks."""
        items = []
        page = 1
        while True:
            result = await self._request(
                "GET",
                "/folders",
                params={"page": page, "fields": "id,title,parent_id,created_time,updated_time"},
            )
            if isinstance(result, dict) and "items" in result:
                items.extend(result["items"])
                if not result.get("has_more"):
                    break
                page += 1
            else:
                # Old API format - direct list
                items = result if isinstance(result, list) else []
                break
        return items

    async def get_notebook(self, notebook_id: str) -> dict:
        """Get a specific notebook."""
        return await self._request("GET", f"/folders/{notebook_id}")

    async def create_notebook(self, title: str, parent_id: str | None = None) -> dict:
        """Create a new notebook."""
        data = {"title": title}
        if parent_id:
            data["parent_id"] = parent_id
        return await self._request("POST", "/folders", json=data)

    async def update_notebook(self, notebook_id: str, title: str) -> dict:
        """Update a notebook's title."""
        return await self._request("PUT", f"/folders/{notebook_id}", json={"title": title})

    async def delete_notebook(self, notebook_id: str) -> dict:
        """Delete a notebook."""
        return await self._request("DELETE", f"/folders/{notebook_id}")

    async def get_notebook_by_title(self, title: str) -> dict | None:
        """Find a notebook by title."""
        notebooks = await self.list_notebooks()
        for nb in notebooks:
            if nb.get("title") == title:
                return nb
        return None

    # ==================== Notes ====================

    async def list_notes(
        self,
        notebook_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List notes, optionally filtered by notebook."""
        if notebook_id:
            endpoint = f"/folders/{notebook_id}/notes"
        else:
            endpoint = "/notes"

        items = []
        page = 1
        while len(items) < limit:
            result = await self._request(
                "GET",
                endpoint,
                params={
                    "page": page,
                    "fields": "id,title,parent_id,created_time,updated_time,is_todo,todo_completed",
                    "order_by": "updated_time",
                    "order_dir": "DESC",
                },
            )
            if isinstance(result, dict) and "items" in result:
                items.extend(result["items"])
                if not result.get("has_more"):
                    break
                page += 1
            else:
                items = result if isinstance(result, list) else []
                break
        return items[:limit]

    async def get_note(self, note_id: str, include_body: bool = True) -> dict:
        """Get a specific note."""
        fields = "id,title,body,parent_id,created_time,updated_time,is_todo,todo_completed"
        if not include_body:
            fields = fields.replace(",body", "")
        return await self._request("GET", f"/notes/{note_id}", params={"fields": fields})

    async def create_note(
        self,
        title: str,
        body: str,
        notebook_id: str,
        is_todo: bool = False,
    ) -> dict:
        """Create a new note."""
        data = {
            "title": title,
            "body": body,
            "parent_id": notebook_id,
        }
        if is_todo:
            data["is_todo"] = 1
        return await self._request("POST", "/notes", json=data)

    async def update_note(
        self,
        note_id: str,
        title: str | None = None,
        body: str | None = None,
        notebook_id: str | None = None,
    ) -> dict:
        """Update a note."""
        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if notebook_id is not None:
            data["parent_id"] = notebook_id
        return await self._request("PUT", f"/notes/{note_id}", json=data)

    async def delete_note(self, note_id: str) -> dict:
        """Delete a note."""
        return await self._request("DELETE", f"/notes/{note_id}")

    # ==================== Search ====================

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search notes."""
        result = await self._request(
            "GET",
            "/search",
            params={
                "query": query,
                "limit": limit,
                "fields": "id,title,parent_id,created_time,updated_time",
            },
        )
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return result if isinstance(result, list) else []

    # ==================== Tags ====================

    async def list_tags(self) -> list[dict]:
        """List all tags."""
        result = await self._request("GET", "/tags", params={"fields": "id,title"})
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return result if isinstance(result, list) else []

    async def create_tag(self, title: str) -> dict:
        """Create a new tag."""
        return await self._request("POST", "/tags", json={"title": title})

    async def get_tag_notes(self, tag_id: str) -> list[dict]:
        """Get all notes with a specific tag."""
        result = await self._request(
            "GET",
            f"/tags/{tag_id}/notes",
            params={"fields": "id,title,parent_id,created_time,updated_time"},
        )
        if isinstance(result, dict) and "items" in result:
            return result["items"]
        return result if isinstance(result, list) else []

    async def add_tag_to_note(self, tag_id: str, note_id: str) -> dict:
        """Add a tag to a note."""
        return await self._request("POST", f"/tags/{tag_id}/notes", json={"id": note_id})

    async def remove_tag_from_note(self, tag_id: str, note_id: str) -> dict:
        """Remove a tag from a note."""
        return await self._request("DELETE", f"/tags/{tag_id}/notes/{note_id}")

    async def get_or_create_tag(self, title: str) -> dict:
        """Get an existing tag by title or create it."""
        tags = await self.list_tags()
        for tag in tags:
            if tag.get("title") == title:
                return tag
        return await self.create_tag(title)
