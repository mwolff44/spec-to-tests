---
date: 2026-05-20
contexte: Exemples PBT/Hypothesis appliqués à un mini parser SIP et un dialog SIP stateful
but: démontrer concrètement que Hypothesis trouve des bugs subtils sur du code "qui marche"
---

# pbt-examples-sip

Deux exemples runnables qui illustrent ce que le PBT apporte sur ton terrain (VoIP/SIP) :

1. **`sip_message.py` + `test_sip_roundtrip.py`** — parser/formatter SIP simplifié.
   Round-trip property : `parse(format(msg)) == msg`. Bug inclus volontairement, à découvrir.

2. **`dialog.py` + `test_dialog_stateful.py`** — FSM dialog SIP (EARLY → CONFIRMED → TERMINATED) avec un `RuleBasedStateMachine`. Bug inclus volontairement, à découvrir.

Les bugs ne sont pas dissimulés méchamment : ce sont des erreurs typiques que l'humain ou l'IA produisent sans s'en apercevoir avec des tests example-based, et que Hypothesis trouve en < 30 secondes.

## Installation

```bash
cd /home/mwolff/MW/01_PERSONNEL/IA-chats/dev-ia-methods/pbt-examples-sip
python -m venv .venv
source .venv/bin/activate.fish   # ou .venv/bin/activate pour bash
pip install -r requirements.txt
```

## Lancer les tests

```bash
pytest -v
```

Sortie attendue (spoiler) : **les deux suites trouvent un échec et fournissent un contre-exemple minimal**.

Pour ne lancer que le round-trip :

```bash
pytest test_sip_roundtrip.py -v
```

Pour ne lancer que le stateful :

```bash
pytest test_dialog_stateful.py -v
```

## Voir ce que Hypothesis fait

```bash
pytest -v --hypothesis-show-statistics
```

Affiche : nombre d'exemples générés, taux d'acceptation, shrinking, exemples sauvés en base.

## Une fois les bugs trouvés

Pour réparer puis re-tester :

1. Lis le contre-exemple minimal que Hypothesis affiche.
2. Corrige `sip_message.py` ou `dialog.py` (le bug est commenté `# BUG:` dans le code).
3. Relance — les tests doivent passer.

Hypothesis sauvegarde les contre-exemples dans `.hypothesis/examples/` : les bugs trouvés seront re-testés en priorité au prochain run (régression-test automatique). À committer ou .gitignore selon ta préférence.

## Lien avec le reste du dossier

- Le deep-dive théorique : `../property-based-testing-hypothesis-deep-dive.md`
- Le skill TDD : `../tdd-skill/`
- Le survey outils : `../test-quality-tools-survey.md`
