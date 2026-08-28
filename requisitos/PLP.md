# Usar o compilador Jython

**Disciplina:** Paradigmas de Linguagens de Programação  
**Período:** 2026.2  
**Professor:** Thiago Sales  
**Valor:** 2 pontos  
**Data de entrega:** Amanhã, 23:59

## Objetivo

Nesta atividade, você deverá explorar o **[trecho ausente no PDF]**, uma implementação da linguagem Python que executa sobre a **[trecho ausente no PDF]**, permitindo utilizar diretamente classes e bibliotecas Java dentro de programas escritos em Python.

O objetivo é observar, na prática, como diferentes linguagens podem interoperar quando compartilham uma mesma plataforma de execução.

## Atividade

Você deverá:

- **[trecho ausente no PDF]** em sua máquina.
- Criar **[trecho ausente no PDF]**, executados utilizando Jython, que façam uso de **[trecho ausente no PDF]**.

Os programas são de livre escolha, mas devem demonstrar de forma clara a integração entre Python e Java.

Alguns exemplos possíveis:

- manipulação de arquivos utilizando classes de `java.io`;
- utilização de estruturas de dados de `java.util`;
- manipulação de datas utilizando bibliotecas Java;
- criação de interfaces gráficas utilizando Java Swing;
- utilização de threads da JVM;
- comunicação de rede utilizando classes Java.

Pelo menos **[trecho ausente no PDF]**, de forma que fique evidente a interoperabilidade proporcionada pelo Jython.

Criar um **[trecho ausente no PDF]** contendo todo o código desenvolvido.

Criar um arquivo `README.md` contendo:

- uma breve descrição do Jython;
- descrição dos programas desenvolvidos;
- quais classes ou bibliotecas Java foram utilizadas;
- explicação de como Python e Java estão sendo integrados no exemplo;
- instruções para executar o projeto;
- instruções para executar o projeto utilizando **[trecho ausente no PDF]**.

Criar um `Dockerfile` que permita executar os exemplos sem que seja necessário instalar manualmente o Jython na máquina.

O projeto deverá poder ser executado, preferencialmente, com comandos semelhantes a:

```bash
docker build -t atividade-jython .
docker run --rm atividade-jython
```

Ao final da atividade, enviar o **[trecho ausente no PDF]**.

## Requisitos

O repositório deverá conter, no mínimo:

```text
atividade-jython/
├── README.md
├── Dockerfile
├── exemplo1.py
└── exemplo2.py
```

A organização pode ser diferente, desde que todos os arquivos necessários estejam presentes.

## Critérios de avaliação

Serão considerados:

- funcionamento correto dos programas;
- utilização efetiva de APIs/classes Java dentro do código Python;
- compreensão da interoperabilidade entre Python e Java;
- organização e clareza do código;
- qualidade da documentação no `README.md`;
- funcionamento da execução utilizando Docker;
- organização do repositório GitHub.

## Entrega

- Envie o link do repositório GitHub contendo a solução completa da atividade.
- Grave um vídeo explicando os detalhes do projeto que demonstre a integração Java com Python de no máximo 5 minutos usando a ferramenta Loom ou anexando o vídeo no README do projeto. No vídeo é obrigatório que seu rosto apareça em tempo real enquanto você fala.