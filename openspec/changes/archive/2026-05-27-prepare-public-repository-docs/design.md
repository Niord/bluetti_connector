## Context

The repository has grown from a standalone Python extraction into a mixed project: Python core/backend, backend-served local web page, Swift package, and SwiftUI macOS sample. The root README currently carries setup details, verification notes, current-scope history, and roadmap-style statements in one file, while upstream provenance is only documented in agent context.

This change prepares the repository for public viewing by improving navigation, attribution, and setup guidance without moving code or changing runtime behavior.

## Goals / Non-Goals

**Goals:**

- Make the root README a concise public landing document for the repository.
- Split detailed setup and verification instructions into module-focused docs.
- Publicly document the relationship to the official BLUETTI Home Assistant integration and preserve upstream provenance.
- Add lightweight repository guidance for contribution and security reporting.
- Keep documentation consistent with the existing package layout and commands.

**Non-Goals:**

- Do not restructure source directories or rename Python/Swift modules.
- Do not change backend routes, local web behavior, Swift APIs, sample app behavior, or authentication flows.
- Do not introduce CI, release automation, installers, or package publishing in this slice.
- Do not claim official BLUETTI affiliation beyond documented provenance from the official upstream repository.

## Decisions

1. Use the root README as a map, not as the full manual.

   Rationale: first-time readers need to understand what this repository contains before they need fake-gateway or live-account verification details. Detailed instructions will move into module docs while the README links to them.

   Alternative considered: keep all setup instructions in the root README and only edit wording. Rejected because the current single-page structure already hides the module boundaries the public documentation needs to clarify.

2. Put public documentation under `docs/`.

   Rationale: `docs/` is a familiar public location and avoids exposing agent-only context as the primary reader path. Module READMEs can stay useful, but the public docs provide consistent cross-module navigation.

   Alternative considered: move all details into existing module READMEs only. Rejected because the local web page is packaged under the Python package and does not have a natural public README location of its own.

3. Keep upstream provenance public and separate from internal agent notes.

   Rationale: public readers should see that the work is based on the official BLUETTI Home Assistant integration and which upstream files informed the extraction. `NOTICE` and `docs/upstream.md` will carry that information without requiring readers to inspect `.agents/`.

   Alternative considered: link directly to `.agents/context/upstream-provenance.md`. Rejected because `.agents/` is a working context area, not a stable public documentation surface.

4. Treat the macOS app as a sample, not a packaged product.

   Rationale: the existing `swift/BluettiMonitorSample` target is useful as an executable reference and copyable Xcode example, but this change should not imply production app distribution, signing, or installer support.

## Risks / Trade-offs

- [Documentation drift] -> Keep commands copied from current README and module READMEs, then run focused validation commands after editing.
- [Overstating official status] -> Use careful wording: based on and verified against the official upstream repository, but not an official BLUETTI product unless that changes.
- [Too many docs for a small project] -> Keep docs focused on module setup and public trust topics, with the root README acting as a short index.
- [Missing license choice] -> Add public attribution and repository guidance now, but only add a LICENSE file if the license can be stated consistently with upstream attribution and project intent.
