# spec-to-tests

> Matériel runnable accompagnant la série d'articles
> **["De la spécification à l'exécution — un workflow pour fiabiliser le code à l'ère IA"](https://www.blog-des-telecoms.com/blog/ia-tests-indispensables-workflow/)**
> sur [blog-des-telecoms.com](https://blog-des-telecoms.com/).

L'idée centrale de la série : à l'ère des agents IA capables de générer du code en quelques secondes, la qualité ne se joue plus sur l'écriture du code, mais sur la **spécification** en amont et sur les **tests** qui guident l'agent. Ce dépôt rassemble les démos, *skills* et exemples concrets pour mettre en pratique ce workflow.

## Contenu

```
spec-to-tests/
├── tdd-skill/                    Skill TDD étendu pour Claude Code,
│                                 hardened pour discipliner les agents IA.
│                                 Fork du skill de Matt Pocock.
│
├── examples/
│   ├── pbt-sip/                  Property-based testing avec Hypothesis
│   │                             sur un parseur SIP et un dialog FSM SIP.
│   │                             Démontre stateful PBT en contexte télécom.
│   │
│   └── billing-react-go/         Démo full-stack — React + Go (Gin/GORM/PostgreSQL)
│                                 avec Vitest+RTL+MSW, testcontainers-go,
│                                 et contract testing Pact (consumer/provider).
│
└── docs/
    └── workflow-overview.md      Vue d'ensemble du workflow,
                                  référencée depuis les articles du blog.
```

## Articles de la série

| # | Titre | Lien |
|---|---|---|
| 1 | L'IA n'a pas tué les tests, elle les rend indispensables | [Article 1](https://www.blog-des-telecoms.com/blog/ia-tests-indispensables-workflow/) |
| 2 | La spécification exécutable : ce que vous donnez à lire à l'humain et à l'IA | [Article 2](https://www.blog-des-telecoms.com/blog/specification-executable-gherkin-proprietes/) |
| 3 | Qui écrit le test, qui écrit le code ? La répartition humain / IA / outils | [à venir] |
| 4 | Mesurer si les tests valent quelque chose : les 4 axes | [à venir] |
| 5 | Property-based testing : la défense contre les oracles faibles | [à venir] |
| 6 | Mise en pratique : React + Go (Gin / GORM / PostgreSQL) | [à venir] |
| 7 | Lancer l'exécution : du plan aux PR | [à venir] |

## Démarrage rapide

### 1. Property-based testing sur SIP (Python)

```bash
cd examples/pbt-sip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v --hypothesis-show-statistics
```

Deux suites :
- `test_sip_roundtrip.py` — round-trip property sur un parseur SIP.
- `test_dialog_stateful.py` — `RuleBasedStateMachine` sur un dialog FSM SIP.

Les deux contiennent un bug intentionnel que Hypothesis découvre en quelques millisecondes. Voir le README du dossier pour les détails et l'exercice de correction.

### 2. Billing React + Go avec Pact (full-stack)

```bash
cd examples/billing-react-go
# Backend
cd api && go mod tidy && go test -race ./pricing/... ./handlers/...
cd ../frontend && pnpm install && pnpm test
# Contract testing
pnpm test:pact                       # consumer (génère le pact)
cd ../api && go test -tags=pact ./pacts/...   # provider (vérifie le pact)
# E2E complet via Docker
cd .. && docker compose up --build
```

### 3. Utiliser le skill TDD avec Claude Code

```bash
cp -r tdd-skill ~/.claude/skills/
# Dans Claude Code, invoquer via mention TDD ou explicitement.
```

Le skill apporte :
- Une discipline `agent-discipline.md` en 10 règles dures.
- Un artefact `plan.md` que l'agent suit.
- Des templates de *hooks* (pre-commit, RED-must-fail-first, mutation testing CI).

## Attribution

Le dossier `tdd-skill/` est un **fork étendu** du *skill* TDD de Matt Pocock — [`mattpocock/skills`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd). Les ajouts (discipline agent, plan persistant, *hooks* par langage, mutation testing CI) sont documentés dans `tdd-skill/README.md`. Tous les apports originaux de Pocock sont conservés et clairement crédités.

Les démos `pbt-sip/` et `billing-react-go/` sont originales.

## Licence

[MIT](LICENSE) — utilisation, modification et redistribution libres, y compris commerciales. Attribution appréciée.

## Comment contribuer

Issues et pull requests bienvenues. Quelques angles ouverts :

- Portage des démos sur d'autres stacks (Vue, Svelte, FastAPI, Spring Boot…).
- Adaptation du `tdd-skill/` à d'autres environnements agent (Cursor, Aider, OpenCode).
- Cas d'usage métier supplémentaires pour le PBT stateful (FSM dialplan, état RTP, etc.).
- Retours d'expérience sur l'application du workflow en production.

Avant toute PR conséquente, ouvrez une issue pour discuter de l'angle.

## Auteur

**Mathias Wolff** — architecte télécom chez [Wazo](https://wazo.io), animateur du [blog des télécoms](https://blog-des-telecoms.com).
[LinkedIn](https://www.linkedin.com/in/mathias-wolff-47a7941/) · [Celea Consulting](https://celea.org)

## Aller plus loin

- [Kent Beck — *Augmented Coding: Beyond the Vibes* (2025)](https://signals.aktagon.com/articles/2025/09/augmented-coding-beyond-the-vibes/)
- [Martin Fowler — *Exploring Gen AI: Spec-Driven Development* (2025)](https://martinfowler.com/tags/testing.html)
- [ThoughtWorks Technology Radar v33 (2025)](https://www.thoughtworks.com/radar)
- [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- [Pact contract testing](https://docs.pact.io/)
