#!/usr/bin/env bash
# Regenerate the committed stylesheets from their Tailwind v4 source files.
#
# The site is a Python static-site generator that must build offline in CI with
# no Node toolchain, so Tailwind is a DEV-TIME step only: it compiles the
# *.src.css sources into committed *.css artifacts that main.py ships verbatim.
# Run this after editing assets/page.src.css or assets/landing.src.css, then
# commit the regenerated page.css / landing.css alongside the source change.
#
# Tailwind standalone CLI (no npm): https://tailwindcss.com/blog/standalone-cli
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
assets="$here/assets"

# Prefer an on-PATH tailwindcss, fall back to the user-local install.
if command -v tailwindcss >/dev/null 2>&1; then
  TW="$(command -v tailwindcss)"
elif [ -x "$HOME/.local/bin/tailwindcss" ]; then
  TW="$HOME/.local/bin/tailwindcss"
else
  echo "ERROR: tailwindcss standalone CLI not found." >&2
  echo "Install it (Linux x64) with:" >&2
  echo "  curl -fsSL -o ~/.local/bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 && chmod +x ~/.local/bin/tailwindcss" >&2
  exit 1
fi

echo "Using $("$TW" --help 2>&1 | grep -oiE 'tailwindcss v[0-9.]+' | head -1) ($TW)"

build() {
  local src="$1" out="$2"
  echo "  $src -> $out"
  "$TW" -i "$assets/$src" -o "$assets/$out" --minify
}

build page.src.css    page.css
build landing.src.css landing.css

echo "Done. Regenerated assets/page.css and assets/landing.css."
