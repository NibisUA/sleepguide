# Security and configuration

SleepGuide handles personal diary data. Use synthetic data in development,
screenshots, bug reports, and demonstrations.

## Credentials

- Keep real bot tokens, database passwords, JWT signing secrets, and webhook
  secrets in local environment files or the deployment platform's secret store.
- Commit only sanitized templates such as `backend/.env.example` and
  `.env.prod.example`. Never replace their placeholders with production values.
- Frontend bundles are public. Variables exposed to browser code must never
  contain server credentials or signing secrets.
- Production configuration requires a bot token, strong JWT and webhook secrets,
  HTTPS endpoints, and disabled development login. See
  [the release guide](docs/RELEASE.md).

The repository's `.gitignore` excludes local environment files, private keys,
credential files, database backups, logs, and generated exports. Ignore rules do
not remove a secret that was already committed.

## Checks before committing

Install the optional local hook:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The GitHub Actions secret scan also checks pushed history with Gitleaks. These
checks reduce accidental exposure; they do not replace reviewing a change before
committing it.

## If a credential is exposed

Revoke or rotate it at its provider first. Then remove it from tracked files and
review all affected branches and history. Do not paste credentials or real user
exports into public issues, pull requests, or screenshots.
