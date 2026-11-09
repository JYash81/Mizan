# Windows local setup

From the repository root, run `./scripts/check_environment.ps1`. To provision dependencies, run `./scripts/setup_windows.ps1`.

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env` if overrides are needed. Do not commit either `.env` file.

Start the API:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Start the web app separately:

```powershell
cd frontend
npm run dev
```

Run checks with `backend/.venv/Scripts/python.exe -m pytest`, `backend/.venv/Scripts/python.exe -m ruff check .`, then `npm run lint`, `npm run typecheck`, `npm test`, and `npm run build` from `frontend`. Stop either development process with `Ctrl+C`.
