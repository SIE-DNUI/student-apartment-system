import os
from flask import Flask
from flask_login import LoginManager
from config import config

db = None
login_manager = LoginManager()


def create_app(config_name=None):
    """应用工厂"""
    global db
    
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # 确保上传目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    # 确保实例目录存在
    os.makedirs('instance', exist_ok=True)
    
    # 初始化扩展
    from app.models import db as _db
    db = _db
    db.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # 注册蓝图
    from app.routes import auth, dashboard, students, rooms, fees, reservations
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(students.bp)
    app.register_blueprint(rooms.bp)
    app.register_blueprint(fees.bp)
    app.register_blueprint(reservations.bp)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 检查是否需要创建默认收费标准
        from app.models import FeeStandard
        if FeeStandard.query.count() == 0:
            # 创建默认收费标准
            default_standards = [
                FeeStandard(name='标准双人间', price=800, unit='月', description='普通双人间配置'),
                FeeStandard(name='高级双人间', price=1200, unit='月', description='带独立卫浴'),
                FeeStandard(name='单人间', price=1500, unit='月', description='独立房间'),
            ]
            for std in default_standards:
                db.session.add(std)
            db.session.commit()
    
    return app
