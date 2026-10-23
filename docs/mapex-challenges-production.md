# Mapex daily challenges release

The challenge workflow lives in EduCam Pro under `/edu/`. Staff create a challenge at `/edu/admin/challenges/`; students open its public link or QR code and submit up to five photos or one PDF. Gemini grades the work against the teacher-provided answer key and rubric. AI grades are provisional until a teacher verifies them.

## Production release

1. Pull the release commit on the existing VPS checkout at `/home/eshelle/app`.
2. Run `sudo bash deploy/update_mapex_challenges.sh`.
3. The script refuses to proceed unless the worktree is clean, the checkout matches `origin/main`, Django checks pass, the Gemini credential is configured, and a verified database backup is created. It migrates only `edu_platform` and `facebook_agent`, collects static files, then restarts the web, Celery worker, and Celery Beat services.
4. Open `/edu/admin/challenges/` while signed in as staff. Create and publish a challenge, then download its QR code.

Required AI configuration is an existing `GOOGLE_API_KEY`, `GEMINI_SEARCH_API_KEY`, or valid Vertex service-account file configured by `GCP_VERTEX_KEY_PATH`. The release script checks presence only; it never prints credentials or sends a test student copy.

The database backup is stored under `/home/eshelle/backups/mapex-facebook/` with restrictive permissions. A schema migration rollback is not automated; these migrations are additive and the code should be rolled back only after assessing database state.
