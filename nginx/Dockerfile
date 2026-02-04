FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

COPY docker-entrypoint.d/ /docker-entrypoint.d/
RUN chmod +x /docker-entrypoint.d/*.sh
COPY templates/ /etc/nginx/templates-src/
RUN mkdir -p /etc/nginx/templates
