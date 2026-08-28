# Ferramentas do agente

## Registro e segurança

O arquivo `tools/registry.py` mantém a lista branca de tools expostas ao
modelo. Cada tool declara nome, descrição, schema de parâmetros e handler
Python. O registro valida campos obrigatórios, tipos, enums, limites de
números, strings, arrays e objetos antes da execução. Um nome fora da lista
branca resulta em erro controlado.

As 12 tools públicas são divididas entre ferramentas do projeto e gateway
Caelum Stella. A Stella não recebe nomes de classes Java da LLM: o catálogo
interno resolve somente capabilities previamente permitidas.

## Tools do projeto

### `search_project_knowledge`

Pesquisa a documentação local em `knowledge/`. Use para perguntas sobre
arquitetura, Jython, Java, Groq, Docker, banco, configuração ou funcionamento
interno.

Pergunta exemplo: `Como este projeto usa Jython?`

### `list_project_tests`

Lista os testes automatizados. Aceita `only` com `offline`, `integration` ou
`all`, e `detail` para incluir descrição e tags.

Pergunta exemplo: `Quais testes automatizados existem?`

### `run_project_tests`

Executa a suíte offline por padrão. `target` aceita `all`, identificadores
como `T08,T09` ou uma palavra-chave como `fuzzy`, `banco` ou `stella`.

Pergunta exemplo: `Rode os testes da Stella.`

### `search_chat_history`

Pesquisa fuzzy no histórico de conversas persistido em SQLite.

Pergunta exemplo: `Eu já perguntei sobre Docker antes?`

### `get_recent_interactions`

Retorna as interações recentes, em vez de pesquisar por um termo específico.

Pergunta exemplo: `Sobre o que conversamos recentemente?`

### `get_usage_metrics`

Consulta métricas de tokens, cache, latência e uso de tools. `scope` aceita
`session`, `all` e `last_n`.

Pergunta exemplo: `Quantos tokens usamos nesta sessão?`

## Gateway Caelum Stella

As ferramentas abaixo chamam a biblioteca Java `caelum-stella-core` na mesma
JVM do Jython. Os documentos iniciais são `cpf`, `cnpj`, `nit`, `renavam`,
`titulo_eleitoral` e `inscricao_estadual`. Para inscrição estadual, `uf` é
obrigatória e aceita as siglas brasileiras.

Os valores documentais são sensíveis: campos como `value`, `values`,
`normalized`, `formatted`, `input` e `output` são redigidos antes de serem
persistidos em `tool_executions`.

### `stella_validate_document`

Valida um único documento. Parâmetros: `document_type`, `value`, `uf`
(necessária para IE), `formatted` e `details`.

Perguntas exemplo:

- `O CPF 529.982.247-25 é válido?`
- `Confira se o CNPJ 04.252.011/0001-10 é válido.`
- `Essa inscrição estadual 110.042.490.114 de SP é válida?`

### `stella_transform_document`

Formata ou remove a máscara de um documento. Parâmetros: `document_type`,
`action` (`format` ou `unformat`) e `value`.

Perguntas exemplo:

- `Formate o CPF 52998224725.`
- `Remova a máscara do CNPJ 04.252.011/0001-10.`

### `stella_generate_document`

Gera um documento válido somente quando a capability existe no Stella. Para a
primeira fase, é disponível para CPF, CNPJ, NIT, RENAVAM e título eleitoral;
não é oferecida para inscrição estadual. Parâmetros: `document_type` e
`formatted`.

Pergunta exemplo: `Gere um CPF válido formatado para um teste.`

### `stella_number_to_words`

Converte um número para palavras por meio de `NumericToWordsConverter` da
Stella. Recebe o parâmetro numérico `value`.

Pergunta exemplo: `Escreva 123 por extenso.`

### `stella_capabilities`

Lista de modo compacto as capabilities disponíveis. `category` pode ser
`all`, `validation`, `transform` ou `generation`.

Pergunta exemplo: `Quais documentos a Stella consegue gerar?`

### `stella_validate_batch`

Valida um lote de documentos do mesmo tipo. Recebe `document_type`, `values`,
`uf`, `formatted` e `details`. O limite padrão é 100 itens, configurável por
`STELLA_BATCH_MAX_ITEMS`; `details` é `false` por padrão para reduzir o tamanho
da resposta.

Pergunta exemplo: `Valide em lote estes CPFs: 52998224725, 11111111111.`

## Modo privado no terminal

Perguntas normais passam primeiro pela Groq, portanto um documento digitado na
conversa pode ser enviado ao modelo antes do tool calling. Para executar a
Stella sem qualquer chamada LLM, use `/stella`:

```text
/stella validar cpf 529.982.247-25
/stella validar-ie SP 110.042.490.114
/stella formatar cnpj 04252011000110
/stella gerar cpf
/stella extenso 123
/stella catalog generation
```

## Roteamento obrigatório na conversa

Nas perguntas inequívocas de validação, formatação, geração, número por
extenso, capabilities ou lote, o orquestrador força a tool Stella na primeira
rodada da Groq. Por isso o terminal exibe, por exemplo,
`[executando tool de validação Stella... 12 ms]` antes da resposta final.
Depois da execução, uma segunda rodada livre da LLM explica o resultado ao
usuário.
