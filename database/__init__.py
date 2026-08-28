# -*- coding: utf-8 -*-
"""
Pacote ``database`` -- persistência em SQLite através de **JDBC**.

O projeto não usa o módulo ``sqlite3`` do CPython. Toda a persistência passa
por ``java.sql``:

    Jython -> java.sql.DriverManager -> SQLite JDBC (Xerial) -> arquivo .db

    connection.py             -> conexão e execução de SQL
    schema.py                 -> DDL das cinco tabelas
    interaction_repository.py -> sessões, interações, mensagens, tools
    metrics_repository.py     -> agregações de tokens, cache e latência
"""
from __future__ import unicode_literals
