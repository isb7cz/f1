# F1 víkend

Jedna mobilní stránka s nejbližším zveřejněným víkendem Formule 1 a přímými
přenosy na Nova Sport 5. Časy jsou začátky televizního vysílání, nikoli starty
sportovních částí. Aplikace byla otestována na skutečném programu Novy.

## Jak ji otevřít

Potřebujete Python 3.9 nebo novější. Žádné balíčky, účty, API klíče ani databáze.

**Na Macu:** ve stažené složce projektu spusťte soubor `Spustit.command`.
Otevře Terminál, spustí server a otevře stránku v běžném prohlížeči. Terminál
nechte běžet; ukončení klávesami Ctrl+C zastaví aplikaci. Pokud macOS spuštění
staženého souboru nepovolí, použijte následující příkaz v Terminálu.

**Z Terminálu ve složce projektu:**

```sh
python3 app.py --open
```

Stránka běží na adrese `http://localhost:8000`. První načtení může několik
sekund trvat. Pokud Python chybí, nainstalujte ho z https://www.python.org/downloads/.
Na počítači nemusí být předinstalovaný.

**iPhone a iPad ve stejné domácí Wi-Fi:** na Macu spusťte
`python3 app.py --host 0.0.0.0`. V Safari telefonu či tabletu otevřete
`http://IP-ADRESA-MACU:8000`; IP adresu najdete v Nastavení systému → Wi-Fi →
Podrobnosti → TCP/IP. Je-li to potřeba, povolte Pythonu přístup v místním
firewallu. Mac musí zůstat zapnutý a server spuštěný. To je místní test,
nikoli veřejné nasazení; routeru nenastavujte přesměrování portů.

V cloudovém pracovním prostředí je server spuštěný na portu 8000. Pokud
rozhraní nabízí náhled portu, otevřete jej tam. Adresa `localhost` na vašem
Macu neodkazuje na cloudový počítač. Bez náhledu portu je pro otevření potřeba
projekt stáhnout a spustit lokálně podle postupu výše.

## Co se děje automaticky

- Server načte oficiální `https://tv.nova.cz/program` způsobem ověřeným
  v `research/`: `User-Agent: Mozilla/5.0`, JSON `PageData.program`, kanál
  `nova-sport-5`. Neprovádí JavaScript ze zdroje a nepoužívá žádné přihlašovací údaje.
- Kontrola Novy probíhá každých šest hodin, při výpadku znovu za 15 minut.
  Návštěvníci nevyvolávají další požadavky na Novu. Otevřená stránka kontroluje
  místní server jednou za minutu a po návratu na kartu.
- Poslední úspěšný výsledek se ukládá do ignorovaného `.cache/nova.json`.
  Po restartu se znovu použije; obnovení není závislé na otevřeném prohlížeči.
  Při výpadku zůstane k dispozici s viditelným upozorněním. Tento soubor není
  databáze a lze ho bezpečně smazat při vypnutém serveru.
- Přímý přenos musí mít explicitní označení v popisu. Záznamy, neznámé
  a rozporné stavy se nezobrazují; F1 Academy, F2 a F3 se nezaměňují s F1.
- Výběr víkendu vychází z aktuálního televizního programu, není pevně zadaný.
  Probíhající víkend zůstává do konce závodu. Poté aplikace přejde na další
  zveřejněný víkend. Při neúplném programu ukáže jen známé přenosy s upozorněním;
  při chybějícím programu ukáže zprávu a žádné odhadnuté časy ani název závodu.
- Zobrazují se tréninky, sprintová kvalifikace, sprint, kvalifikace, závod
  a přilehlé úvodní studio. Závěrečné studio a magazíny se nezobrazují.
- Každý přenos se přiřazuje podle skutečného začátku v `Europe/Prague`,
  nikoli podle programového dne Novy. Letní/zimní čas řeší časová databáze.

## Testy

```sh
python3 -m unittest discover -s tests -v
```

Devět testů: přechod na další GP, noční datum, letní/zimní čas včetně změny,
sprintový víkend, vyloučení repríz a Academy, chybějící program, výpadek,
zachování cache a HTTP odpovědi. Sprintový test používá simulovaná data;
v získaném skutečném programu sprint nebyl.

Volitelně pro vývoj, při spuštěném serveru:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/browser_smoke.py
```

Prohlížečové testy používají systémový Chromium, pokud je dostupný. Výsledky
a snímky jsou v ignorovaném `test-results/`. Kontrolují skutečné API, rozměry
iPhonu/iPadu/Macu, české časy i při americkém časovém pásmu zařízení, chybové
stavy a další víkend. Volitelně otestují WebKit, pokud je nainstalovaný.
Shrnutí provedených kontrol je v `TESTING.md`.

## Soubory a omezení

- `app.py`: získávání programu, automatické obnovování, výběr víkendu a server.
- `web/`: stránka, styly a jednoduchý JavaScript bez frameworku a sestavování.
- `tests/`: automatické testy; `research/`: zachované průzkumné skripty a data.

Veřejný web Novy nemá pro tuto strukturu zaručené API: změna může vyžadovat
opravu parseru. Při testu byl dostupný program přibližně 14 dní dopředu;
nejde o garanci. Aplikace nevymýšlí chybějící víkendy podle kalendáře F1.
Práva k programu ani podmínky jeho veřejného přebírání nebyly tímto testem
řešeny; před veřejným nasazením je zkontrolujeme. Zdroj je na stránce uveden.

Provoz je bez placených služeb. Veřejný hosting zatím není nastavený ani
provedený; bude potřebovat běžící Python proces (samotné GitHub Pages nestačí).
