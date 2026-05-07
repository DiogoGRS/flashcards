# flashCards

Base pessoal de flashcards com revisão espaçada simples. Monorepo com FastAPI + SQLite no backend e HTML/Alpine.js no frontend (sem build step).

## Estrutura

```
flashCards/
├── apps/
│   ├── api/        # FastAPI + SQLModel + SQLite
│   └── web/        # index.html + app.js (Alpine.js + Tailwind via CDN)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Modelo de card

- `topics`: lista ordenada (ex: `["frontend", "vue", "watch"]`) — define a hierarquia
- `question`: pergunta
- `options`: lista de strings
- `correct_answer`: índice da opção correta
- `difficulty`: `easy` | `medium` | `hard` (definido pelo usuário ao revisar)
- `next_review`: próxima revisão (calculada com base na dificuldade)
- `last_reviewed`, `created_at`

Intervalos: easy = +7d, medium = +3d, hard = +1d. Errou = +4h.

## Rodar local

```bash
pip install -r requirements.txt
uvicorn apps.api.main:app --reload
```

Abra http://localhost:8000.

## Rodar com Docker

```bash
docker compose up --build
```

Dados persistem em volume nomeado `flashcards_data`.

## Deploy no Coolify

1. Aponte para este repo.
2. Build pack: **Dockerfile** (raiz do projeto).
3. Porta: `8000`.
4. Adicione um volume persistente em `/app/data`.
5. Deploy.

Variável opcional:
- `DATABASE_URL` (default `sqlite:////app/data/flashcards.db`).

## API

- `GET  /api/cards?topic_path=frontend/vue` — listar
- `GET  /api/cards/due?topic_path=...` — pendentes
- `POST /api/cards` — criar
- `PUT  /api/cards/{id}` — editar
- `DELETE /api/cards/{id}` — excluir
- `POST /api/cards/{id}/review` — body `{difficulty, correct}`
- `GET  /api/topics` — árvore de tópicos com contagem
- `GET  /healthz`

Docs interativas: `/docs`.
