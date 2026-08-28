# Caelum Stella Core

O agente integra `br.com.caelum.stella:caelum-stella-core:2.2.2` diretamente
no classpath do Jython. A LLM vê somente seis ferramentas: validação,
transformação, geração, número por extenso, capabilities e validação em lote.

Os documentos disponíveis são CPF, CNPJ, NIT, RENAVAM, título eleitoral e
inscrição estadual. Para inscrição estadual é obrigatório informar a UF.
O catálogo `stella/catalog.py` é uma whitelist: entradas da LLM nunca são
convertidas em nomes de classes Java ou avaliadas dinamicamente.

Documentos pessoais e fiscais são dados sensíveis. As ferramentas Stella
redigem `value`, `values`, `normalized`, `formatted`, `input` e `output` na
auditoria SQLite. A resposta enviada à LLM permanece completa apenas em
memória para que ela possa responder à solicitação atual.

Para evitar que um documento seja enviado à Groq, use o modo privado no
terminal: `/stella validar cpf 529.982.247-25`, `/stella validar-ie SP
110.042.490.114`, `/stella formatar cpf 52998224725` ou `/stella catalog`.
Esses comandos chamam `StellaService` diretamente e não criam chamada LLM.
