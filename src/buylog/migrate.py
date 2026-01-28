#!/usr/bin/env python3
"""
Simple database migration for buylog.

Compares SQLAlchemy models to actual database schema and applies changes.
Only handles additive changes (new tables, new columns) - not destructive ones.
"""

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from .models import Base

logger = logging.getLogger("buylog")


def get_model_tables() -> dict[str, dict[str, Any]]:
    """Get table definitions from SQLAlchemy models."""
    tables = {}
    for table_name, table in Base.metadata.tables.items():
        columns = {}
        for col in table.columns:
            col_type = str(col.type)
            # Normalize types for SQLite
            if "VARCHAR" in col_type or "TEXT" in col_type:
                col_type = "TEXT"
            elif "INTEGER" in col_type:
                col_type = "INTEGER"
            elif "FLOAT" in col_type or "REAL" in col_type:
                col_type = "REAL"
            elif "DATE" in col_type and "DATETIME" not in col_type:
                col_type = "DATE"
            elif "DATETIME" in col_type:
                col_type = "DATETIME"
            elif "BOOLEAN" in col_type:
                col_type = "INTEGER"  # SQLite stores booleans as integers

            columns[col.name] = {
                "type": col_type,
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "foreign_key": [fk.target_fullname for fk in col.foreign_keys]
                if col.foreign_keys
                else None,
            }
        tables[table_name] = {"columns": columns}
    return tables


def get_db_tables(engine: Engine) -> dict[str, dict[str, Any]]:
    """Get table definitions from actual database."""
    inspector = inspect(engine)
    tables = {}

    for table_name in inspector.get_table_names():
        columns = {}
        for col in inspector.get_columns(table_name):
            col_type = str(col["type"])
            # Normalize
            if "VARCHAR" in col_type or "TEXT" in col_type:
                col_type = "TEXT"
            elif "INTEGER" in col_type:
                col_type = "INTEGER"
            elif "FLOAT" in col_type or "REAL" in col_type:
                col_type = "REAL"

            columns[col["name"]] = {
                "type": col_type,
                "nullable": col.get("nullable", True),
            }
        tables[table_name] = {"columns": columns}

    return tables


def get_sqlite_type(model_type: str) -> str:
    """Convert model type to SQLite type."""
    model_type = model_type.upper()
    if "INT" in model_type:
        return "INTEGER"
    elif "FLOAT" in model_type or "REAL" in model_type:
        return "REAL"
    elif "DATE" in model_type and "TIME" not in model_type:
        return "DATE"
    elif "DATETIME" in model_type or "TIMESTAMP" in model_type:
        return "DATETIME"
    else:
        return "TEXT"


def generate_migrations(engine: Engine) -> list[str]:
    """Generate SQL statements needed to sync database with models."""
    model_tables = get_model_tables()
    db_tables = get_db_tables(engine)

    migrations = []

    for table_name, table_def in model_tables.items():
        if table_name not in db_tables:
            # Create new table
            cols = []
            for col_name, col_def in table_def["columns"].items():
                col_sql = f"{col_name} {get_sqlite_type(col_def['type'])}"
                if col_def.get("primary_key"):
                    col_sql += " PRIMARY KEY"
                if not col_def.get("nullable", True) and not col_def.get("primary_key"):
                    col_sql += " NOT NULL"
                if col_def.get("foreign_key"):
                    # Extract table.column from foreign key
                    fk = col_def["foreign_key"][0]
                    col_sql += f" REFERENCES {fk.replace('.', '(')}"
                    col_sql += ")"
                cols.append(col_sql)

            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    "
            create_sql += ",\n    ".join(cols)
            create_sql += "\n)"
            migrations.append(create_sql)
        else:
            # Check for missing columns
            db_columns = db_tables[table_name]["columns"]
            for col_name, col_def in table_def["columns"].items():
                if col_name not in db_columns:
                    sqlite_type = get_sqlite_type(col_def["type"])
                    alter_sql = (
                        f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sqlite_type}"
                    )
                    if col_def.get("foreign_key"):
                        fk = col_def["foreign_key"][0]
                        alter_sql += f" REFERENCES {fk.replace('.', '(')}"
                        alter_sql += ")"
                    migrations.append(alter_sql)

    return migrations


def run_migrations(engine: Engine, dry_run: bool = False) -> list[str]:
    """
    Run database migrations.

    Args:
        engine: SQLAlchemy engine
        dry_run: If True, only return SQL without executing

    Returns:
        List of SQL statements executed (or would be executed)
    """
    migrations = generate_migrations(engine)

    if not migrations:
        logger.info("Database schema is up to date")
        return []

    if dry_run:
        return migrations

    with engine.connect() as conn:
        for sql in migrations:
            logger.info(f"Executing: {sql[:80]}...")
            try:
                conn.execute(text(sql))
            except Exception as e:
                # Some statements may fail if already applied (e.g., duplicate column)
                # Log and continue
                logger.warning(f"Migration warning: {e}")
        conn.commit()

    logger.info(f"Applied {len(migrations)} migration(s)")
    return migrations


def check_migrations(engine: Engine) -> list[str]:
    """Check what migrations are needed without applying them."""
    return generate_migrations(engine)
