#!/usr/bin/env bash
# Harvest whatever the render box has finished, build it, and stage it in
# kind_robots -- the whole path from queue to game in one command.
#
#   bash scripts/deliver.sh              # harvest, build, submit waiting videos, sync
#   bash scripts/deliver.sh --no-sync    # stop before touching kind_robots
#
# Needs KR_API_TOKEN, a conductor checkout next to this repo (for the queue
# client), and a kind_robots checkout next to it (for the sync). Idempotent:
# run it as often as you like; it only does what is new.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
kind_robots="${KIND_ROBOTS:-$here/../kind_robots}"
sync=1
[[ "${1:-}" == "--no-sync" ]] && sync=0

cd "$here"
python3 scripts/render_art.py harvest
python3 scripts/build_sprites.py
python3 scripts/build_story_art.py
# Clips whose source still just arrived can go now.
python3 scripts/render_art.py submit videos
python3 scripts/render_art.py status

if [[ $sync == 1 ]]; then
  (cd "$kind_robots" && node scripts/sync_cthulhuquarium_canon.mjs "$here")
  echo "Staged in $kind_robots -- review, test and open a PR there."
fi
