#!/usr/bin/env python3
"""
学生公寓管理系统 - 运行入口
"""
import os
from app import create_app

# 创建应用实例
app = create_app(os.environ.get('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    # 本地开发环境运行
    app.run(host='0.0.0.0', port=5000, debug=True)
