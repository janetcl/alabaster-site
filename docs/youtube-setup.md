# Automatic Sunday livestream links

The Sunday services are streamed as **unlisted** YouTube videos, so the site
can't find them on the public channel. A scheduled GitHub workflow reads the
channel's own broadcast list (read-only) and updates
`src/data/livestream.json`:

- **upcoming**: this Sunday's scheduled stream → the "Watch live" link
- **last**: the most recent finished Sunday stream → "Missed last Sunday?"

It runs Saturday evening, every 30 minutes on Sunday morning, and Monday,
and only commits when a link changes (which redeploys the site).

## One-time setup (about 10 minutes)

Do this signed in to the Google account that owns or manages the
Alabaster Group YouTube channel.

1. **Create a Google Cloud project**: https://console.cloud.google.com/projectcreate
   (name it e.g. "alabaster-site").
2. **Enable the API**: APIs & Services → Library → "YouTube Data API v3" → Enable.
3. **OAuth consent screen**: APIs & Services → OAuth consent screen
   - User type: External · App name: "Alabaster site" · your email as support/contact
   - Scopes: add `.../auth/youtube.readonly`
   - Test users: add the channel owner's Google account
   - Then click **Publish app** (Production). In "Testing" mode Google expires
     the sign-in after 7 days. An unverified app is fine here: only you sign in,
     and you'll click through one "Google hasn't verified this app" warning.
4. **Create credentials**: APIs & Services → Credentials → Create credentials →
   OAuth client ID → Application type **Desktop app**. Copy the client ID and secret.
5. **Sign in once** from this repo:

       python3 scripts/youtube_auth.py CLIENT_ID CLIENT_SECRET

   Choose the Alabaster Group channel when asked, approve read-only access,
   and answer **y** to save the three GitHub secrets.
6. **Test it**: on GitHub → Actions → "Update livestream" → Run workflow.

## Manual override

You can always paste links into `src/data/livestream.json` by hand; the next
automatic run only replaces them when it finds a newer stream.

## Revoking access

Remove "Alabaster site" at https://myaccount.google.com/permissions and delete
the `YT_*` secrets in the repo settings.
