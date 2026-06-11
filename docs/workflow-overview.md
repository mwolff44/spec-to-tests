# Workflow overview — de la spécification à l'exécution

Vue d'ensemble du workflow proposé dans la série d'articles. Ce document sert de référence pour le lecteur qui souhaite avoir la carte complète sous les yeux.

## Le workflow en cinq étapes

```
┌──────────────────────────────────────────────────────────────┐
│ 1. SPÉCIFICATION                                             │
│    Humain formalise l'intention :                            │
│      • User story → Gherkin                                  │
│      • Exemples typés (table-driven, fixtures)               │
│      • Propriétés candidates (invariants, round-trip)        │
│      • Contracts / types (icontract, Zod, OpenAPI)           │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. TESTS                                                     │
│    Humain écrit (ou valide strictement) les tests AVANT      │
│    toute écriture de code de production.                     │
│    Outils déterministes utiles ici :                         │
│      • Hypothesis ghostwriter (squelettes PBT)               │
│      • Pynguin / EvoSuite (tests structurels)                │
│      • GraphWalker / ModelJUnit (model-based)                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. EXÉCUTION IA                                              │
│    L'agent implémente sous la contrainte des tests :         │
│      • Un cycle = un test = un commit                        │
│      • plan.md persistant que l'agent suit                   │
│      • Règles dures de tdd-skill/agent-discipline.md         │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. VÉRIFICATION                                              │
│    Multi-agent (writer + critic) + outils déterministes :    │
│      • Critic-agent applique la discipline TDD               │
│      • Mutation testing scoped aux changes                   │
│      • Coverage gate (line + branch)                         │
│      • Lint + smells detector                                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. AUDIT                                                     │
│    Bouclage régulier (mensuel ou trimestriel) :              │
│      • Niveau 1 statique cheap (15 min)                      │
│      • Niveau 2 dynamique (heure)                            │
│      • Niveau 3 IA-assisté (jour)                            │
└──────────────────────────────────────────────────────────────┘
```

## Mapping articles → étapes

| Article | Étape principale couverte |
|---|---|
| 1 — *L'IA n'a pas tué les tests* | Contexte général, pourquoi le workflow |
| 2 — *La spécification exécutable* | Étape 1 |
| 3 — *Qui écrit le test, qui écrit le code ?* | Étapes 2 et 3, répartition des rôles |
| 4 — *Mesurer si les tests valent quelque chose* | Étape 4 (vérification de la qualité) |
| 5 — *Property-based testing* | Outil-clé des étapes 2 et 4 |
| 6 — *Mise en pratique React + Go* | Application du workflow à un stack moderne |
| 7 — *Lancer l'exécution : du plan aux PR* | Étape 3 opérationnelle + étape 5 (audit) |

## Outils référencés dans la série

### Tests, frameworks et runners
- **Python** : pytest, [Hypothesis](https://hypothesis.readthedocs.io/), [mutmut](https://github.com/boxed/mutmut), [ruff](https://docs.astral.sh/ruff/)
- **TypeScript / React** : [Vitest](https://vitest.dev/), [React Testing Library](https://testing-library.com/), [MSW](https://mswjs.io/), [fast-check](https://fast-check.dev/), [StrykerJS](https://stryker-mutator.io/)
- **Go** : `testing` + [testify](https://github.com/stretchr/testify), [testcontainers-go](https://golang.testcontainers.org/), [rapid](https://github.com/flyingmutant/rapid), [gremlins](https://github.com/go-gremlins/gremlins), [golangci-lint](https://golangci-lint.run/)
- **Cross-stack** : [Pact](https://docs.pact.io/), [Playwright](https://playwright.dev/)

### Outils déterministes de génération de tests
- [Hypothesis ghostwriter](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html) — Python
- [Pynguin](https://pynguin.readthedocs.io/) — Python
- [EvoSuite](https://www.evosuite.org/) — Java
- [GraphWalker](https://graphwalker.github.io/) — Multi-langage (model-based testing)
- [KLEE](https://klee-se.org/) — C/C++ (symbolic execution)

### Recherche académique citée
- *Augmented Coding* — Kent Beck (2025)
- *Spec-Driven Development* — Martin Fowler (2025)
- *Are Coding Agents Generating Over-Mocked Tests?* — arxiv 2602.00409 (2025)
- *Acceptance Test Generation with LLMs* — arxiv 2504.07244 (2025)
- *Agentic Property-Based Testing* — arxiv 2510.09907 (2025)
- *Multi-Agent Verification* — arxiv 2502.20379 (2025)

## Où trouver quoi dans ce dépôt

```
spec-to-tests/
│
├── tdd-skill/                              ← étapes 3-4
│   Règles dures pour discipliner l'agent IA :
│   agent-discipline.md, plan-template.md, hooks-*.md
│
├── examples/pbt-sip/                       ← étapes 2 (article 5)
│   Démo Hypothesis sur un parseur SIP et un dialog FSM.
│   Inclut des bugs intentionnels que le PBT trouve.
│
├── examples/billing-react-go/              ← étape 6 (article 6)
│   Mini-application React + Go avec testcontainers,
│   MSW et Pact. Le stack complet du workflow.
│
└── docs/workflow-overview.md               ← ce document
```
