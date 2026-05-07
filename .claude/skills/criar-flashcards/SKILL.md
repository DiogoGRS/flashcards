---
name: criar-flashcards
description: Use ao criar/gerar/seedar flashcards do projeto flashCards a partir de uma fonte de documentação. Dispara em pedidos como "criar flashcards sobre X", "gere N cards de Y", "seedar perguntas sobre Z (link)". Fluxo: usuário informa tema + URL de doc, skill busca a doc com WebFetch, gera cards seguindo as regras de qualidade do projeto, revisa com o usuário, e seeda em lote via API. Não use para revisar cards existentes ou alterar a UI — só para criação.
---

# criar-flashcards

Skill para gerar flashcards do projeto flashCards a partir de documentação. As regras canônicas dos campos vivem em `spec-criacao-cards.md` na raiz do projeto — leia esse arquivo antes de gerar.

## Quando ativar

Ativar quando o usuário pedir explicitamente para criar/gerar/seedar cards e fornecer (ou puder fornecer) um tema + fonte. Exemplos:

- "cria 10 flashcards sobre Vue computed: https://vuejs.org/api/reactivity-core.html#computed"
- "gera cards de Postgres window functions a partir de <link>"
- "seedar perguntas avançadas sobre Tailwind config"

**Não ativar** para: dúvidas conceituais, edição de UI, revisão de cards existentes, debug.

## Input esperado do usuário

Mínimo:
- `tema`: tópico hierárquico (ex: `frontend/vue/computed`)
- `doc`: URL da documentação primária

Opcional:
- `doc-extra`: URLs adicionais (ex: changelog, RFC, post complementar)
- `quantidade`: N cards (default `8`)
- `nivel`: `iniciante` | `intermediario` | `avancado` (default `intermediario`)

Se o usuário só passar o tema sem URL, peça a fonte antes de continuar — não invente conteúdo.

## Passos

1. **Carregar o spec.** `Read` em `spec-criacao-cards.md` para garantir que os campos e regras de qualidade estão frescos.
2. **Confirmar API de pé.** `curl -s http://localhost:8000/healthz` — se 404/conn refused, avisar o usuário e parar (ou subir o servidor se ele autorizar).
3. **Listar tópicos existentes.** `curl -s http://localhost:8000/api/topics` — se já existir um path compatível com o tema, **reutilizar exatamente** (não criar `["frontend","vue"]` se já existe `["front-end","vue"]`).
4. **Buscar a doc primária** com `WebFetch` na URL. Extrair conceitos atômicos, APIs, defaults, *gotchas*, exemplos.
5. **Buscar docs extras** se fornecidas, ou se a doc primária deixar lacunas (ex: comportamento entre versões).
6. **Gerar os cards** como uma lista JSON em memória, seguindo `spec-criacao-cards.md`:
   - 1 conceito atômico por card
   - 3–4 opções com distratores plausíveis
   - `correct_answer` como índice 0-based
   - `explanation` curta (1–4 frases) usando termos exatos da doc
   - `difficulty` sempre `null` (o usuário define no review)
7. **Mostrar pré-visualização** ao usuário (lista numerada com pergunta + correta destacada). Pedir aprovação ou ajustes antes de seedar.
8. **Seedar via helper.** Salvar a lista aprovada em `/tmp/flashcards-seed-<tema>.json` e rodar:
   ```bash
   python3 .claude/skills/criar-flashcards/seed.py /tmp/flashcards-seed-<tema>.json
   ```
   O script faz POST por card e reporta sucesso/falha.
9. **Confirmar** ao usuário quantos foram seedados e mostrar o filtro de tópico (`http://localhost:8000/?topic=<tema>`).

## Regras importantes

- **Sempre via API**, nunca `INSERT` direto no SQLite.
- **Nunca** misturar fontes não oficiais sem avisar.
- **Citações fiéis**: a explicação deve refletir o que a doc realmente diz, não interpretação livre.
- **Falhou um POST?** Não abortar o lote — continuar e reportar quais falharam no fim.
- **Tópicos**: minúsculo, sem acento, espaços viram `-`. Profundidade típica: 2–4 níveis.

## Saída final esperada

- Cards no banco (visíveis em `/api/cards?topic_path=<tema>`)
- Resumo curto pro usuário: `N/M cards seedados em <tópico>`
