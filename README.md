# tinyman
This is a repo for TinyFish Hackathon

## Netlify Reverse Proxy + OAuth

The app is designed to be accessed through Netlify so users always stay on `https://tinyman.netlify.app`.

### Backend setting

Set `APP_BASE_URL` for OAuth callbacks (default is already Netlify):

- `APP_BASE_URL=https://tinyman.netlify.app`

### Required OAuth redirect URIs

Add these exact callback URLs in each provider dashboard:

- `https://tinyman.netlify.app/auth/google/callback`
- `https://tinyman.netlify.app/auth/github/callback`
- `https://tinyman.netlify.app/auth/gitlab/callback`

If provider dashboard URIs and the app callback URIs do not match exactly, login will fail.

### Netlify redirect rule

Use this in Netlify `_redirects`:

`/* https://tinyman-d9ka.onrender.com/:splat  200!`

This proxies all routes (including `/main` and `/output`) through Netlify without changing the browser URL.
