# 部署到 GitHub 说明

## 方法一：使用 GitHub Token（推荐）

### 1. 创建 Personal Access Token
1. 登录 GitHub
2. 进入 Settings → Developer settings → Personal access tokens
3. 点击 "Generate new token (classic)"
4. 选择权限：`repo` (完全控制私有仓库)
5. 生成并复制 token

### 2. 推送代码

```bash
cd student-apartment-system
git remote set-url origin https://YOUR_GITHUB_TOKEN@github.com/SIE-DNUI/student-apartment-system.git
git push -u origin main
```

或者使用 URL 格式：
```bash
git push https://YOUR_GITHUB_TOKEN@github.com/SIE-DNUI/student-apartment-system.git main
```

## 方法二：克隆并手动合并（如果仓库有现有内容）

```bash
# 克隆空仓库
git clone https://github.com/SIE-DNUI/student-apartment-system.git temp
cd temp

# 将新代码复制进去
cp -r /path/to/new/code/* .

# 提交并推送
git add -A
git commit -m "Initial commit: 学生公寓管理系统 v1.0"
git push

# 清理临时文件夹
cd ..
rm -rf temp
```

## 方法三：使用 GitHub CLI

```bash
gh auth login
gh repo clone SIE-DNUI/student-apartment-system
cd student-apartment-system
# 复制新代码到此处
git add -A
git commit -m "Initial commit"
gh repo push
```

## 推送后设置

### 1. PythonAnywhere 部署
```bash
# 在 PythonAnywhere Bash 终端执行
git clone https://github.com/SIE-DNUI/student-apartment-system.git
cd student-apartment-system
pip install -r requirements.txt
python init_db.py init-db
python init_db.py create-admin
```

### 2. 配置 WSGI 文件
在 PythonAnywhere 的 Web 选项卡中配置：
- 工作目录：`/home/你的用户名/student-apartment-system`
- WSGI 文件：选择 Flask 应用

## 文件结构
```
student-apartment-system/
├── app/
│   ├── __init__.py      # 应用工厂
│   ├── models.py        # 数据库模型
│   ├── routes/          # 路由
│   └── templates/       # 模板
├── instance/            # 数据库存放目录
├── uploads/             # 上传文件目录
├── config.py           # 配置文件
├── run.py              # 运行入口
├── init_db.py          # 数据库初始化
├── requirements.txt    # 依赖清单
└── README.md           # 说明文档
```
