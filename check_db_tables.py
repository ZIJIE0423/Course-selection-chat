from app.database.mysql import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print("数据库中的表:", tables)

# 检查特定表
crawled_table_exists = 'crawled_documents' in tables
print("crawled_documents 表是否存在:", crawled_table_exists)