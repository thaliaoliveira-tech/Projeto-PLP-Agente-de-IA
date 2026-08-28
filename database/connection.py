# -*- coding: utf-8 -*-
"""
database/connection.py -- conexão SQLite via JDBC.

Este módulo é outro ponto forte de interoperabilidade do projeto: em vez do
módulo ``sqlite3`` do CPython, usamos a API padrão de banco de dados da
plataforma Java.

    from java.sql import DriverManager
    connection = DriverManager.getConnection("jdbc:sqlite:/app/data/base.db")

APIs Java utilizadas neste módulo:

    java.sql.DriverManager     -> abre a conexão JDBC
    java.sql.Connection        -> transação e statements
    java.sql.PreparedStatement -> SQL parametrizado (sem concatenar strings)
    java.sql.ResultSet         -> leitura dos resultados
    java.sql.Types             -> tipagem de parâmetros nulos
    java.sql.SQLException      -> erros de banco
    java.lang.Class            -> carga explícita do driver org.sqlite.JDBC
    java.io.File               -> criação do diretório do banco
"""
from __future__ import unicode_literals

# ---------------------------------------------------------------------------
# Classes Java do subsistema de banco de dados.
# ---------------------------------------------------------------------------
from java.sql import DriverManager
from java.sql import Types
from java.sql import SQLException
from java.lang import Class as JavaClass
from java.lang import ClassNotFoundException
from java.io import File

from database import schema


JDBC_DRIVER = "org.sqlite.JDBC"
JDBC_PREFIX = "jdbc:sqlite:"


class DatabaseError(Exception):
    """Erro de banco de dados com mensagem amigável."""

    def __init__(self, message, cause=None):
        Exception.__init__(self, message)
        self.message = message
        self.cause = cause


class Database(object):
    """Conexão JDBC com o banco SQLite do projeto."""

    def __init__(self, path):
        self.path = path
        self.connection = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def connect(self, create_schema=True):
        """Abre a conexão JDBC e, por padrão, garante o schema."""
        self._ensure_directory()
        try:
            JavaClass.forName(JDBC_DRIVER)
        except ClassNotFoundException:
            raise DatabaseError(
                "[ERRO] Driver JDBC do SQLite não encontrado no classpath.\n"
                "       Verifique se sqlite-jdbc está em /opt/lib "
                "(veja o pom.xml e o Dockerfile).")

        try:
            self.connection = DriverManager.getConnection(JDBC_PREFIX + self.path)
            self.connection.setAutoCommit(True)
        except SQLException as error:
            raise DatabaseError(
                "[ERRO] Não foi possível abrir o banco de dados.\n"
                "       Caminho: %s\n"
                "       Detalhe (java.sql.SQLException): %s"
                % (self.path, error.getMessage()), error)

        if create_schema:
            self.create_schema()
        return self

    def _ensure_directory(self):
        """Cria o diretório do banco usando java.io.File."""
        parent = File(self.path).getParentFile()
        if parent is not None and not parent.exists():
            parent.mkdirs()

    def create_schema(self):
        """Executa a DDL das cinco tabelas e aplica as migrações pendentes."""
        for statement in schema.STATEMENTS:
            self.execute(statement)
        self.migrate()

    def migrate(self):
        """
        Adiciona colunas que não existem em bancos criados por versões
        anteriores (um volume Docker antigo, por exemplo).
        """
        applied = []
        for table, column, statement in schema.MIGRATIONS:
            if column in self.column_names(table):
                continue
            try:
                self.execute(statement)
                applied.append("%s.%s" % (table, column))
            except DatabaseError:
                pass
        return applied

    def column_names(self, table):
        """Colunas existentes em uma tabela, via PRAGMA table_info."""
        try:
            rows = self.query("PRAGMA table_info(%s)" % table)
        except DatabaseError:
            return []
        return [row.get("name") for row in rows]

    def close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except SQLException:
                pass
            self.connection = None

    def is_connected(self):
        return self.connection is not None

    # ------------------------------------------------------------------
    # Execução de SQL
    # ------------------------------------------------------------------
    def _bind(self, statement, parameters):
        """Associa os parâmetros Python aos tipos JDBC correspondentes."""
        position = 1
        for value in parameters:
            if value is None:
                statement.setNull(position, Types.VARCHAR)
            elif isinstance(value, bool):
                statement.setInt(position, 1 if value else 0)
            elif isinstance(value, (int, long)):
                statement.setLong(position, value)
            elif isinstance(value, float):
                statement.setDouble(position, value)
            else:
                statement.setString(position, unicode(value))
            position += 1

    def execute(self, sql, parameters=()):
        """Executa um comando (INSERT/UPDATE/DELETE/DDL)."""
        statement = None
        try:
            statement = self.connection.prepareStatement(sql)
            self._bind(statement, parameters)
            return statement.executeUpdate()
        except SQLException as error:
            raise DatabaseError(
                "[ERRO] Falha ao executar SQL.\n"
                "       Detalhe (java.sql.SQLException): %s"
                % error.getMessage(), error)
        finally:
            if statement is not None:
                statement.close()

    def insert(self, sql, parameters=()):
        """Executa um INSERT e devolve o id gerado."""
        self.execute(sql, parameters)
        rows = self.query("SELECT last_insert_rowid() AS id")
        if rows:
            return rows[0]["id"]
        return None

    def query(self, sql, parameters=()):
        """Executa um SELECT e devolve uma lista de dicionários."""
        statement = None
        result_set = None
        try:
            statement = self.connection.prepareStatement(sql)
            self._bind(statement, parameters)
            result_set = statement.executeQuery()
            metadata = result_set.getMetaData()
            column_count = metadata.getColumnCount()

            columns = []
            for index in range(1, column_count + 1):
                columns.append(metadata.getColumnLabel(index))

            rows = []
            while result_set.next():
                row = {}
                for index in range(1, column_count + 1):
                    row[columns[index - 1]] = result_set.getObject(index)
                rows.append(row)
            return rows
        except SQLException as error:
            raise DatabaseError(
                "[ERRO] Falha ao consultar o banco de dados.\n"
                "       Detalhe (java.sql.SQLException): %s"
                % error.getMessage(), error)
        finally:
            if result_set is not None:
                result_set.close()
            if statement is not None:
                statement.close()

    def scalar(self, sql, parameters=(), default=None):
        """Devolve o primeiro valor da primeira linha de um SELECT."""
        rows = self.query(sql, parameters)
        if not rows:
            return default
        row = rows[0]
        for value in row.values():
            return value if value is not None else default
        return default

    def table_names(self):
        """Nomes das tabelas existentes no banco."""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")
        return [row["name"] for row in rows]

    def __repr__(self):
        return "<Database %s conectado=%s>" % (self.path, self.is_connected())
