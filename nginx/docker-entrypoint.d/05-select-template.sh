#!/usr/bin/env sh
set -eu

# This runs before nginx's built-in envsubst script (20-envsubst-on-templates.sh).
# It selects a single template into /etc/nginx/templates/default.conf.template.
#
# Supported templates:
# - dev  -> /etc/nginx/templates/dev.conf.template
# - prod -> /etc/nginx/templates/prod.conf.template
#
# Env:
# - NGINX_TEMPLATE=dev|prod (default: prod)

template="${NGINX_TEMPLATE:-prod}"

case "$template" in
  dev|prod) ;;
  *)
    echo "[nginx] Invalid NGINX_TEMPLATE: ${template} (expected dev|prod)" >&2
    exit 1
    ;;
esac

src="/etc/nginx/templates/${template}.conf.template"
dst="/etc/nginx/templates/default.conf.template"

if [ ! -f "$src" ]; then
  echo "[nginx] Template not found: ${src}" >&2
  exit 1
fi

cp "$src" "$dst"

