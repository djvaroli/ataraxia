# Ataraxia deployment

The plan for running Ataraxia on a small VM and reading it on a phone, so that only
the owner can reach the app or the machine. This is the L06 design; the step-by-step
runbook is completed when L06 is implemented. Nothing here is provisioned yet.

## Shape

- One small Linux VM (Ubuntu 24.04 LTS, 1–2 GB RAM) running Docker Engine and the
  Compose stack from this repository.
- **No public inbound ports.** The VM joins the owner's Tailscale network, which
  needs no open ports. The phone uses the Tailscale app.
- `tailscale serve` provides HTTPS at `https://<machine>.<tailnet>.ts.net` with a
  valid certificate and forwards to nginx on `127.0.0.1:8080`.
- Firebase sign-in on top: even someone on the tailnet needs the owner's password.
  Add the `ts.net` hostname to Firebase's authorized domains.

Two independent locks (network membership and Firebase identity) protect the data,
and the machine has no internet-facing service to attack. Public HTTPS with a domain
and Caddy is a possible later alternative; it would add a public attack surface and
is not the default.

## Hardening checklist

1. Create a non-root user with sudo; install the owner's SSH public key.
2. In `/etc/ssh/sshd_config`: `PasswordAuthentication no`, `PermitRootLogin no`,
   `KbdInteractiveAuthentication no`. Restart sshd and confirm key login works in a
   second session before closing the first.
3. Enable `unattended-upgrades` for security updates.
4. Install Docker Engine from Docker's apt repository and Tailscale from its repository.
5. `tailscale up`, enable MagicDNS and HTTPS certificates in the Tailscale admin console,
   then `tailscale serve --bg 8080`.
6. Close public SSH: in the provider's firewall remove the inbound SSH rule (and all
   others), and SSH over the tailnet instead. Keep the provider's web console as the
   recovery path.
7. `ufw default deny incoming`, `ufw allow in on tailscale0`, `ufw enable`. Docker's
   published ports bypass ufw, which is why the Compose file binds nginx to `127.0.0.1`
   only; keep it that way.
8. Do not add users to the `docker` group other than the owner; it is root-equivalent.

## Configuration

`.env` on the VM, `chmod 600`, never committed:

| Variable | Value |
| --- | --- |
| `ATARAXIA_AUTH_MODE` | `firebase` |
| `ATARAXIA_FIREBASE_PROJECT_ID` | The dedicated Firebase project |
| `ATARAXIA_OWNER_UID` | UID of the manually created account |
| `ATARAXIA_FIREBASE_API_KEY`, `ATARAXIA_FIREBASE_AUTH_DOMAIN`, `ATARAXIA_FIREBASE_APP_ID` | Firebase web app configuration (public values) |
| `CLAUDE_CODE_OAUTH_TOKEN` | Optional; see [logging in](lessons.md#logging-in) |

Start with `docker compose up --build --detach --wait`, then log the worker in to
Claude.

## Backups

Required before trusting the app with months of history. A small command
(`python -m ataraxia.tools backup`) uses SQLite's online backup to write a consistent
copy, which a daily timer then sends off the VM: to a private cloud bucket with a
dedicated write-only credential, or over Tailscale to another of the owner's machines.
Keep 30 days. A restore drill (copy into an empty volume, start the stack, compare
lesson and event counts) must pass once before regular use.

## Updating

`git pull`, then `docker compose up --build --detach --wait`. Migrations run at API
start. Take a backup first when a release changes the schema.
