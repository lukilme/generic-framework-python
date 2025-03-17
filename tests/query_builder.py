import unittest
from unittest.mock import patch, MagicMock, call
from psycopg2 import sql
from modules.database import DatabaseConnection
from your_module import QueryBuilder  # Substitua "your_module" pelo nome do seu módulo

class TestModel:
    _table_name = 'test_table'
    
    @classmethod
    def from_db_row(cls, row):
        instance = cls()
        for key, value in row.items():
            setattr(instance, key, value)
        return instance

class QueryBuilderTest(unittest.TestCase):
    def setUp(self):
        self.qb = QueryBuilder(TestModel)
        
    def test_init(self):
        self.assertEqual(self.qb.model, TestModel)
        self.assertEqual(self.qb._table_name, 'test_table')
        self.assertEqual(self.qb._query, [])
        self.assertEqual(self.qb._params, [])
        self.assertEqual(self.qb._joins, [])
        self.assertIsNone(self.qb._group_by)
        self.assertIsNone(self.qb._having)
        
    def test_select_all(self):
        self.qb.select()
        expected_query = sql.SQL("SELECT {} FROM {}").format(
            sql.SQL(', ').join(map(sql.Identifier, ['*'])),
            sql.Identifier('test_table')
        )
        self.assertEqual(self.qb._query[0].as_string(None), expected_query.as_string(None))
        
    def test_select_specific_columns(self):
        self.qb.select('id', 'name')
        expected_query = sql.SQL("SELECT {} FROM {}").format(
            sql.SQL(', ').join(map(sql.Identifier, ['id', 'name'])),
            sql.Identifier('test_table')
        )
        self.assertEqual(self.qb._query[0].as_string(None), expected_query.as_string(None))
        
    def test_where_equal(self):
        self.qb.select().where(id=1, name='test')
        self.assertEqual(len(self.qb._query), 2)
        self.assertEqual(self.qb._params, [1, 'test'])
        
    def test_where_with_operator(self):
        self.qb.select().where(age=('>', 18))
        self.assertEqual(len(self.qb._query), 2)
        self.assertEqual(self.qb._params, [18])
        
    def test_where_raw(self):
        self.qb.select().where_raw('id = %s OR name = %s', 1, 'test')
        self.assertEqual(len(self.qb._query), 2)
        self.assertEqual(self.qb._params, [1, 'test'])
        
    def test_join(self):
        self.qb.select().join('users', 'users.id = test_table.user_id')
        self.assertEqual(len(self.qb._joins), 1)
        
    def test_left_join(self):
        self.qb.select().left_join('users', 'users.id = test_table.user_id')
        self.assertEqual(len(self.qb._joins), 1)
        
    def test_group_by(self):
        self.qb.select().group_by('category_id')
        self.assertIsNotNone(self.qb._group_by)
        
    def test_having(self):
        self.qb.select().group_by('category_id').having('COUNT(*) > %s', 5)
        self.assertIsNotNone(self.qb._having)
        self.assertEqual(self.qb._params, [5])
        
    def test_order_by(self):
        self.qb.select().order_by('name')
        self.assertEqual(len(self.qb._query), 2)
        
    def test_order_by_desc(self):
        self.qb.select().order_by('name', 'DESC')
        self.assertEqual(len(self.qb._query), 2)
        
    def test_limit(self):
        self.qb.select().limit(10)
        self.assertEqual(len(self.qb._query), 2)
        
    def test_offset(self):
        self.qb.select().offset(5)
        self.assertEqual(len(self.qb._query), 2)
        
    def test_build_simple_query(self):
        self.qb.select().where(id=1)
        query, params = self.qb.build()
        self.assertIsInstance(query, sql.Composed)
        self.assertEqual(params, [1])
        
    def test_build_complex_query(self):
        self.qb.select('id', 'name') \
            .join('categories', 'categories.id = test_table.category_id') \
            .where(active=True) \
            .group_by('category_id') \
            .having('COUNT(*) > %s', 3) \
            .order_by('name') \
            .limit(10) \
            .offset(20)
        query, params = self.qb.build()
        self.assertIsInstance(query, sql.Composed)
        self.assertEqual(params, [True, 3])
        
    @patch.object(DatabaseConnection, 'get_cursor')
    def test_execute(self, mock_get_cursor):
        mock_cursor = MagicMock()
        mock_get_cursor.return_value.__enter__.return_value = mock_cursor
        
        self.qb.select().where(id=1)
        result = self.qb.execute()
        
        mock_get_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        self.assertEqual(result, mock_cursor)
        
    @patch.object(QueryBuilder, 'execute')
    def test_get_all_dict(self, mock_execute):
        # Simulando um modelo sem from_db_row
        qb = QueryBuilder(dict)
        
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 'test'), (2, 'test2')]
        mock_cursor.description = [('id',), ('name',)]
        mock_execute.return_value = mock_cursor
        
        results = qb.get_all()
        
        mock_execute.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {'id': 1, 'name': 'test'})
        self.assertEqual(results[1], {'id': 2, 'name': 'test2'})
        
    @patch.object(QueryBuilder, 'execute')
    def test_get_all_model(self, mock_execute):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 'test'), (2, 'test2')]
        mock_cursor.description = [('id',), ('name',)]
        mock_execute.return_value = mock_cursor
        
        results = self.qb.get_all()
        
        mock_execute.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], TestModel)
        self.assertEqual(results[0].id, 1)
        self.assertEqual(results[0].name, 'test')
        
    @patch.object(QueryBuilder, 'get_all')
    def test_get_one_with_result(self, mock_get_all):
        mock_get_all.return_value = [{'id': 1, 'name': 'test'}]
        
        result = self.qb.get_one()
        
        mock_get_all.assert_called_once()
        self.assertEqual(result, {'id': 1, 'name': 'test'})
        
    @patch.object(QueryBuilder, 'get_all')
    def test_get_one_no_result(self, mock_get_all):
        mock_get_all.return_value = []
        
        result = self.qb.get_one()
        
        mock_get_all.assert_called_once()
        self.assertIsNone(result)