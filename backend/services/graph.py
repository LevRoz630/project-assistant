"""Microsoft Graph API client for OneDrive, Calendar, Tasks, and Email."""

import httpx

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class GraphClient:
    """Microsoft Graph API client."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make a request to Graph API."""
        url = f"{GRAPH_BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json,
                params=params,
                timeout=30.0,
            )

            if response.status_code == 204:
                return {"success": True}

            response.raise_for_status()
            return response.json()

    async def _request_content(self, endpoint: str) -> bytes:
        """Get raw content from Graph API."""
        url = f"{GRAPH_BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=url,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.content

    async def _upload_content(
        self, endpoint: str, content: bytes, content_type: str = "text/plain"
    ) -> dict:
        """Upload content to Graph API."""
        url = f"{GRAPH_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": content_type,
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                url=url,
                headers=headers,
                content=content,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    # ==================== User ====================

    async def get_me(self) -> dict:
        """Get current user profile."""
        return await self._request("GET", "/me")

    # ==================== OneDrive ====================

    async def list_drive_root(self) -> dict:
        """List items in OneDrive root."""
        return await self._request("GET", "/me/drive/root/children")

    async def list_folder(self, folder_path: str) -> dict:
        """List items in a folder by path."""
        # URL encode the path
        encoded_path = folder_path.replace(" ", "%20")
        return await self._request("GET", f"/me/drive/root:/{encoded_path}:/children")

    async def get_item_by_path(self, item_path: str) -> dict:
        """Get item metadata by path."""
        encoded_path = item_path.replace(" ", "%20")
        return await self._request("GET", f"/me/drive/root:/{encoded_path}")

    async def get_file_content(self, item_path: str) -> bytes:
        """Get file content by path."""
        encoded_path = item_path.replace(" ", "%20")
        return await self._request_content(f"/me/drive/root:/{encoded_path}:/content")

    async def create_folder(self, parent_path: str, folder_name: str) -> dict:
        """Create a folder."""
        encoded_path = parent_path.replace(" ", "%20")
        return await self._request(
            "POST",
            f"/me/drive/root:/{encoded_path}:/children",
            json={
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail",
            },
        )

    async def upload_file(self, file_path: str, content: bytes) -> dict:
        """Upload or update a file (for files < 4MB)."""
        encoded_path = file_path.replace(" ", "%20")
        return await self._upload_content(
            f"/me/drive/root:/{encoded_path}:/content",
            content,
            "text/plain",
        )

    async def delete_item(self, item_path: str) -> dict:
        """Delete an item by path."""
        encoded_path = item_path.replace(" ", "%20")
        return await self._request("DELETE", f"/me/drive/root:/{encoded_path}")

    # ==================== Microsoft To Do ====================

    async def list_task_lists(self) -> dict:
        """List all task lists."""
        return await self._request("GET", "/me/todo/lists")

    async def get_task_list(self, list_id: str) -> dict:
        """Get a specific task list."""
        return await self._request("GET", f"/me/todo/lists/{list_id}")

    async def list_tasks(self, list_id: str, include_completed: bool = False) -> dict:
        """List tasks in a task list."""
        params = {}
        if not include_completed:
            params["$filter"] = "status ne 'completed'"
        return await self._request("GET", f"/me/todo/lists/{list_id}/tasks", params=params)

    async def create_task(
        self, list_id: str, title: str, body: str | None = None, due_date: str | None = None
    ) -> dict:
        """Create a new task."""
        task_data = {"title": title}

        if body:
            task_data["body"] = {"content": body, "contentType": "text"}

        if due_date:
            task_data["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}

        return await self._request("POST", f"/me/todo/lists/{list_id}/tasks", json=task_data)

    async def update_task(self, list_id: str, task_id: str, updates: dict) -> dict:
        """Update a task."""
        return await self._request(
            "PATCH", f"/me/todo/lists/{list_id}/tasks/{task_id}", json=updates
        )

    async def complete_task(self, list_id: str, task_id: str) -> dict:
        """Mark a task as complete."""
        return await self.update_task(list_id, task_id, {"status": "completed"})

    async def delete_task(self, list_id: str, task_id: str) -> dict:
        """Delete a task."""
        return await self._request("DELETE", f"/me/todo/lists/{list_id}/tasks/{task_id}")

    # ==================== Calendar ====================

    async def list_calendars(self) -> dict:
        """List all calendars."""
        return await self._request("GET", "/me/calendars")

    async def get_calendar_events(
        self,
        start_datetime: str,
        end_datetime: str,
        calendar_id: str | None = None,
    ) -> dict:
        """Get calendar events in a time range."""
        endpoint = f"/me/calendars/{calendar_id}/events" if calendar_id else "/me/events"

        params = {
            "$filter": f"start/dateTime ge '{start_datetime}' and end/dateTime le '{end_datetime}'",
            "$orderby": "start/dateTime",
            "$top": "50",
        }

        return await self._request("GET", endpoint, params=params)

    async def get_calendar_view(
        self,
        start_datetime: str,
        end_datetime: str,
    ) -> dict:
        """Get calendar view (includes recurring events expanded)."""
        params = {
            "startDateTime": start_datetime,
            "endDateTime": end_datetime,
            "$orderby": "start/dateTime",
            "$top": "50",
        }

        return await self._request("GET", "/me/calendarView", params=params)

    async def create_event(
        self,
        subject: str,
        start_datetime: str,
        end_datetime: str,
        body: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
    ) -> dict:
        """Create a calendar event."""
        event_data = {
            "subject": subject,
            "start": {"dateTime": start_datetime, "timeZone": "UTC"},
            "end": {"dateTime": end_datetime, "timeZone": "UTC"},
        }

        if body:
            event_data["body"] = {"contentType": "text", "content": body}

        if location:
            event_data["location"] = {"displayName": location}

        if attendees:
            event_data["attendees"] = [
                {"emailAddress": {"address": email}, "type": "required"} for email in attendees
            ]

        return await self._request("POST", "/me/events", json=event_data)

    async def delete_event(self, event_id: str) -> dict:
        """Delete a calendar event."""
        return await self._request("DELETE", f"/me/events/{event_id}")

    # ==================== Email ====================

    async def list_messages(
        self,
        folder: str = "inbox",
        top: int = 20,
        skip: int = 0,
    ) -> dict:
        """List email messages."""
        params = {
            "$top": str(top),
            "$skip": str(skip),
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
        }

        return await self._request("GET", f"/me/mailFolders/{folder}/messages", params=params)

    async def get_message(self, message_id: str) -> dict:
        """Get a specific email message."""
        return await self._request("GET", f"/me/messages/{message_id}")

    async def search_messages(self, query: str, top: int = 20) -> dict:
        """Search email messages."""
        params = {
            "$search": f'"{query}"',
            "$top": str(top),
            "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
        }

        return await self._request("GET", "/me/messages", params=params)
