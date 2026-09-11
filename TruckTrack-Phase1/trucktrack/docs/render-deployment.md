# Render Deployment

TruckTrack can run on Render as a Docker web service.

## Recommended setup

- Render Web Service using the Dockerfile in this repo
- Render PostgreSQL if you want persistent data across deploys
- `DATABASE_URL` from the database connection string
- `COOKIE_SECURE=true`
- `ALLOWED_HOSTS` including your Render service hostname

## 1. Create the web service

In Render, create a new Web Service from this GitHub repository.

Use these settings:

- Runtime: Docker
- Branch: `main`
- Health check path: `/health`

Render will build the image from [Dockerfile](../Dockerfile).

## 2. Add a database

For persistent data, create a Render PostgreSQL database and copy its connection string.

Set the `DATABASE_URL` environment variable in the web service to that connection string.

## 3. Add environment variables

Set these in the Render web service:

- `APP_TIMEZONE=Asia/Kolkata`
- `SESSION_HOURS=12`
- `COOKIE_SECURE=true`
- `ALLOWED_HOSTS=<your-render-service>.onrender.com`

Optional first-run admin bootstrap values:

- `ADMIN_USERNAME`
- `ADMIN_NAME`
- `ADMIN_PASSWORD`

## 4. Deploy

Deploy the service and wait for the migration step to complete.

After the first successful deploy, open the service URL and sign in with the admin account you created.

## 5. Update the app later

Push changes to `main`. Render will redeploy automatically if auto-deploy is enabled.

If you need a ready-made blueprint, use [render.yaml](../render.yaml). If Render blueprint database creation is not available on your account, create the PostgreSQL database manually and set `DATABASE_URL` in the web service settings.