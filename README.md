# 学生公寓管理系统

基于 Flask 的学生公寓管理系统，支持学生信息管理、房间管理、收费管理和入住计划预判等功能。

## 功能特性

- **学生管理**：增删改查、Excel批量导入
- **房间管理**：批量设置房间、实时状态展示、自动容量管理
- **收费管理**：多种收费标准、到期自动提醒
- **入住计划**：上传未来入住计划、智能预判房间需求
- **Dashboard**：房间总览、欠费提醒、到期提醒

## 技术栈

- 后端：Flask 3.0 + SQLAlchemy
- 前端：Bootstrap 5 + Jinja2
- 数据库：SQLite（开发）/ PostgreSQL（生产）

## 快速开始

```bash
git clone https://github.com/SIE-DNUI/student-apartment-system.git
cd student-apartment-system
pip install -r requirements.txt
flask init-db
flask create-admin
flask run
```

访问 http://127.0.0.1:5000

## 默认管理员

- 用户名：admin
- 密码：admin123

## 部署到 PythonAnywhere

1. 克隆仓库到 PythonAnywhere
2. 创建虚拟环境并安装依赖
3. 初始化数据库
4. 配置 WSGI 文件

## License

MIT License
