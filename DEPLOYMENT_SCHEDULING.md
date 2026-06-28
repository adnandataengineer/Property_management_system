# Deployment: scheduling & secrets

This covers two things that must be done on DigitalOcean for the finance
automation to work and to close the committed-secrets hole.

## 1. Rotate the exposed credentials (do this first)

The Gmail App Password, the Xero client secret, and the old `admin/admin`
superuser were previously hard-coded in the source and are in the git history.
Treat them as compromised and rotate them:

- **Gmail App Password** — Google Account → Security → App Passwords → revoke the
  old one, generate a new one. Use it as `EMAIL_HOST_PASSWORD`.
- **Xero client secret** — Xero Developer portal → your app → regenerate the
  client secret. Use it as `XERO_CLIENT_SECRET` (the client ID can stay).
- **Admin user** — set a strong `DJANGO_SUPERUSER_PASSWORD` and re-run
  `create_admin.py` (it now refuses to run without env-provided credentials).

The code no longer contains any fallback secrets — all of the above are read
from the environment only (see `.env.example` for the full list).

## 2. Set environment variables on the app

In the DigitalOcean control panel: **Apps → your app → Settings → App-Level
Environment Variables**, add everything listed in
`property_management/.env.example` (mark secrets as type **SECRET**). At minimum:
`SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`,
`XERO_REDIRECT_URI`.

## 3. Add the daily scheduled job

Without this, `send_rent_reminders` and `generate_monthly_invoices` never run on
their own — which is why invoices weren't going out. App Platform now supports
native cron jobs (minimum interval 15 minutes).

A single command runs both jobs:

```
python property_management/manage.py run_daily_finance_tasks
```

### Option A — Control panel (easiest)

1. Apps → your app → **Create → Create Resources / Add Component**.
2. Choose the **same GitHub repo/branch** as your web service.
3. Set the component **Resource Type** to **Job**.
4. Under **Job Trigger**, pick **On a schedule** and enter cron `0 7 * * *`
   with time zone **Europe/Dublin** (daily at 07:00).
5. Set the **Run Command** to:
   `python property_management/manage.py run_daily_finance_tasks`
6. Confirm the job inherits the app-level env vars (DATABASE_URL, email, Xero).
7. Save and deploy.

### Option B — App spec via doctl

```
# Pull your current spec
doctl apps spec get <APP_ID> > app.yaml

# Add the job block from deploy/scheduled-job.yaml under the top-level `jobs:`
# key (edit github.repo/branch to match your web component), then push it back:
doctl apps update <APP_ID> --spec app.yaml
```

The job block to merge in lives in `deploy/scheduled-job.yaml`.

## 4. Configure bank details + enable invoicing

- Django admin → **Finance → Finance settings**: fill in the bank/payment
  routing fields and set the reminder lead time (default 10 days).
- Set **Enable monthly invoices** if you want `generate_monthly_invoices` to
  create Xero invoices on the due day.
- Make sure Xero is connected (Finance dashboard → Connect to Xero); the token
  now auto-refreshes, so this only needs doing once.

## 5. Verify

After the first scheduled run, check **Apps → your app → Runtime Logs** for the
`daily-finance` job. You should see the `=== Daily finance tasks ... ===`
banners and per-tenant send/skip lines. You can also trigger it on demand from
the job component's **Run** button (control panel) to test immediately.
