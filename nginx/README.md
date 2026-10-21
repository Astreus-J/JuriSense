# Nginx reverse proxy

`nginx.conf` is the only config file this container loads (mounted read-only by
`docker-compose.prod.yml`). It listens on plain HTTP :80 and routes `/api/*` to the
`backend` service, everything else to `frontend` — see that file's comments for why.

## TLS

The default setup assumes an edge proxy (Cloudflare, per
`docs/04-architecture/deployment.md`'s diagram) terminates TLS and forwards plain HTTP to
the VPS. If you point DNS straight at the VPS with no edge proxy in front, this container
needs to terminate TLS itself instead:

1. Point the domain's DNS `A`/`AAAA` record at the VPS.
2. Get a certificate (Let's Encrypt via certbot is the standard free option):
   ```sh
   docker run --rm -p 80:80 \
     -v /etc/letsencrypt:/etc/letsencrypt \
     certbot/certbot certonly --standalone -d your-domain.example
   ```
   (stop the `nginx` container first so certbot can bind :80 itself for the HTTP-01
   challenge, then start it again afterward).
3. Mount `/etc/letsencrypt` into the `nginx` service in `docker-compose.prod.yml`
   (`- /etc/letsencrypt:/etc/letsencrypt:ro`) and add a `443` server block to
   `nginx.conf`:
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.example;
       ssl_certificate     /etc/letsencrypt/live/your-domain.example/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.example/privkey.pem;
       # ... same location blocks as the :80 server ...
   }
   server {
       listen 80;
       server_name your-domain.example;
       return 301 https://$host$request_uri;
   }
   ```
4. Publish `443:443` on the `nginx` service and set up certbot renewal (a cron job or
   systemd timer running the same `certbot renew` command periodically, then
   `docker compose -f docker-compose.prod.yml restart nginx`).

If you use Cloudflare, the simpler and recommended path is: enable Cloudflare proxying
(orange cloud) on the DNS record, set the Cloudflare SSL/TLS mode to **Full** (or **Full
(strict)** using a Cloudflare Origin CA certificate mounted the same way as above), and
leave this container on plain HTTP :80 as shipped.
