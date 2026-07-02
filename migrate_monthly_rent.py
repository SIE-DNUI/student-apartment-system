#!/usr/bin/env python3
"""迁移脚本：添加 MonthlyRent 表"""
import sqlite3
import os

# 数据库路径
db_path = 'instance/students.db'

if not os.path.exists(db_path):
    print(f'❌ 数据库文件不存在: {db_path}')
    exit(1)

# 备份
backup_path = 'instance/students.db.bak'
import shutil
shutil.copy(db_path, backup_path)
print(f'✅ 已备份到: {backup_path}')

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_rents'")
if cursor.fetchone():
    print('✅ monthly_rents 表已存在，无需创建')
else:
    # 创建 monthly_rents 表
    cursor.execute('''
        CREATE TABLE monthly_rents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year, month)
        )
    ''')
    conn.commit()
    print('✅ monthly_rents 表创建成功')

conn.close()
print('✅ 迁移完成')
