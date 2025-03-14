from psycopg2 import sql

class QueryBuilder:
    def __init__(self, model_class: Type[BaseModel]):
        self.model = model_class
        self._query = []
        self._params = []
        self._table_name = model_class.__name__.lower()

    def select(self, *columns: str):
        if not columns:
            columns = ('*',)
        self._query.append(sql.SQL("SELECT {} FROM {}").format(
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.Identifier(self._table_name)
        ))
        return self

    def where(self, condition: str, *values):
        self._query.append(sql.SQL("WHERE {}").format(sql.SQL(condition)))
        self._params.extend(values)
        return self

    def order_by(self, column: str, direction: str = 'ASC'):
        self._query.append(sql.SQL("ORDER BY {} {}").format(
            sql.Identifier(column),
            sql.SQL(direction)
        ))
        return self

    def limit(self, count: int):
        self._query.append(sql.SQL("LIMIT {}").format(sql.Literal(count)))
        return self

    def raw(self, sql_part: str, *params):
        self._query.append(sql.SQL(sql_part))
        self._params.extend(params)
        return self

    def build(self) -> tuple:
        full_query = sql.SQL(' ').join(self._query)
        return full_query, self._params

    def execute(self):
        conn = DatabaseConnection().connection
        cursor = conn.cursor()
        query, params = self.build()
        cursor.execute(query, params)
        return cursor