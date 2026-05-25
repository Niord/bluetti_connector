# Known Issues

- The upstream BLUETTI integration mixes Home Assistant lifecycle code with reusable transport and device logic. Workaround: extract `api/`, `model/`, `profile/`, and domain pieces from `models.py` before rebuilding UI or automation layers.
- Standalone authentication requirements are not fully documented outside Home Assistant. Workaround: validate the cloud login and token refresh path with a dedicated extraction spike before building a broader local UI.