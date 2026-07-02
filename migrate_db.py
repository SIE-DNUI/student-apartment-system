#!/usr/bin/env python3
"""修改数据库字段名：passport_number -> department"""
import sqlite3
import os

# 数据库路径
db_path = 'instance/app.db'

if not os.path.exists(db_path):
    print(f'❌ 数据库文件不存在: {db_path}')
    exit(1)

# 备份
backup_path = 'instance/app.db.bak'
import shutil
shutil.copy(db_path, backup_path)
print(f'✅ 已备份到: {backup_path}')

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查当前字段
cursor.execute("PRAGMA table_info(students)")
columns = [col[1] for col in cursor.fetchall()]
print(f'当前字段: {columns}')

if 'department' in columns:
    print('✅ department 字段已存在，无需修改')
elif 'passport_number' in columns:
    # 修改字段名
    cursor.execute('ALTER TABLE students RENAME COLUMN passport_number TO department')
    conn.commit()
    print('✅ 字段修改成功：passport_number -> department')
else:
    print('❌ 未找到 passport_number 或 department 字段')

conn.close()
