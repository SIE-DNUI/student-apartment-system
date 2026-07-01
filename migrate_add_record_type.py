# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 fee_records 表添加 record_type 字段
运行方式：python migrate_add_record_type.py
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
    cursor.execute("PRAGMA table_info(fee_records)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'record_type' in columns:
        print("record_type 字段已存在，无需迁移。")
        conn.close()
        return
    
    # 添加字段
    cursor.execute("ALTER TABLE fee_records ADD COLUMN record_type VARCHAR(20) DEFAULT 'payment'")
    conn.commit()
    print("迁移成功！已为 fee_records 表添加 record_type 字段（默认值 'payment'）。")
    conn.close()


if __name__ == '__main__':
    migrate()
