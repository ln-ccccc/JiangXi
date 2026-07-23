#!/usr/bin/env bash
set -euo pipefail

curl -fsS "http://127.0.0.1:5008/" >/dev/null
curl -fsS "http://127.0.0.1:4000/" >/dev/null
