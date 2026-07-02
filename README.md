# 学生公寓管理系统

基于 Flask 的学生公寓管理系统，支持房间管理、学生管理、入住计划和费用管理。

## 功能特性

### 🔑 核心功能

- **房间管理** - 管理所有房间，支持按楼号、楼层筛选
- **学生管理** - 管理学生信息，包括个人资料、入住记录
- **入住计划** - 以房间为单位的入住计划管理
  - 支持按部门、团体名称管理入住计划
  - 精确到天的房间占用日历视图
  - 自动计算所需房间数（每间2人）
  - 高峰期预警（红色标注缺房天数）
  - 支持批量导入Excel数据
- **费用管理** - 管理收费标准和缴费记录
- **提醒中心** - 缴费到期提醒

### 📊 入住计划模块（新设计）

以房间为单位的入住计划管理：

```
┌─────────────────────────────────────────────────────────────┐
│  入住计划管理                                                  │
├─────────────────────────────────────────────────────────────┤
│  部门          │ 国际交流处                                    │
│  团体名称      │ 美国交换生团                                  │
│  入住时间      │ 2024-03-01                                  │
│  离开时间      │ 2024-06-30                                  │
│  入住人数      │ 20                                          │
│  需要房间数    │ 10  (系统自动计算: 20÷2=10)                  │
└─────────────────────────────────────────────────────────────┘
```

**日历视图特点：**
- 显示选定月份的每一天
- 每天显示：已占用房间数、剩余房间数
- 红色标注缺房天数（高峰期预警）
- 点击可查看当天详细的入住计划列表

### 📥 Excel批量导入

支持导入以下格式的Excel文件：

| 部门 | 国籍/团体名称 | 入住时间 | 离开时间 | 入住人数 | 需要房间数 | 备注 |
|------|--------------|----------|----------|----------|-----------|------|
| 国际交流处 | 美国交换生团 | 2024-03-01 | 2024-06-30 | 20 | 10 | 春季学期 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py init-db
python init_db.py migrate
python init_db.py create-admin
```

### 3. 运行系统

```bash
python run.py
```

访问 http://localhost:5000

- 用户名: admin
- 密码: admin123

## 项目结构

```
student-apartment-system/
├── app/
│   ├── __init__.py          # 应用工厂
│   ├── models.py            # 数据库模型
│   ├── routes/              # 路由模块
│   │   ├── auth.py          # 认证
│   │   ├── dashboard.py     # 仪表盘
│   │   ├── fees.py          # 费用管理
│   │   ├── reservations.py  # 入住计划 ★ 新设计
│   │   ├── rooms.py         # 房间管理
│   │   └── students.py      # 学生管理
│   └── templates/           # 模板文件
├── config.py                # 配置文件
├── init_db.py               # 数据库工具
└── run.py                   # 启动文件
```

## 数据库工具

```bash
# 初始化数据库
python init_db.py init-db

# 迁移字段（Reservation模型更新后）
python init_db.py migrate

# 创建管理员
python init_db.py create-admin --username admin --password yourpassword

# 添加演示数据
python init_db.py seed

# 重置数据库
python init_db.py reset-db
```

## 部署到 PythonAnywhere

1. 克隆仓库到 PythonAnywhere
2. 创建虚拟环境并安装依赖
3. 初始化数据库
4. 配置 WSGI 文件
5. 重启 Web App

## 技术栈

- **后端**: Flask, SQLAlchemy, Flask-Login
- **前端**: Bootstrap 5, Bootstrap Icons
- **Excel处理**: openpyxl
- **数据库**: SQLite (默认), MySQL (生产环境)

## License

MIT License
