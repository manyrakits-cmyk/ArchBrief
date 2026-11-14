# Handoff: oživení ArchBrief (stav k 14. 11. 2026)

Cíl: rozjet celý stack (frontend na Vercelu + backend na Railway), aktualizovat a dostat ho do stavu,
kdy jeden demo scénář projde od začátku do konce bez chyby. Pak připravit na jednání s investorem.

## Zjištěný stav

### Repo
- GitHub `manyrakits-cmyk/ArchBrief`, výchozí větev `master`, poslední commit `d156825` (29. 6. 2026).
- `frontend`: `npm ci` + `npm run build` projde bez chyb.
- `backend`: závislosti se nainstalují, `server.py` se naimportuje, 8 endpointů:
  `/api/session/new`, `/api/chat`, `/api/projects`, `/api/session/<id>`, `/api/generate-image`,
  `/api/floorplan-svg`, `/api/export-pdf`, `/api/projects/<id>`.

### Vercel (frontend) — projekt `arch-brief`
- Poslední production deploy `READY` z commitu `d156825`, doména `arch-brief.vercel.app`.
- Env proměnné: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (production+preview), `VITE_API_URL` (jen production).
- **Zapnutá Vercel Authentication (SSO protection, "all_except_custom_domains").** Ověřit, jestli je
  `arch-brief.vercel.app` přístupná bez přihlášení — pro investora/testery musí být.
- `VITE_API_URL` míří na backend, který neběží (viz níže) → frontend teď nemůže fungovat.

### Railway (backend) — ROZBITÉ
Existují dva projekty se stejným repem, oba `FAILED`:
1. **`meticulous-energy`** — služba `web`. Má nastavené proměnné `ANTHROPIC_API_KEY`, `FAL_KEY`, `FLASK_APP`,
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Novější deploye (26.–29. 6.) jsou ve stavu `REMOVED`
   (pravděpodobně vypršel trial/kredit). → **Toto je ten správný projekt.**
2. **`alluring-flow`** — služby `web` (FAILED, žádné vlastní proměnné) a `proud-surprise` (prázdná).
   → Duplicitní pokus, po ověření smazat.

Pravděpodobné příčiny pádů:
- Railway účet / kredit — ověřit v dashboardu (Usage / Billing).
- `Procfile` spouští `flask run`, což je dev server; závisí na `FLASK_APP` (v alluring-flow chybí).
  Pro produkci nahradit `gunicorn`em: `web: cd backend && gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`
  (a přidat `gunicorn` do `backend/requirements.txt`). Timeout kvůli generování obrázků a PDF.
- Nejasné, jestli je Root Directory služby `backend/` nebo kořen repa — commity se o to přetahovaly
  (`archbrief_cli.py` přesunut do backend/, pak root `requirements.txt`). Sjednotit na jednu variantu.
- `CORS(app)` povoluje všechny originy — pro demo OK, před ostrým spuštěním omezit na doménu Vercelu.

### Zastaralé věci
- `MODEL = "claude-sonnet-4-6"` v `backend/archbrief_cli.py:30`. Aktuální modely: `claude-sonnet-5-5`,
  `claude-opus-5-5`, `claude-haiku-5-5`. Změna ovlivní chování agenta a cenu → ověřit na demo scénáři.
- Ověřit, že `fal-client` model ID pro Flux v `image_generator.py` stále existuje.
- `npm outdated`: minor updaty `@supabase/supabase-js`, `postcss`, `autoprefixer` jsou bezpečné.
  Majory (React 19, Vite 8, Tailwind 4, TS 7, lucide 1.x) **zatím ne**.
- Supabase: ověřit, že projekt není pozastavený (free tier se po neaktivitě pauzuje) a že Google OAuth
  má v redirect URLs doménu Vercelu i `localhost:5173`.

## Výsledek oživení (14. 11. 2026, večer)
- Railway `meticulous-energy` redeploynut → `SUCCESS` (zatím `flask run`). Supabase obnoven z pauzy.
- Otestováno na produkci (`arch-brief.vercel.app`): Google login ✅, seznam projektů ✅, otevření projektu ✅,
  nová konverzace + patch modelu ✅, vizualizace přes fal.ai ✅, půdorys ✅, `/api/export-pdf` → 200 ✅.

### Nalezené problémy pro demo (priorita)
1. **Model ztrácí prostory.** Projekt „Nový dům v Garganu": agent v chatu shrnul celý dům (obývák, kuchyň,
   ložnice, koupelny, technická místnost… + hostovská jednotka), ale v `program.spaces` jsou jen 3 prostory
   hostovské jednotky (54 m²). Půdorys i PDF pak ukazují jen 54 m². Prověřit `apply_patch` (přepisuje pole
   místo merge podle `id`?) a prompt v `archbrief_cli.py`, jestli agent posílá spaces v patchi.
2. **Vizualizace neodpovídá stylu.** Styl „minimalismus, kámen, bílá, sklo, středomořská", ale druhá generace
   dala dvoupatrový dům se sedlovou taškovou střechou. Zpřísnit prompt v `image_generator.py` (styl, střecha,
   podlažnost z modelu) a zvážit fixní seed pro demo.
3. **Formátování v PDF/exportu:** rozpočet `40000000` bez měny a oddělovačů (měna je v modelu `CZK`),
   style keywords spojené bez mezer (`minimalismus,kámen,bílá,sklo`).

## Plán (v tomto pořadí)

### Fáze 1 — rozjet lokálně
1. `git pull`, vytvořit `backend/.env` a `frontend/.env` podle `.env.example` (hodnoty z Railway/Vercel/Supabase dashboardu).
2. Spustit backend + frontend lokálně, projít celý flow: registrace → konverzace → model → půdorys → obrázek → PDF.
3. Sepsat seznam chyb, které se objeví. Nic zatím neopravovat bez souhlasu.

### Fáze 2 — opravit deploy
1. Railway: rozhodnout `meticulous-energy` jako jediný backend; ověřit kredit; sjednotit Root Directory;
   přejít na gunicorn; redeploy; ověřit `/api/session/new` z venku.
2. Vercel: `VITE_API_URL` nastavit na Railway doménu (production i preview), redeploy.
3. Supabase: OAuth redirect URLs, ověřit tabulky.
4. Vypnout nebo upravit Vercel Authentication, aby demo URL byla veřejná.
5. Smazat duplicitní Railway projekt `alluring-flow` (až po potvrzení).

### Fáze 3 — update
1. Minor updaty npm balíčků, `npx update-browserslist-db@latest`.
2. Model na `claude-sonnet-5-5`, otestovat demo scénář, porovnat kvalitu otázek a patchů.
3. Ověřit fal.ai model ID.

### Fáze 4 — stabilizace pro demo
1. Připravit jeden demo scénář (např. rodinný dům 4+kk pro pár s dětmi) a projít ho 3× bez chyby.
2. Ošetřit chybové stavy, které by mohly nastat živě (timeout LLM, selhání generování obrázku → fallback).
3. Teprve pak refaktoring — jen v rozsahu, který demo potřebuje.

## Definition of Done
- `https://arch-brief.vercel.app` je veřejně dostupná a demo scénář projde od registrace po PDF.
- Backend běží na jednom Railway projektu přes gunicorn, bez chyb v logu.
- Žádné secrets v repu, `.env.example` odpovídá skutečně používaným proměnným (doplnit backend `.env.example`).
