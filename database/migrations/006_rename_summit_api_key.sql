-- Rename summit_api_key to summit_access_token to match backend expectations
-- The backend code (backend/app/routers/summit.py) expects summit_access_token
-- but the original migration created summit_api_key instead

ALTER TABLE agencies
RENAME COLUMN summit_api_key TO summit_access_token;
