# Used when Railway deploys from the monorepo root (Root Directory left blank).
# If you set Root Directory to `backend` in Railway, the backend/Procfile is used instead.
web: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
