# Contributing

Merci de l'intérêt porté à ce dépôt.

## Avant d'ouvrir une pull request

1. **Ouvrir une issue** pour discuter de l'angle, sauf pour les corrections triviales (fautes, liens cassés, typos). Cela évite les efforts en parallèle.
2. **Lire la série d'articles** correspondante sur [blog-des-telecoms.com](https://blog-des-telecoms.com) pour comprendre le fil rouge et le ton.
3. **Respecter la doctrine du `tdd-skill/`** dans les exemples — notamment :
   - Pas de mocks sur du code interne.
   - Tests à travers l'interface publique uniquement.
   - Une property = un fichier, pas de propriétés combinées.

## Style

- Code Python : `ruff` propre, `pytest` qui passe.
- Code TypeScript : `eslint` propre (config dans `examples/billing-react-go/frontend/`), `vitest` qui passe.
- Code Go : `golangci-lint run` propre, `go test -race ./...` qui passe.
- Documentation Markdown : un titre H1 par fichier, sections H2, frontmatter facultatif.

## Types de contributions appréciées

- **Portage stack** : adapter les démos à Vue, Svelte, FastAPI, Spring Boot, Rust + Axum, etc.
- **Nouveaux patterns PBT** : invariants ou métamorphique non couverts dans les exemples.
- **Retours d'expérience** : retour d'application du workflow en production, sous forme de fichier `case-studies/<sujet>.md`.
- **Corrections de bugs** dans les exemples (en dehors des bugs **intentionnels** signalés `# BUG:` dans le code).

## Ce qui ne sera pas accepté

- PR qui transforment les démos en frameworks abstraits — la valeur pédagogique vient du fait qu'elles soient courtes et explicites.
- Ajout de dépendances lourdes (frameworks complets) pour les exemples.
- Reformulations stylistiques sans amélioration substantielle.

## Licence des contributions

En soumettant une PR, vous acceptez que votre contribution soit publiée sous la même licence MIT que le dépôt.
