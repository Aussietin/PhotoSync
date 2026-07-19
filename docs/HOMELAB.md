# Self-hosting PhotoSync in a homelab

PhotoSync is built to be fully self-hosted: no cloud, no external APIs, all AI
on-device. This guide covers running it as a long-lived service on homelab
infrastructure — a NAS or mini-PC with Docker, or a Kubernetes (k3s) cluster —
with the library on network storage.

Two deployment paths, both using the prebuilt multi-arch images
(amd64 + arm64) from GHCR:

| Path | Files | Good for |
|------|-------|----------|
| Docker Compose | `docker-compose.homelab.yml` | NAS, mini-PC, single VM |
| Kubernetes | `deploy/k8s/` (kustomize) | k3s / homelab clusters |

Images: `ghcr.io/aussietin/photosync-backend` and
`ghcr.io/aussietin/photosync-frontend`, published by
`.github/workflows/docker-publish.yml` on every push to `main` (`latest`) and
on version tags.

## How storage is laid out

Everything the app persists lives under **one directory**, set by the
`DATA_DIR` env var (default `/data` in the homelab deployments):

```
/data/
├── photosync.db   # SQLite database (catalog, tags, faces, embeddings)
├── uploads/       # originals copied in via browser upload
├── thumbnails/    # 400px grid thumbnails
├── previews/      # 1600px web-friendly JPEGs (HEIC → browser)
└── faces/         # cropped face thumbnails
```

Mount your storage of choice at `/data` and you're done. Each path is also
individually overridable (`DATABASE_URL`, `UPLOAD_DIR`, `THUMBNAIL_DIR`,
`PREVIEW_DIR`, `FACE_DIR`) — which matters for the next section.

### ⚠️ SQLite and NFS don't mix

SQLite depends on file locking that NFS implements unreliably; a database on
an NFS share risks corruption. If `/data` lives on NFS or SMB:

- keep **media** on the share (uploads/thumbnails/previews/faces are plain
  files, written once — totally fine on NFS), and
- point the **database** at local/block storage:

```
DATABASE_URL=sqlite+aiosqlite:////dblocal/photosync.db
```

with `/dblocal` on a local disk (bind mount in Compose, local-path or
Longhorn PVC in Kubernetes). Both deployment files ship commented-out
examples of exactly this split. A `/data` volume on a **local** disk or a
block-storage PVC needs none of this — the default single-directory layout is
fine there.

### Importing a library that already lives on the NAS

Folder import references photos **in place** — it stores the path rather than
copying the file. So you can mount your existing photo share read-only into
the backend container (both deployment files show a `/library` example
mount), then in the UI run **Import → `/library`**. 20k photos are indexed
without duplicating a single original, and the read-only mount guarantees
PhotoSync can never touch them (on top of the `DELETE_IN_PLACE_ORIGINALS`
safety guard, default off).

Don't rename or move that share afterwards — the library stores those paths.

## Path 1 — Docker Compose (NAS / mini-PC)

```bash
git clone https://github.com/Aussietin/PhotoSync && cd PhotoSync
echo "API_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
docker compose -f docker-compose.homelab.yml up -d
# UI at http://<host>/ — paste the token when prompted
```

By default state goes in a named Docker volume (`photosync_data`). To put it
on network storage, pick one in `.env` / the compose file:

- **Bind mount** (simplest if the host already mounts the NAS):
  `PHOTOSYNC_DATA=/mnt/nas/photosync` in `.env`
- **NFS or SMB Docker volume**: uncomment the `driver_opts` recipe at the
  bottom of `docker-compose.homelab.yml` — Docker mounts the share itself, no
  host fstab entry needed.

Remember the SQLite caveat above if you choose either network option.

## Path 2 — Kubernetes (k3s and friends)

```bash
# 1. Create the namespace + token secret
kubectl create namespace photosync
kubectl create secret generic photosync -n photosync \
  --from-literal=API_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Review deploy/k8s/ (PVC size/StorageClass, ingress hostname), then
kubectl apply -k deploy/k8s/
```

What you get:

- **backend** — 1 replica, `Recreate` strategy (SQLite: never scale this out),
  `/data` on the `photosync-data` PVC, health probes on `/api/health`,
  token from the `photosync` secret.
- **frontend** — nginx serving the SPA and proxying `/api` + media routes to
  the backend service (`BACKEND_URL` env, no rebuild needed).
- **ingress** — single host rule to the frontend; works out of the box with
  k3s Traefik. On nginx-ingress add
  `nginx.ingress.kubernetes.io/proxy-body-size: 512m` for uploads.

Storage options, in order of homelab-likelihood:

1. **Default StorageClass** (k3s `local-path`): fine as-is; the library lives
   on whichever node the pod lands on.
2. **NFS provisioner / CSI** (nfs-subdir-external-provisioner, Longhorn,
   democratic-csi → TrueNAS): set `storageClassName` in `pvc.yaml`. If the
   class is NFS-backed, apply the SQLite split (commented env in
   `backend.yaml`).
3. **Direct NFS PV, no provisioner**: edit `nfs-pv.example.yaml` and follow
   the comments there.

Pin image tags for reproducible deploys via the `images:` block in
`kustomization.yaml` (release tags like `v1.0.0` are published alongside
`latest`).

## Access, auth, and HTTPS

- `API_TOKEN` is **required** in both homelab deployments — the backend
  serves your entire library to anyone who can reach it otherwise. All API
  and media routes require the token; the UI prompts once and stores it.
- The backend is intentionally not exposed outside the stack/cluster; the
  frontend proxies everything, so only port 80 (or the ingress) is reachable.
- For HTTPS, terminate TLS at the layer you already run — a reverse proxy
  (Traefik, Caddy, NPM) in front of the Compose stack, or cert-manager on
  the ingress. PhotoSync itself needs no TLS configuration.
- Prefer keeping it LAN/VPN-only (Tailscale/WireGuard) over internet-exposed.

## Backups

The catalog — tags, people/faces, albums, trash state, CLIP embeddings — is
the SQLite file; the media dirs are plain files. Snapshot/rsync `/data`
(plus the DB path if you split it) and you have a complete backup. Restore is
"put it back and start the container". Back up the DB file while the backend
is stopped, or use `sqlite3 photosync.db ".backup ..."` for a hot copy.

## Environment reference (homelab-relevant)

| Variable | Default | Notes |
|----------|---------|-------|
| `DATA_DIR` | `backend/` (source dir); `/data` in homelab deploys | Root for DB + all media dirs |
| `DATABASE_URL` | `sqlite+aiosqlite:///<DATA_DIR>/photosync.db` | Override to move the DB off NFS |
| `UPLOAD_DIR` / `THUMBNAIL_DIR` / `PREVIEW_DIR` / `FACE_DIR` | `<DATA_DIR>/<name>` | Individual overrides |
| `API_TOKEN` | *(empty = open)* | Required by both homelab deployments |
| `BACKEND_URL` (frontend) | `http://backend:8000` | Where nginx proxies `/api` + media |
| `MAX_UPLOAD_SIZE_MB` | `50` | Per-file backend limit (nginx allows 512m) |
| `TRASH_RETENTION_DAYS` | `30` | Trash auto-empty window |
| `DELETE_IN_PLACE_ORIGINALS` | `false` | Keep `false` when importing a mounted library |
