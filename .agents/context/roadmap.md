# Roadmap

## Active Workstreams
- Bootstrap the repository for standalone BLUETTI connector development.
- Extract a reusable Python core from the upstream Home Assistant integration.
- Build a local backend and a minimal local web page for state display and safe device control.

## Next Decisions
- Decide how upstream source will be referenced locally: vendored snapshot, subtree, or documented external reference.
- Define the standalone authentication approach that replaces the Home Assistant OAuth flow.
- Define the first supported command set for the local web page.

## Later
- Add repeatable test and smoke-check commands once the Python and web project structure exists.
- Decide packaging and distribution strategy for the standalone connector.