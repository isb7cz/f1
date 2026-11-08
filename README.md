# F1 víkend

Jedna mobilní stránka s nejbližším zveřejněným víkendem F1 a živými přenosy
na Nova Sport 5. Časy jsou začátky televizního vysílání v Europe/Prague.

## Pro uživatele

Cílová stálá adresa GitHub Pages je **https://isb7cz.github.io/f1/**.
Samotné uvedení adresy v návodu není potvrzením dokončeného nasazení.
Stav je vidět v [Actions](https://github.com/isb7cz/f1/actions/workflows/pages.yml)
a v [Settings → Pages](https://github.com/isb7cz/f1/settings/pages).
Po prvním úspěšném nasazení stačí adresu otevřít v Safari na iPhonu, iPadu
nebo Macu. Nic se neinstaluje, Mac nemusí být zapnutý.

## Jednorázové nastavení GitHubu

Pro bezplatné Pages musí být tento repozitář veřejný (nebo by účet potřeboval
placený tarif pro soukromé Pages). Vlastník se zveřejněním výslovně souhlasil;
pokud změnu nepovolí připojená integrace, provede ji vlastník v rozhraní:

1. Settings → General → Danger Zone → Change repository visibility → Public.
   Zveřejní se soubory a historie repozitáře.
2. Settings → Pages → Build and deployment → Source → **GitHub Actions**.
3. Actions → **Update schedule and deploy Pages** → **Run workflow** → main →
   **Run workflow**. Pokud první automatický běh skončil před zapnutím Pages,
   stačí jej znovu spustit.
4. Počkejte na zelené dokončení kroku Deploy; odkaz je přímo u nasazení.

Pokud GitHub hlásí vypnuté Actions, na kartě Actions je nejprve povolte.
Pokud je odmítnut zápis aktualizovaných dat, ověřte Settings → Actions → General
→ Workflow permissions → Read and write permissions; pravidla chráněné větve
mohou zápis bota rovněž omezovat. Nepovolujte placené služby.

## Automatické aktualizace a další změny

Workflow `.github/workflows/pages.yml` běží po změně `main`, ručně a podle
plánu v **00:17, 06:17, 12:17 a 18:17 UTC**. GitHub může plánované úlohy
zpozdit; nejde o přesný časový SLA. Na otevřené stránce se data znovu kontrolují
každou minutu a při návratu na kartu.

1. Python na runneru načte oficiální Novu, stejně jako při průzkumu v `research/`.
2. Uloží pouze potvrzené živé F1 přenosy do `web/schedule.json` a zapíše data
   do `main`. Nepřevádí do veřejných souborů nesouvisející obsah stránky Novy.
3. Nahraje obsah `web/` do GitHub Pages. Veřejná aplikace je čistě statická:
   HTML, CSS, JavaScript a JSON, bez Python serveru, databáze a API klíčů.

Při výpadku Novy se zachovají poslední platná data včetně původního času ověření,
přidá se příznak neúspěšné aktualizace a stránka ukáže varování. Starší data
se označují také automaticky po 12 hodinách, i pokud Actions přestanou běžet.
Při selhání nasazení zůstává online předchozí úspěšná verze.
Pokud nikdy neexistovala platná data, neúspěšné načtení nevytvoří fiktivní program.

Výběr víkendu probíhá v prohlížeči podle aktuálního času, takže se po konci
závodu přepne bez čekání na další build. Noční vysílání patří pod skutečné
české datum, letní a zimní čas řeší Intl/Europe/Prague. Studio se od závodu
odlišuje, reprízy a F1 Academy se nezobrazují. Neúplný program je označen;
pokud další víkend není zveřejněný, stránka nevymýšlí jeho název ani časy.

Při budoucích změnách stačí změny z Codexu commitnout a odeslat nebo sloučit
na GitHub do `main`. Pouhé uložení souborů v pracovním prostředí GitHub nenasadí.
Po dokončení workflow zůstává veřejná adresa stejná.

## Místní vývoj (uživatel aplikace toto nepotřebuje)

Python 3.9+ a Node.js pro testy; produkční stránka nic z toho nevyžaduje:

```sh
python3 scripts/update_schedule.py
python3 -m unittest discover -s tests -v
node --test tests/schedule.test.cjs
python3 -m http.server 8001
```

Statický náhled je na `http://localhost:8001/web/`. Průzkumné soubory zůstávají
v `research/`. Původní `app.py` a `Spustit.command` stále umožňují lokální
serverovou variantu, nejsou ale součástí nasazení Pages.

Volitelné prohlížečové testy (vývojová závislost Playwright):
`python3 tests/browser_smoke.py`. Pro veřejnou stránku lze nastavit
`F1_TEST_URL=https://isb7cz.github.io/f1/`. Snímky vznikají v ignorovaném
`test-results/`; výsledky jsou popsány v `TESTING.md`.

## Omezení zdroje

Nova neposkytuje pro použitou strukturu garantované API. Její změna může
vyžadovat opravu parseru. Pozorovaný rozsah programu byl přibližně 14 dní
napřed, nikoli garantovaná lhůta. Novu kontaktuje jen GitHub runner čtyřikrát
denně a při nasazení změn; zařízení návštěvníků žádné požadavky na Novu neposílají.
Zdroj je uveden na stránce. Podmínky veřejného přebírání programu tímto
technickým řešením nejsou zaručeny.
