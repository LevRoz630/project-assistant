# Azure AD Setup

This guide walks you through setting up Azure AD authentication for the Personal AI Assistant.

## Step 1: Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: Personal AI Assistant
   - **Supported account types**: Personal Microsoft accounts only (or your preference)
   - **Redirect URI**: Web - `http://localhost:8000/auth/callback`
5. Click **Register**

## Step 2: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission** > **Microsoft Graph** > **Delegated permissions**
3. Add these permissions:
   - `User.Read`
   - `Files.ReadWrite.All` (OneDrive)
   - `Tasks.ReadWrite` (Microsoft To Do)
   - `Calendars.ReadWrite` (Calendar)
   - `Mail.Read` (Email - read only)
   - `Notes.ReadWrite` (OneNote)
4. Click **Grant admin consent** if you're an admin

## Step 3: Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and expiration
4. Click **Add**
5. **Copy the secret value immediately** - you won't see it again

## Step 4: Get Application IDs

From your app registration's **Overview** page, copy:

- **Application (client) ID** → `AZURE_CLIENT_ID`
- **Directory (tenant) ID** → `AZURE_TENANT_ID` (or use "common")

## Step 5: Configure Environment

Add to your `.env` file:

```bash
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_TENANT_ID=common
AZURE_REDIRECT_URI=http://localhost:8000/auth/callback
```

## Production Configuration

For production deployment:

1. Add your production redirect URI in Azure
2. Update `AZURE_REDIRECT_URI` accordingly
3. Consider using separate app registrations for dev/prod

## Troubleshooting

### "Invalid redirect URI"

- Ensure the redirect URI in Azure exactly matches your `.env`
- Include the `/auth/callback` path

### "Insufficient permissions"

- Verify all required permissions are added
- Admin consent may be required for organization accounts

### "Token expired"

- The app handles token refresh automatically
- If issues persist, log out and log in again
