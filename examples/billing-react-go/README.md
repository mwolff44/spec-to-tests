---
date: 2026-05-21
contexte: Démo runnable du stack React + Go (Gin/GORM/Postgres) + Pact entre les deux
but: illustrer le workflow décrit dans test-stack-react-go-postgresql.md sur un cas concret
---

# test-stack-demo-billing

Mini-application "billing" qui démontre la pile de tests recommandée :

- **Backend Go** : un endpoint `POST /api/rate` qui calcule le coût d'un appel à partir d'un tarif stocké en base.
- **Frontend React** : un formulaire qui appelle l'endpoint et affiche le coût.
- **Contract testing** : Pact entre les deux, sans dépendance E2E.

## Le domaine

Calcul de prix d'un appel téléphonique :
- Input : durée (secondes) + numéro de destination (E.164).
- Lookup : on cherche en base le tarif dont le préfixe matche (le plus long, longest-prefix).
- Output : coût (durée arrondie à la minute supérieure × tarif).

Simpliste — mais suffisant pour montrer :
- Logique pure → unit tests + PBT.
- Persistance → testcontainers-go + Postgres réel.
- API HTTP → httptest + Gin.
- Frontend → Vitest + RTL + MSW.
- Contrat → Pact consumer (JS) + provider (Go).

## Structure

```
test-stack-demo-billing/
├── api/                          # backend Go
│   ├── pricing/                  # logique pure (unit + rapid PBT)
│   ├── repository/               # GORM + tariff (integration testcontainers)
│   ├── handlers/                 # Gin handlers (httptest)
│   ├── pacts/                    # Pact provider verification
│   └── migrations/               # SQL migrations (golang-migrate)
│
├── frontend/                     # React + Vite + TS
│   └── src/
│       ├── api/                  # client + Pact consumer test
│       ├── components/           # RateCalculator + Vitest+RTL test
│       └── test/                 # MSW handlers, setup
│
├── pacts/                        # contracts générés (artefact CI)
└── docker-compose.yml            # Postgres + API + Front pour E2E
```

## Pré-requis

- Go ≥ 1.22
- Node ≥ 20 + pnpm (ou npm)
- Docker (pour testcontainers + docker-compose)

## Lancement local (sans Docker)

### Backend

```fish
cd api
go mod tidy
# Lance Postgres séparément (ou docker run --rm -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:16)
export DATABASE_URL="postgres://test:test@localhost:5432/billing?sslmode=disable"
go run .
```

### Frontend

```fish
cd frontend
pnpm install
pnpm dev
```

Ouvrir http://localhost:5173.

## Lancer les tests

### Backend Go

```fish
cd api

# Unit (rapide, sans Docker)
go test -race ./pricing/...

# Handlers (rapide, sans Docker)
go test -race ./handlers/...

# Intégration DB (lent, requiert Docker)
go test -race -tags=integration ./repository/...

# Pact provider verification (lent, requiert Docker + pact-broker OU fichier pact local)
PACT_FILE=../pacts/react-frontend-go-api.json go test -race -tags=pact ./pacts/...

# Lint
golangci-lint run

# Mutation (lent, sur changed packages)
gremlins unleash ./pricing/...
```

### Frontend React

```fish
cd frontend

# Unit + composants
pnpm test:ci

# Pact consumer (génère le fichier pact dans ../pacts/)
pnpm test:pact

# Mutation (lent)
pnpm test:mutation

# Lint
pnpm lint
```

### Cross-stack (E2E)

```fish
docker compose up --build --wait
pnpm --dir frontend playwright test
docker compose down
```

## Workflow Pact

Le pattern bout-en-bout :

```
1. Le frontend écrit un consumer test qui décrit ce qu'il attend de l'API.
   → pnpm test:pact génère pacts/react-frontend-go-api.json.

2. Le fichier pact est publié sur un broker (Pactflow / self-hosted) — ou pour
   cette démo, partagé via le filesystem (../pacts/).

3. Le backend tourne ses tests de "provider verification" :
   il démarre l'API, configure les states (e.g. "tariff for prefix 33 exists"),
   et joue le pact contre lui.
   → Si le pact est rouge, le PR backend est bloqué.
```

## Bugs intentionnels (pour apprentissage)

Comme dans `pbt-examples-sip/`, un bug est laissé en place pour que les tests le démontrent :

- `api/pricing/pricing.go` — `RateCall` arrondit à la minute supérieure mais a un cas limite à 0 seconde. Le PBT le révèle.

Le bug est commenté `// BUG:` dans le code.

## Articulation avec les docs

- Méthode : `../test-stack-react-go-postgresql.md`
- PBT : `../property-based-testing-hypothesis-deep-dive.md`
- Outils déterministes : `../test-generation-from-spec.md`
- Skill TDD : `../tdd-skill/`

## Limites de cette démo

- Pas d'auth, pas de pagination, pas de gestion d'erreur sophistiquée — c'est volontaire.
- Le pact est généré localement et partagé via filesystem ; en prod, utiliser Pactflow ou un broker self-hosted.
- Le frontend est minimal (un formulaire) — pas de router ni de state management.
- Mutation testing CI non inclus (template dans `tdd-skill/hooks-*.md`).
