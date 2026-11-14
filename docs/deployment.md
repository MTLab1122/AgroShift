# Deployment

## Public frontend

The `Deploy AgroShift to GitHub Pages` workflow builds and publishes the React
frontend whenever changes are pushed to the repository's current default branch,
`feature/nasa-data`. It can also be started manually from the Actions tab. The
project Pages URL is:

<https://mtlab1122.github.io/AgroShift/>

In the repository settings, enable **Settings → Pages → Build and deployment →
Source → GitHub Actions**. The first deployment cannot succeed until Pages is
enabled. Once configured, GitHub Pages serves the static frontend independently
of whether anyone is running a workstation.

## FastAPI backend

GitHub Actions runs short-lived jobs; it does not keep a FastAPI process running
24/7. The public frontend can be deployed to Pages without an API, but climate
health checks and recommendation requests require the backend to be deployed
separately to an always-on ASGI-capable hosting service.

After deploying the API:

1. Add the repository Actions **variable** `AGROSHIFT_API_URL` with the backend
   origin, for example `https://api.example.com` (no trailing slash).
2. Configure the backend's `CORS_ORIGINS` environment variable to include
   `https://mtlab1122.github.io`.
3. Push a change to `feature/nasa-data`, or run the Pages workflow manually, to
   rebuild the frontend with the API URL.

The API URL is public configuration, not a secret. If it is unset, the Pages
site remains viewable and reports that its backend is not configured; it does
not generate recommendations or substitute fabricated climate data.
