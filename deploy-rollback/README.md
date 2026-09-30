# Deploy script with automatic rollback

Genericized from a script I use to deploy a production bot worker. Real
hostnames, app paths, and container names are replaced with placeholders —
the logic is otherwise unchanged.

## The pattern

A deploy that can fail two different ways, and a script that watches for
both:

- **Build/restart itself fails** (bad syntax, a broken dependency, `docker
  compose up` exiting non-zero) → caught immediately, image tag rolled back
  before the script exits.
- **Build succeeds but the app doesn't come up healthy** (crash on startup,
  missing env var, import error) → caught by grepping recent container
  logs for a known-good startup marker string; if it's not there, same
  rollback path runs automatically.

Either way, a bad deploy self-heals without anyone needing to notice and
intervene manually — the previous image is already tagged and ready before
the risky step (rebuild) even runs.

## Usage

```powershell
.\deploy.ps1 -RemoteHost "deploy@your-server" -RemoteAppDir "/opt/yourapp" `
             -ImageName "yourapp-worker" -ContainerName "yourapp-worker-1" `
             -StartupMarker "Application startup complete"

# upload + syntax check only, no build/restart:
.\deploy.ps1 -DryRun
```
