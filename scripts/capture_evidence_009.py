"""Captura screenshots after para evidência T042 (009-persona-visual-redesign).

Pré-requisitos:
  python manage.py migrate
  python scripts/seed_evidence_007.py
  python manage.py runserver 127.0.0.1:8000

Uso:
  python scripts/capture_evidence_009.py [--base-url http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / 'specs/009-persona-visual-redesign/evidence/before-after'
PASSWORD = 'TestPass123!'

CAPTURES = [
    {
        'slug': '01-personal-charts',
        'path': '/',
        'email': 'colab@test.greenn.com.br',
        'wait_ms': 2500,
    },
    {
        'slug': '02-team-panel',
        'path': '/dashboard/team/',
        'email': 'lider@test.greenn.com.br',
        'wait_ms': 2500,
    },
    {
        'slug': '03-admin-charts',
        'path': '/dashboard/admin/',
        'email': 'admin@test.greenn.com.br',
        'wait_ms': 2500,
    },
    {
        'slug': '04-structure-panel',
        'path': '/dashboard/structure/',
        'email': 'admin@test.greenn.com.br',
        'wait_ms': 2500,
    },
    {
        'slug': '05-adherence-panel',
        'path': '/dashboard/adherence/',
        'email': 'admin@test.greenn.com.br',
        'wait_ms': 2500,
    },
    {
        'slug': '06-ciclo-detail-panel',
        'path': '/cycles/1/',
        'email': 'admin@test.greenn.com.br',
        'wait_ms': 2500,
    },
]


def login(page, base_url: str, email: str) -> None:
    page.goto(f'{base_url}/accounts/login/', wait_until='networkidle')
    page.fill('input[name="username"]', email)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    base_url = args.base_url.rstrip('/')

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright não instalado — pip install playwright && playwright install chromium', file=sys.stderr)
        return 1

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for item in CAPTURES:
            context = browser.new_context(viewport={'width': 1280, 'height': 900})
            page = context.new_page()
            login(page, base_url, item['email'])
            page.goto(f"{base_url}{item['path']}", wait_until='networkidle')
            page.wait_for_timeout(item['wait_ms'])
            out = EVIDENCE_DIR / f"{item['slug']}-after.png"
            page.screenshot(path=str(out), full_page=True)
            print(f'CAPTURED {out.name} ({item["email"]} → {item["path"]})')
            context.close()

        browser.close()

    print('CAPTURE_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
