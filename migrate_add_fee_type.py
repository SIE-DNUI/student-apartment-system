# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 fee_standards 表添加 fee_type 字段
运行方式：python migrate_add_fee_type.py
"""
import sqlite3
import os
import sys

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'students.db')


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(fee_standards)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'fee_type' in columns:
        print("fee_type 字段已存在，无需迁移。")
        conn.close()
        return
    
    # 添加字段，默认为 '学年'
    cursor.execute("ALTER TABLE fee_standards ADD COLUMN fee_type VARCHAR(20) DEFAULT '学年'")
    conn.commit()
    print("迁移成功！已为 fee_standards 表添加 fee_type 字段（默认值 '学年'）。")
    conn.close()


if __name__ == '__main__':
    migrate()
