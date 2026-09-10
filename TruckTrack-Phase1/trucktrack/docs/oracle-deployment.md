# Oracle Cloud Always Free Deployment

This project is already container-ready. The simplest free deployment path is an Oracle Cloud Always Free compute instance running Docker.

## Recommended setup

- Oracle Cloud Compute Always Free VM
- Ubuntu 22.04 or Oracle Linux
- Docker installed on the VM
- SQLite database stored on the VM disk, or PostgreSQL if you prefer a separate managed database later

SQLite is the easiest free option for this repo because the app already defaults to a local database file. If you want stronger database isolation, switch `DATABASE_URL` to PostgreSQL before launching the container.

## 1. Create the VM

Create an Always Free compute instance, then allow inbound traffic for:

- TCP 22 for SSH
- TCP 80 for HTTP
- TCP 443 for HTTPS if you later add a reverse proxy

Use a public subnet and note the public IP address.

## 2. Install Docker

On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

## 3. Get the code onto the VM

Clone the repository on the VM:

```bash
git clone https://github.com/Nixxzzzzz/Truck.git
cd Truck/TruckTrack-Phase1/trucktrack
```

## 4. Configure environment variables

Create a `.env` file on the VM:

```bash
cp .env.example .env
```

For a SQLite-based free deployment, set `DATABASE_URL=sqlite:////data/trucktrack.db` and mount a persistent `/data` directory into the container.

Set these values before first boot if you want the container to bootstrap the admin user automatically:

- `ADMIN_USERNAME`
- `ADMIN_NAME`
- `ADMIN_PASSWORD`

Set `COOKIE_SECURE=true` only after the site is behind HTTPS. If you are starting with plain HTTP on the VM, keep it `false` until you add TLS.
If you access the app by public IP, add that IP address to `ALLOWED_HOSTS` as well.

## 5. Build and run

```bash
docker build -t trucktrack .
docker run -d \
  --name trucktrack \
  --restart unless-stopped \
  -p 80:8000 \
  --env-file .env \
  -v "$PWD/data:/data" \
  trucktrack
```

The bind mount keeps the SQLite database on the VM disk so data survives container restarts. If you later switch to PostgreSQL, remove the volume mapping and update `DATABASE_URL`.

## 6. Check the app

- Home: `http://YOUR_PUBLIC_IP/`
- Health: `http://YOUR_PUBLIC_IP/health`

If you added an admin bootstrap secret, sign in with that account after the first start, then remove the bootstrap variables from `.env` or the cloud secret store.

## 7. Updates

When you pull new code:

```bash
docker stop trucktrack
docker rm trucktrack
git pull
docker build -t trucktrack .
docker run -d \
  --name trucktrack \
  --restart unless-stopped \
  -p 80:8000 \
  --env-file .env \
  -v "$PWD/data:/data" \
  trucktrack
```

If you want HTTPS on Oracle Cloud, place Nginx or Caddy in front of the container and point it at `127.0.0.1:8000`.