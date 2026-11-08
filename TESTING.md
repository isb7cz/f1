# Ověření první verze – 8. listopadu 2026

## Skutečná data a běžící aplikace

Spuštěno `python3 app.py --host 0.0.0.0 --port 8000`.
Server si sám stáhl Novu, bez podstrčení průzkumného JSON. API `/api/weekend`
vrátilo `ready`, `stale: false`, GP São Paula a tři dny 6.–8. 11. 2026.
Ověřeny tréninky, kvalifikace, úvodní studio 17:00 a závod 17:50.
Reprízy, závěrečné studio a F1 Academy se na stránce nezobrazily.

Po posunutí času pouze v testu na 10. 11. vybrala stejná skutečná data
Las Vegas: první trénink 20. 11. v 01:25, závod 22. 11. ve 04:50.
Produkční aplikace nemá testovací přepínač času ani pevně zadanou GP.

## Automatické testy

`python3 -m unittest discover -s tests -v`: **9 testů, 9 prošlo**.

- Aktuální víkend zůstává do konce závodu, poté přechází na další.
- Noční přenos se zobrazí pod skutečným českým kalendářním datem.
- Převod z UTC v létě, zimě i během opakované hodiny při změně času.
- Simulovaný sprintový víkend včetně sprintové kvalifikace.
- Reprízy, nejasné/rozporné příznaky a Academy jsou vyloučené.
- Prázdný program vrátí stav „zatím není k dispozici“, žádné vymyšlené časy.
- Změněná struktura Novy způsobí chybu parseru, nikoli falešný úspěch.
- Výpadek zachová uložená data a zobrazí upozornění; bez cache vrátí chybu.
- HTTP API a stránka fungují i pro prázdný program.

`node --check web/app.js`: prošlo.

## Prohlížeč

`python3 tests/browser_smoke.py`: **3 scénáře zařízení prošly v Chromiu**:

- iPhone rozměr 390 × 844.
- iPad rozměr 768 × 1024.
- Mac rozměr 1440 × 1000.

Každý scénář načetl skutečnou stránku a API, porovnal všechny zobrazené časy,
ověřil nepřítomnost vodorovného přetečení a JavaScriptových chyb, stav bez
programu, chybu, upozornění na stará data a následující víkend. Časové pásmo
prohlížeče bylo úmyslně America/Los_Angeles; časy zůstaly české.
Snímky jsou v ignorovaném `test-results/`.

WebKit byl stažen a jeho spuštění vyzkoušeno, ale v cloudovém systému chybí
knihovny GTK/GLES a není k dispozici oprávnění pro jejich systémovou instalaci.
**Nativní Safari ani fyzické Apple zařízení proto testovány nebyly.**
Použité rozhraní a styly míří na současné Safari; to není náhradou skutečného
testu na iPhonu/iPadu/Macu. Na Macu lze aplikaci místně ověřit přes `Spustit.command`.

Sprintová data jsou simulovaná: v načteném živém vzorku sprint nebyl.
Budoucí automatické stažení za šest hodin nebylo odčekáno; interval je
implementován v serverovém aktualizačním vlákně. První automatické stažení,
cache a výpadkové chování byly ověřeny.

Veřejné nasazení nebylo provedeno.
