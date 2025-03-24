class Migration(ABC):
    @abstractmethod
    def up(self, connection):
        pass
    
    @abstractmethod
    def down(self, connection):
        pass

class MigrationManager:
    def __init__(self, connection):
        self.connection = connection
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        query = """
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.connection.execute(query)
    
    def get_applied_migrations(self):
        query = "SELECT name FROM migrations"
        results = self.connection.execute(query)
        return [row["name"] for row in results]
    
    def apply_migration(self, migration, name):
        if name in self.get_applied_migrations():
            return False
        
        migration.up(self.connection)
        query = "INSERT INTO migrations (name) VALUES (%s)"
        self.connection.execute(query, (name,))
        return True
    
    def revert_migration(self, migration, name):
        if name not in self.get_applied_migrations():
            return False
        
        migration.down(self.connection)
        query = "DELETE FROM migrations WHERE name = %s"
        self.connection.execute(query, (name,))
        return True