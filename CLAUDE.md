# ArchBrief — instrukce pro Claude Code

Komunikuj česky. Piš přímo, bez konzultantských frází.

## Co je ArchBrief
Konverzační AI nástroj, který nahrazuje první schůzku klienta s architektem. Uživatel popisuje, jak chce bydlet,
agent se ptá (1–2 otázky najednou) a průběžně staví strukturovaný JSON model záměru. Výstup: shrnutí, profesní brief,
schematický půdorys (SVG), AI vizualizace a PDF export.

ArchBrief **není** CAD/BIM ani generátor designu. Agent nenavrhuje řešení a nerozhoduje za uživatele.

## Nedotknutelné principy (neměnit bez výslovného souhlasu)
- JSON model = single source of truth. Backend drží stav, LLM je stateless.
- LLM vrací jen `assistant_message` + `intent_model_update` (patch). Nikdy nepřepisuje celý model,
  nemaže existující data, nepřejmenovává ID, konflikty zapisuje do `conflicts` místo aby je řešil.
- Každá informace může mít `source` a `confidence`.
- Dvě vrstvy: topologie (spaces, relationships, zoning) je stabilní; geometrie je odvozená a přepočitatelná.
- Agent se na velikost místností ptá přes srovnání a kontext ("útulný obývák vs. prostor pro hosty"),
  ne přímo na m², a `area_target` z toho odvozuje.

Plná specifikace je v claude.ai projektu ArchBrief (docs 01–07, API contract, schema). Když narazíš na rozpor
mezi kódem a specifikací, zastav se a zeptej se.

## Stack
- `frontend/` — React 18 + Vite 5 + TypeScript + Tailwind 3, Supabase JS (auth vč. Google OAuth). Hosting: Vercel
  (projekt `arch-brief`, větev `master`, root `frontend/`).
- `backend/` — Python + Flask (`server.py`), Anthropic SDK, fal.ai (Flux), ReportLab + svglib, Supabase (service key).
  Hosting: Railway.
- Klíčové moduly: `archbrief_cli.py` (prompt, `EMPTY_MODEL`, `apply_patch`, `call_agent`, konstanta `MODEL`),
  `agent.py` (session logika), `floorplan.py` (geometrie + SVG), `pdf_generator.py`, `image_generator.py`,
  `supabase_client.py`.

## Proměnné prostředí
Backend: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `FAL_KEY` (čte ho `fal_client` sám).
Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` (URL backendu).
Secrets nikdy necommituj, nevypisuj do logů a neposílej do chatu. `.env` je v `.gitignore`.

## Lokální spuštění
```bash
# backend
cd backend && python -m venv .venv && .venv/Scripts/activate   # Windows; na Linux/mac: source .venv/bin/activate
pip install -r requirements.txt
python server.py            # http://localhost:5000

# frontend
cd frontend && npm ci && npm run dev   # http://localhost:5173
```

## Pravidla práce
- Před každou editací ukaž plán a počkej na souhlas (Ask before edits).
- Pracuj po malých krocích, každý krok = samostatný commit s popisnou zprávou (česky, prefix `fix:`/`feat:`/`chore:`/`refactor:`).
- Před commitem: `npm run build` ve `frontend/` musí projít; backend se musí naimportovat (`python -c "import server"`).
- Při práci s API, DB a secrets použij skill `secure-code`, pokud je dostupný.
- Neupgraduj major verze knihoven (React 19, Vite 8, Tailwind 4…) bez výslovného souhlasu.
