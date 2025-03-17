from psycopg2 import sql
from typing import Type, List, Any, Optional, Dict, Union
from contextlib import contextmanager
from modules.database import DatabaseConnection

class QueryBuilder:
    def __init__(self, model_class):
        self.model = model_class
        self._query = []
        self._params = []
        self._table_name = getattr(model_class, '_table_name', model_class.__name__.lower())
        self._joins = []
        self._group_by = None
        self._having = None

    def select(self, *columns):
        if not columns:
            columns = ('*',)
        self._query.append(sql.SQL("SELECT {} FROM {}").format(
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.Identifier(self._table_name)
        ))
        return self

    def where(self, **conditions):
        if not conditions:
            return self
            
        where_parts = []
        for field, value in conditions.items():
            if isinstance(value, tuple) and len(value) == 2:
                operator, val = value
                where_parts.append(sql.SQL("{} {} %s").format(
                    sql.Identifier(field), sql.SQL(operator)
                ))
                self._params.append(val)
            else:
                where_parts.append(sql.SQL("{} = %s").format(sql.Identifier(field)))
                self._params.append(value)
                
        self._query.append(sql.SQL("WHERE {}").format(
            sql.SQL(" AND ").join(where_parts)
        ))
        return self

    def where_raw(self, condition: str, *params):
        self._query.append(sql.SQL("WHERE {}").format(sql.SQL(condition)))
        self._params.extend(params)
        return self

    def limit(self, count: int):
        self._query.append(sql.SQL("LIMIT {}").format(sql.Literal(count)))
        return self 

    def build(self) -> tuple:

        if self._joins:
            self._query[1:1] = self._joins
            
        if self._group_by:
            self._query.append(self._group_by)
        if self._having:
            self._query.append(self._having)
            
        full_query = sql.SQL(' ').join(self._query)
        return full_query, self._params

    def execute(self):
        db = DatabaseConnection()
        with db.get_cursor() as cursor:
            query, params = self.build()
            cursor.execute(query, params)
            return cursor

    def get_all(self):
        cursor = self.execute()
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        if hasattr(self.model, 'from_db_row'):
            return [self.model.from_db_row(dict(zip(columns, row))) for row in results]
        return [dict(zip(columns, row)) for row in results]

    def get_one(self):
        self.limit(1)
        results = self.get_all()
        return results[0] if results else None