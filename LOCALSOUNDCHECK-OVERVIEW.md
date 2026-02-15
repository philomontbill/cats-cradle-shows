# Local Soundcheck - Tech Stack & Infrastructure

## How Everything Connects

```
CODE & HOSTING                         EMAIL
─────────────                         ─────
GitHub repo                           GoDaddy
(philomontbill/cats-cradle-shows)     (domain registrar + email plan)
       │                                     │
       │ auto-deploy on push                 │ Email Essentials $1.99/mo
       ▼                                     ▼
    Vercel ──────────────────────►   Microsoft 365 / Outlook
  (hosting + DNS)                    (info@localsoundcheck.com)
       │                                     │
       │ serves site                         │ accessed via
       ▼                                     ▼
 localsoundcheck.com                 Outlook app or outlook.office.com
```

**DNS flow for email:** Vercel DNS → MX/TXT/CNAME records → route to GoDaddy/Microsoft email servers

## Components

### GitHub
- **Repo:** `philomontbill/cats-cradle-shows`
- Source code for the entire site (HTML, CSS, JS, JSON show data)
- Pushes to `main` trigger auto-deploy on Vercel

### Vercel
- **Hosts the site** at localsoundcheck.com
- Auto-deploys from GitHub on every push
- **Manages all DNS records** for localsoundcheck.com (nameservers point to Vercel, not GoDaddy)
- Original URL before custom domain: `cats-cradle-shows.vercel.app`

### GoDaddy
- **Domain registrar** — owns localsoundcheck.com
- **Email Essentials plan** ($1.99/mo) for info@localsoundcheck.com, powered by Microsoft 365
- DNS editor is locked because nameservers point to Vercel — **all DNS changes must be made in Vercel**

### Microsoft 365 / Outlook
- Powers the **info@localsoundcheck.com** inbox
- Access via Outlook app or [outlook.office.com](https://outlook.office.com)

### Gmail
- **soundchecklocal@gmail.com** — original contact email
- Still active but being replaced by info@localsoundcheck.com for public use

## DNS Records (managed in Vercel)

Email setup required these records in Vercel's DNS panel:

| Type  | Purpose                              | Points to                     |
|-------|--------------------------------------|-------------------------------|
| MX    | Mail routing                         | GoDaddy/Microsoft mail servers|
| TXT   | SPF (email authentication)           | Microsoft 365 SPF record      |
| CNAME | autodiscover (email client config)   | Microsoft autodiscover        |
| CNAME | Email routing                        | GoDaddy/Microsoft servers     |

## Important Notes

- **GoDaddy DNS is locked** — nameservers point to Vercel, so all DNS changes go through Vercel's dashboard
- Email setup was done by adding TXT, CNAME, and MX records in Vercel's DNS

## Future Tasks

- [ ] Set up auto-forwarding from info@localsoundcheck.com to soundchecklocal@gmail.com
- [ ] Update Instagram and Facebook contact email to info@localsoundcheck.com
