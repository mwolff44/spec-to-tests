---
date: 2026-05-20
contexte: Fork étendu du skill TDD de Matt Pocock pour discipliner les agents IA
source-amont: https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd
licence-amont: voir repo mattpocock/skills
---

# tdd-skill (fork étendu)

Fork du skill TDD de Matt Pocock, étendu pour traiter explicitement les pathologies des agents IA en TDD documentées en 2024-2026 (Beck, Fowler, ThoughtWorks Radar v33, papers arxiv).

## Pourquoi ce fork

Le skill original est solide pour un humain discipliné mais sous-équipé contre les modes de défaillance spécifiques aux agents IA :

| Pathologie agent | Source | Traitée par l'original ? | Traitée ici ? |
|---|---|---|---|
| Horizontal slicing (tous les tests d'abord) | Beck 2025 | Oui (excellent) | Conservé |
| Over-mocking par défaut | arxiv 2602.00409 | Oui (mock at boundaries only) | Conservé |
| Test through interface only | GOOS, Pocock | Oui | Conservé |
| Suppression de tests pour passer | Beck 2025 (Pragmatic Engineer) | **Non** | `agent-discipline.md` |
| Test must fail first (gate) | Martin, Three Laws | Partiel | `agent-discipline.md` |
| Perpetually green / assertions vides | ThoughtWorks Radar v33 | Non | `refactoring.md` + `hooks.md` (mutation testing) |
| Répartition humain/IA explicite | Fowler 2025 | Non | `SKILL.md` (section Roles) |
| Spec exécutable amont | Fowler 2025 | Implicite | `SKILL.md` (section Spec-first) |
| Plan.md persistant | Beck 2025 (augmented coding) | Non | `plan-template.md` |
| Hooks / file perms / CI gates | ThoughtWorks v33 | Non | `hooks.md` |
| Commit discipline par cycle | Beck 2025 | Non | `SKILL.md` (workflow étendu) |
| Oracle problem | arxiv 2602.07900 | Non | `agent-discipline.md` |

## Fichiers

```
tdd-skill/
├── README.md             ← ce fichier
├── SKILL.md              ← entrée principale (étendue)
├── agent-discipline.md   ← NOUVEAU : règles dures anti-dérive
├── plan-template.md      ← NOUVEAU : artefact externe que l'agent suit
├── hooks.md              ← NOUVEAU : index des 6 mécanismes de garde-fous
├── hooks-python.md       ← NOUVEAU : scripts copy-paste pour pytest + mutmut
├── hooks-typescript.md   ← NOUVEAU : scripts copy-paste pour vitest/jest + Stryker
├── hooks-go.md           ← NOUVEAU : scripts copy-paste pour go test + gremlins
├── tests.md              ← good vs bad tests (de Pocock)
├── mocking.md            ← mock at boundaries only (de Pocock)
├── interface-design.md   ← DI, side-effect-free (de Pocock)
├── deep-modules.md       ← Ousterhout (de Pocock)
└── refactoring.md        ← étendu avec mutation testing
```

## Attribution

Sections "Philosophy", "Anti-Pattern: Horizontal Slices", "Tracer Bullet", `tests.md`, `mocking.md`, `interface-design.md`, `deep-modules.md`, base de `refactoring.md` : Matt Pocock, repo `mattpocock/skills`.

Ajouts : voir tableau ci-dessus.

## Comment utiliser

1. Comme **skill Claude Code** : déposer le dossier dans `~/.claude/skills/tdd-skill/`. L'agent invoque via mention TDD ou explicitement.
2. Comme **doctrine équipe** : lire SKILL.md + agent-discipline.md avant chaque session IA. Activer les hooks de `hooks.md` en CI.
3. Comme **référence personnelle** : à lire pour cadrer une session TDD avec Claude Code / Cursor / Aider.

## Limites assumées

- Les hooks de `hooks.md` sont des **templates**, à adapter au projet (Python/TS/Go/Rust).
- Le skill ne remplace pas la code review humaine sur la qualité des assertions.
- Mutation testing a un coût CI non-trivial — à activer sur les modules critiques en priorité.
