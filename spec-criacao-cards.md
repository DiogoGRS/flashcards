# spec-criacao-cards

Documento de referência para o Claude quando o usuário pedir para gerar/seedar cards. Mantém o processo previsível e a qualidade dos cards consistente.

## Campos do card

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `topics` | `list[str]` | sim | Hierarquia ordenada do mais geral pro mais específico, ex: `["frontend", "vue", "watch"]`. Sempre minúsculo, sem acento, sem espaço (use `-`). Mínimo 1 nível. |
| `question` | `str` | sim | Pergunta direta, em português. Sem "qual das alternativas..."; prefira perguntas que testem entendimento real. |
| `options` | `list[str]` | sim | Mínimo 2, ideal 3–4. Distratores plausíveis (não óbvios). Sem "todas as anteriores". |
| `correct_answer` | `int` | sim | Índice (0-based) da opção correta em `options`. |
| `explanation` | `str` \| null | recomendado | Explica POR QUE a correta é correta e, quando útil, por que as outras erram. Cite o termo/API exato da doc. 1–4 frases. Suporta markdown (veja abaixo). |
| `difficulty` | `"easy"\|"medium"\|"hard"` \| null | não | Definido pelo usuário no momento da revisão, não na criação. Deixe `null`. |

### Markdown e syntax highlighting

Os campos `question`, `options` e `explanation` suportam markdown renderizado com syntax highlight. Use sempre que o conteúdo envolver código:

- **Inline code**: `` `flush: 'pre'` ``, `` `watchEffect` ``, `` `SELECT * FROM` ``
- **Code blocks na explanation** (indicar a linguagem):
  ````
  ```python
  @cache
  def fib(n): ...
  ```
  ````
- Linguagens suportadas: `python`, `javascript`, `typescript`, `sql`, `bash`, `json`, `html`, `css`, entre outras (qualquer linguagem do highlight.js).
- Em `question` e `options`, prefira inline code (`` ` `` ) — code blocks são mais adequados na `explanation`.
- **Não usar markdown** para conteúdo puramente textual (não forçar `**bold**` desnecessariamente).

Regras de qualidade:

- **Foco único**: um card cobre um conceito atômico. Se a explicação tiver "e também...", quebre em dois cards.
- **Sem ambiguidade**: a alternativa correta deve ser inequivocamente correta com base na fonte.
- **Distratores realistas**: erros plausíveis que alguém aprendendo de fato cometeria. Evite distratores absurdos.
- **Sem "pegadinha de português"**: o erro deve ser conceitual, não de leitura.
- **Linguagem da doc**: use os termos exatos da documentação fonte (ex: `flush: 'pre'`, não "antes de renderizar").
- **Tópicos consistentes**: se já existem cards com `["frontend","vue","watch"]`, novos cards do mesmo escopo devem usar exatamente o mesmo path. Antes de criar, consulte `GET /api/topics` pra reaproveitar.

## Processo de criação (input do usuário → cards)

Input mínimo do usuário:

```
tema: <tópico hierárquico>
doc: <URL da documentação primária>
[doc-extra: <URL adicional se necessário>]
[quantidade: N]   # default 8
[nivel: iniciante|intermediario|avancado]  # default intermediario
```

Passos que o Claude deve seguir:

1. **Buscar a doc primária** com `WebFetch` na URL informada. Extrair conceitos, APIs, exemplos e *gotchas*.
2. **Se necessário, buscar docs extras** (limites, pegadinhas, comparações com versões antigas). Só usar fontes oficiais ou referências bem estabelecidas.
3. **Listar conceitos atômicos** que valem virar card (1 conceito = 1 card).
4. **Gerar os cards** seguindo as regras de qualidade. Para cada card:
   - `topics` derivado do tema (quebrar nos níveis naturais).
   - `question` específica e direta.
   - `options` com 1 correta + distratores tirados de erros comuns / APIs próximas.
   - `explanation` curta justificando, com termos da doc.
5. **Mostrar a lista** ao usuário pra revisar antes de seedar.
6. **Seedar via API** (não escrever no SQLite direto).

## Atualizar o snapshot

Após cada seed bem-sucedido, atualizar `seeds/snapshot.json` e commitar:

```bash
curl -s http://localhost:8000/api/export > seeds/snapshot.json
git add seeds/snapshot.json && git commit -m "snapshot: adiciona cards de <tema>"
```

Esse arquivo é o seed automático do banco em deploys novos — manter sempre atualizado.

## Como seedar

Servidor rodando em `http://localhost:8000` (ou URL do Coolify). Para cada card, `POST /api/cards`:

```bash
curl -s -X POST http://localhost:8000/api/cards \
  -H "Content-Type: application/json" \
  -d '{
    "topics": ["frontend","vue","watch"],
    "question": "...",
    "options": ["a","b","c","d"],
    "correct_answer": 2,
    "explanation": "..."
  }'
```

Para seed em lote, o Claude deve gerar um script bash/python ou um único loop com vários POSTs. Não usar `INSERT` SQL direto — sempre via API pra respeitar validações.

## Exemplo (referência)

```json
{
  "topics": ["frontend", "vue", "watch"],
  "question": "Qual é o flush PADRÃO do watch() e quando o callback dispara?",
  "options": [
    "'sync' — síncrono, na hora da mutação",
    "'post' — após o DOM ser atualizado",
    "'pre' — após updates do componente pai, ANTES do DOM do componente dono ser atualizado",
    "Não tem padrão, é obrigatório passar"
  ],
  "correct_answer": 2,
  "explanation": "O default é 'pre'. Por isso, se você ler o DOM do próprio componente dentro do callback, ele estará em estado pré-atualização. Os callbacks também são batched (agrupados) para evitar disparos duplicados."
}
```
