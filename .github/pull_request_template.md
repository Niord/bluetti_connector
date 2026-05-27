## Summary

Describe the user-visible or repository-visible change in 2-4 sentences.

## Scope

- [ ] Python backend or core
- [ ] Local web page
- [ ] Swift package
- [ ] macOS sample app
- [ ] Documentation or repository automation

## Verification

List the exact commands or checks you ran.

```text
.venv/bin/python -m pytest ...
.venv/bin/python -m ruff check ...
node --check ...
node --test ...
swift test
swift build
```

## Safety Checklist

- [ ] I did not include access tokens, refresh tokens, `.env` contents, token-store files, or account-specific logs.
- [ ] I redacted unnecessary BLUETTI account details and device identifiers.
- [ ] I updated docs, specs, or roadmap context when the change required it.

## Notes

Add anything a reviewer should know about scope boundaries, follow-up work, or intentionally deferred pieces.