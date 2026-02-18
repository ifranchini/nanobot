# Google Workspace Skill Setup

## Prerequisites

- A Google account (personal @gmail.com works fine)
- Access to [Google Cloud Console](https://console.cloud.google.com/)

## Step 1: Create or Select a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click **New Project** (or select an existing one)
4. Name it something like "Nanobot" and click **Create**

## Step 2: Enable APIs

1. Go to **APIs & Services > Library**
2. Search for and enable each of these APIs:
   - **Google Calendar API**
   - **Google Docs API**
   - **Google Sheets API**
   - **Google Slides API**
   - **Google Drive API** (needed for creating new documents)

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** user type and click **Create**
3. Fill in the required fields:
   - **App name**: Nanobot
   - **User support email**: your email
   - **Developer contact**: your email
4. Click **Save and Continue**
5. On **Scopes**, click **Add or Remove Scopes** and add:
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/presentations`
   - `https://www.googleapis.com/auth/drive.file`
6. Click **Save and Continue**
7. On **Test users**, add your Gmail address
8. Click **Save and Continue**

## Step 4: Create OAuth2 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **+ Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Name: "Nanobot Desktop"
5. Click **Create**
6. Click **Download JSON** on the confirmation dialog
7. Rename the downloaded file to `credentials.json`

## Step 5: Place Credentials

Copy `credentials.json` to the nanobot workspace:

```bash
# Local development
cp ~/Downloads/credentials.json ~/.nanobot/workspace/google-credentials/

# Or for VPS deployment
scp ~/Downloads/credentials.json puma-vps:/home/nanobot/.nanobot/workspace/google-credentials/
```

## Step 6: Authorize

Run the auth command to generate a token:

```bash
# Local
python3 nanobot/skills/google-workspace/scripts/google_workspace.py auth

# Via nanobot agent
# Just ask: "Authenticate with Google Workspace"
```

This will:
1. Print an authorization URL
2. Open your browser (if available)
3. After you authorize, a `token.json` file is saved alongside `credentials.json`

## Step 7: Deploy Token to VPS (if needed)

If you ran auth locally but need it on the VPS:

```bash
scp ~/.nanobot/workspace/google-credentials/token.json puma-vps:/home/nanobot/.nanobot/workspace/google-credentials/
```

## Troubleshooting

### "Access blocked: This app's request is invalid"
- Ensure your Gmail is added as a test user in the OAuth consent screen

### "File not found: credentials.json"
- Verify the file is at `~/.nanobot/workspace/google-credentials/credentials.json`

### "Token has been expired or revoked"
- Delete `token.json` and run the `auth` command again

### "Insufficient Permission"
- You may need to re-authorize with updated scopes. Delete `token.json` and run `auth` again
