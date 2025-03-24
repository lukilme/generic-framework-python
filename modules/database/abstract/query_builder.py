class QueryBuilder:
    @staticmethod
    def build_select(table, columns="*", where=None, params=None, limit=None, offset=None, order_by=None):
        query = f"SELECT {columns} FROM {table}"
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        return query, params or ()
    
    @staticmethod
    def build_insert(table, columns, returning="id"):
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        if returning:
            query += f" RETURNING {returning}"
        return query
    
    @staticmethod
    def build_update(table, columns, where):
        set_clause = ", ".join([f"{col} = %s" for col in columns])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        return query
    
    @staticmethod
    def build_delete(table, where):
        query = f"DELETE FROM {table} WHERE {where}"
        return query