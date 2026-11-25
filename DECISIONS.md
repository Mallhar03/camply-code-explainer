# Decisions

- D1: Python 3.11+ is required. The initial build environment has Python 3.12.3, while retaining a 3.11-compatible dependency floor.
- D5 deviation: Use Gemini API via Google's `google-genai` SDK instead of Anthropic. The owner has a Gemini API key and requested an option that avoids paid API usage; use the provider's free tier and stay within its limits. A Gemini Pro subscription is separate from API access. Revisit if the free tier is unavailable or insufficient.
- D15: The repository root is `/home/mallhar/Desktop/camply` in the local example configuration.
