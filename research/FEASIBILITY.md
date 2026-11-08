# Ověřená proveditelnost – 8. 11. 2026

**Automatické získávání F1 vysílání Nova Sport 5 funguje.** Nejde už o návrh:
skripty byly spuštěny a získaly skutečné pořady.

## Doporučení: oficiální Nova, Seznam jako záloha

`https://tv.nova.cz/program` obsahuje vložený JSON `PageData.program`:
dny → channels (`nova-sport-5`) → segments → items. Pole `title`, `start_at`,
`end_at`, `description` stačí pro požadovanou aplikaci. JSON se dekóduje,
JavaScript se nespouští; prohlížeč, přihlášení ani placené API nejsou potřeba.
Požadavek s výchozím/probe User-Agentem selhal HTTP 403 (`error code: 1010`),
s `User-Agent: Mozilla/5.0` opakovaně vrátil HTTP 200. TLS ověření zůstalo zapnuté.
Stránka měla přibližně 7,1 MB. Nesouvisející přihlašovací/player data se neukládají.

**Nova:** 369 pořadů stanice, z toho 76 F1 pořadů včetně historie a studií:
21 přímých přenosů a 55 záznamů. V popisech jsou explicitně „Přímý přenos“
a „Záznam“. V tomto vzorku žádný neznámý či rozporný stav.

**Seznam:** veřejné JSON rozhraní používané webem:

- `https://tv.seznam.cz/api` – index a globální dostupnost.
- `https://tv.seznam.cz/api/broadcast` – seznam stanic; Nova Sport 5 má ID 774.
- `https://tv.seznam.cz/api/schedule/774?day=2026-11-08` – denní program.

Pole `name`, `time_from`, `time_to`, `short_description` a boolean `live`.
Unixové časy se převádějí do Europe/Prague; ID stanice skript zjišťuje podle názvu.
Pro 6.–29. 11. získáno 38 F1 pořadů: 14 živých, 24 neživých s popisem záznamu.
**Všech 38 názvů, začátků a označení živého přenosu souhlasí s Novou.**
`live: false` samo o sobě není obecný důkaz reprízy, zde jej potvrzují popisy.

## Skutečně získané přímé přenosy

České časy (Europe/Prague), začátky TV vysílání, nikoli start sportovní části.

| Datum 2026 | Čas | Pořad |
|---|---|---|
| 6. 11. | 16:20 | São Paulo – 1. trénink |
| 6. 11. | 19:50 | São Paulo – 2. trénink |
| 7. 11. | 15:20 | São Paulo – 3. trénink |
| 7. 11. | 18:50 | São Paulo – kvalifikace |
| 8. 11. | 17:00 | São Paulo – úvodní studio |
| 8. 11. | 17:50 | São Paulo – závod |
| 8. 11. | 19:50 | São Paulo – závěrečné studio |
| 20. 11. | 01:25 | Las Vegas – 1. trénink |
| 20. 11. | 04:55 | Las Vegas – 2. trénink |
| 21. 11. | 01:25 | Las Vegas – 3. trénink |
| 21. 11. | 04:55 | Las Vegas – kvalifikace |
| 22. 11. | 04:00 | Las Vegas – úvodní studio |
| 22. 11. | 04:50 | Las Vegas – závod |
| 22. 11. | 06:50 | Las Vegas – závěrečné studio |

Příklad reprízy: 8. 11. v 10:15 kvalifikace São Paula = „Záznam“, `live: false`.
Závod v 17:50 = „Přímý přenos“, `live: true`. Studio se klasifikuje odděleně;
F1 Academy, F2, F3 ani magazíny se nezaměňují za hlavní šampionát.
Sprint ve vzorku nebyl: pravidla pro sprint a sprintovou kvalifikaci jsou
připravená, ale na skutečném sprintovém přenosu zatím neověřená.

## Kolik dní dopředu

Nova vrací 28 programových dní 26. 10.–22. 11. s nočním přesahem do
23. 11. 2026 05:45. Poslední začátek pořadu stanice je 23. 11. ve 02:15.
Od dne testu tedy přibližně **14 dní dopředu a následující noc**, včetně
celého víkendu Las Vegas. Je to pozorovaný rozsah, nikoli garantovaná lhůta.
Seznam vrací ještě pořady začínající v noci 23. 11.; pro 24.–29. 11. prázdné
programy. Jeho globální `schedule_availability` končí 23. 11. v 04:55;
není to specifická hranice Nova Sport 5 ani konec posledního pořadu.

## Veřejné EPG alternativy

XML Můj TV program skutečně vrátilo **171 pořadů** za programové dny
8.–22. 11. s nočními přesahy; 23.–29. 11. mělo prázdné seznamy.
URL: `https://services.mujtvprogram.cz/tvprogram2services/services/tvprogrammelist_mobile.php?channel_cid=1073&day=0`.
Pole `name`, `startDate`, `endDate` a popisy jsou strojově zpracovatelné.
ID 1073 a endpoint byly nalezeny v adaptéru
[iptv-org/epg](https://github.com/iptv-org/epg/tree/ae9cc64f9497c602ec2f6e17857ae38b3aa1ff05/sites/mujtvprogram.cz).
Jeho `days: 2` je výchozí nastavení stahovače, ne limit zdroje.
SMS vrátilo HTTP 200, ale extrakce aktuálních pořadů z HTML nebyla ověřena.
Samostatný průběžně publikovaný XMLTV feed zde ověřen nebyl.

## Reprodukce

Pouze Python 3.9+ a standardní knihovna:

```sh
cd /workspace/f1
python3 research/nova_times.py --output /tmp/nova-f1-times.json
python3 research/f1_times.py --start 2026-11-06 --days 24 --output /tmp/seznam-f1-times.json
python3 research/probe_epg.py --days 22 --output /tmp/xml-epg.json
```

První dva příkazy skutečně dokončeny s kódem 0; uložené výstupy:
`nova-result.json`, `seznam-result.json`. Úspěšný XML běh je zachycen v
`probe-result.json` (171 pořadů, kód 0); nahradil předchozí blokovaný výsledek.
Sonda Nova v tomto starším obecném XML skriptu stále používá probe User-Agent;
pro oficiální Novu slouží ověřený `nova_times.py`.

Pro aplikaci stačí automaticky jednou denně stáhnout Novu a uložit vybrané
pořady. Při selhání využít Seznam, případně ponechat poslední data s časem
aktualizace. Není potřeba ručně doplňovat termíny. Jde však o nezdokumentované
struktury webů: při jejich změně může být nutná oprava parseru. Vysílatel může
měnit časy. Podmínky dalšího zveřejňování dat tento technický test neověřoval.
Celá aplikace zatím vytvořena nebyla.
