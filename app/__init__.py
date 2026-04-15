# -*- coding: utf-8 -*-
"""
应用初始化模块
"""
import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name=None):
    """应用工厂"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 确保上传目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    # 确保实例目录存在
    os.makedirs('instance', exist_ok=True)
    
    # 从models导入db（避免循环导入）
    from app.models import db
    db.init_app(app)
    
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # 模板上下文处理器
    @app.context_processor
    def utility_processor():
        from app.models import Alert
        from flask_login import current_user
        
        def alerts_count():
            if not current_user.is_authenticated:
                return 0
            return Alert.query.filter_by(is_read=False).count()
        
        def is_admin():
            """检查当前用户是否为管理员"""
            if not current_user.is_authenticated:
                return False
            return current_user.is_admin_role()
        
        return dict(alerts_count=alerts_count, is_admin=is_admin)
    
    # 注册蓝图
    from app.routes import auth, dashboard, students, rooms, fees, reservations, users
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(students.bp)
    app.register_blueprint(rooms.bp)
    app.register_blueprint(fees.bp)
    app.register_blueprint(reservations.bp)
    app.register_blueprint(users.bp)
    
    return app
