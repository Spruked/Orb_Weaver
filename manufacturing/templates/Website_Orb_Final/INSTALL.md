# Install your Website ORB

This package contains your approved site data and a self-contained browser
widget. It does not need the factory's API, database, vocabulary, or checkout.
It requires a customer-controlled Python server; uploading files to a static
website alone does not run the backend.

Unzip the `.orbpack`, enter `website-orb`, and use Python 3.10 or newer:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python run.py --check
.venv/bin/python run.py --port 8787
```

The purchaser names the ORB in Orb Weaver's customer setup before downloading
the package. That identity is compiled into `payload/site_config.json` and is
returned by `/orb/bootstrap`, so the installed ORB can be named for the
business, such as `Harley`, instead of inheriting a generic assistant name.

On Windows use `.venv\Scripts\python.exe` instead. Keep the server bound to
loopback behind your HTTPS reverse proxy. Proxy `/orb/` to port 8787, then add
this to the approved customer website (replace the example with your server):

```html
<script src="https://YOUR-RUNTIME-HOST/orb/widget.js" defer></script>
```

The script infers its own backend origin. The site's origin must appear in the
approved `site_config.json` allowlist. Cross-origin deployments, branding and
site goals must be configured before the build is approved. Do not hand-edit
hashed payload files: rebuild and reapprove them after a rescan.

Text answers and lexical/route guidance work offline from the installed Vault.
Speech needs customer-controlled services configured on the server:

```sh
export FASTER_WHISPER_STT_URL=http://127.0.0.1:13000/api/stt/transcribe
export ORB_TTS_KOKORO_URL=http://127.0.0.1:8880/speak
```

These are examples, not bundled speech servers. Voice uses browser microphone
permission and HTTPS, never browser speech recognition/synthesis. Missing
providers leave text available. No LLM or model weights are bundled; this
version answers from approved evidence, not unrestricted model generation.

Pointers require unique visible DOM matches on the current route and never
click or submit forms. Navigation is a proposed customer-site link the visitor
chooses. Unknown, ambiguous or missing targets remain unresolved.

All persisted runtime data stays in `runtime/vault_system`. Back up that entire
directory. The package manifest records the site, scan, artifact hashes and
compiler/build versions. Hash validation detects changed files; it is not a
cryptographic publisher signature. Add TLS, request rate limits and upload
limits at your reverse proxy before exposing the service publicly.
