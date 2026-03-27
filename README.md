# MFK Frydek-Mistek - Web Archive

Complete offline archive of [mfkfm.cz](https://mfkfm.cz) - the website of Czech football club MFK Frydek-Mistek.

## Local Development

```bash
docker compose up
```

Open http://localhost:8080

## Production

Deployed automatically via GitHub Actions to `fotbal-fm-archiv.thedevs.cz`.

## Structure

- `web/` - PHP application serving the archived pages
- `web/pages/` - 12,000+ cached HTML pages
- `web/assets/` - Static assets (photos, CSS, JS, logos)
- `scraper/` - Python scripts used to scrape the original site
