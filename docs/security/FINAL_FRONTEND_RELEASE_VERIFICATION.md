# Final Frontend Release Verification Report

- **Target Frontend URL:** `https://llmguru.hennt.in`
- **Release Artifact:** `frontend/dist.zip` (300,637 bytes, 79 files)
- **Status:** **`READY TO DEPLOY`**
- **Date of Verification:** 2026-11-10

---

## 1. Release Package Inspection & Integrity Audit

| Verification Criteria | Expected Standard | Actual Audit Result | Compliance Status |
| :--- | :--- | :--- | :---: |
| **ZIP File Integrity** | Valid ZIP archive with zero CRC checksum errors | Tested via `zipfile.testzip()` &rarr; 0 errors | **VERIFIED** |
| **Root Entry File** | `index.html` located at the archive root | Present at archive root (`index.html`, 431 bytes) | **VERIFIED** |
| **Asset Directory Hierarchy** | All JavaScript, CSS, and SVG chunks under `/assets/` | 76 compiled chunks located under `assets/` | **VERIFIED** |
| **Runtime Configuration** | `config.js` at root providing production API URL | `window.__MIZAN_CONFIG__.API_BASE_URL = "https://mizan-api-mq0i.onrender.com/api/v1"` | **VERIFIED** |
| **Bake-In Production URL** | Bundled JS defaults to production Cloud API | Bundled chunk uses `https://mizan-api-mq0i.onrender.com/api/v1` | **VERIFIED** |
| **Localhost API Exposure** | Zero active API network calls to `localhost` or `127.0.0.1` | 0 localhost network calls (only DOM polyfill fallback) | **VERIFIED** |
| **Secret Token Scrubbing** | Zero API keys, passwords, or private signing keys | Audited across all 76 JavaScript bundles &rarr; None | **VERIFIED** |
| **SPA Server Routing** | `.htaccess` with mod_rewrite redirecting non-files to `index.html` | `.htaccess` present with `RewriteRule ^ index.html [L]` | **VERIFIED** |
| **Static Asset Paths** | Relative root `/assets/...` asset tags | `index.html` loads `/config.js` and `/assets/index-*.js` | **VERIFIED** |

---

## 2. Safe Hostinger Deployment Checklist & Standard Operating Procedure

To safely release `frontend/dist.zip` to `https://llmguru.hennt.in` without downtime or data loss:

### Step 1: Existing Website Backup
1. Log in to Hostinger hPanel &rarr; Navigate to **File Manager** for `llmguru.hennt.in`.
2. Go into `public_html/`.
3. Select all existing files in `public_html/`, click **Archive/Compress**, and name it `backup_pre_deploy_20261110.zip`.
4. Download this backup archive to your local machine as a cold rollback safety point.

### Step 2: ZIP Content Verification
Verify that your local file `E:\WEB BACKUPS\Llmstarter\frontend\dist.zip` has:
- MD5/SHA checksum integrity.
- Size approximately ~300 KB.
- Contains `.htaccess`, `config.js`, `index.html`, and the `assets/` folder at top level (not nested inside a subfolder).

### Step 3: Temporary Staging Upload
1. In Hostinger File Manager inside `public_html/`, click **Upload** &rarr; Upload `dist.zip`.
2. Ensure the upload completes with 100% transfer confirmation.

### Step 4: Final Release Preparation
Ensure that active browser sessions can gracefully switch by keeping maintenance window or low-traffic timing in mind.

### Step 5: Replacement Procedure
1. Right-click `dist.zip` inside `public_html/` and choose **Extract**.
2. Set extraction path to `public_html/` and check **Replace existing files**.
3. Confirm extraction.
4. Verify that `.htaccess`, `config.js`, `index.html`, and `assets/` are present directly under `public_html/`.
5. Delete the uploaded `dist.zip` from `public_html/` to prevent public archive downloads.

### Step 6: Live Smoke Tests
1. Open a new private/incognito browser window and navigate to `https://llmguru.hennt.in`.
2. Press <kbd>Ctrl</kbd> + <kbd>F5</kbd> to purge browser caching.
3. Verify that the login form loads with clean styling and active input fields.
4. Sign in with the verified user account (`yeswanthjanne86@gmail.com`).
5. Verify that the dashboard loads the default organization `hennt` and workspace `Default Workspace`.
6. Navigate to Datasets tab; confirm datasets load without red connection error banners.
7. Click between Evaluation, Experiments, Hardware, Approvals, and Zoo tabs to confirm instant client-side routing.

### Step 7: Rollback Procedure (If Necessary)
If any critical display or routing issue occurs:
1. In Hostinger File Manager inside `public_html/`, delete all extracted files.
2. Extract the backup archive `backup_pre_deploy_20261110.zip` back into `public_html/`.
3. The previous functional state is restored immediately.
