from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """系统用户（管理员）"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class FeeStandard(db.Model):
    """收费标准表 - 存储不同房间类型/收费档的价格"""
    __tablename__ = 'fee_standards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # 如：标准间、豪华间
    price = db.Column(db.Float, nullable=False)  # 单价
    unit = db.Column(db.String(20), default='月')  # 单位：月、学期、年
    description = db.Column(db.Text)  # 备注说明
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    rooms = db.relationship('Room', backref='fee_standard', lazy='dynamic')
    students = db.relationship('Student', backref='fee_standard', lazy='dynamic')
    
    def __repr__(self):
        return f'<FeeStandard {self.name}: {self.price}/{self.unit}>'


class Room(db.Model):
    """房间表"""
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    building = db.Column(db.String(50), nullable=False, index=True)  # 楼号
    room_number = db.Column(db.String(20), nullable=False, index=True)  # 房间号
    capacity = db.Column(db.Integer, default=2)  # 房间容量（默认2人间）
    current_occupancy = db.Column(db.Integer, default=0)  # 当前入住人数
    floor = db.Column(db.Integer)  # 楼层
    status = db.Column(db.String(20), default='available')  # available, full, maintenance
    fee_standard_id = db.Column(db.Integer, db.ForeignKey('fee_standards.id'))
    description = db.Column(db.Text)  # 备注说明
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 复合唯一索引
    __table_args__ = (
        db.UniqueConstraint('building', 'room_number', name='uix_building_room'),
    )
    
    # 关联
    students = db.relationship('Student', backref='room', lazy='dynamic')
    
    @property
    def available_beds(self):
        """剩余床位数"""
        return self.capacity - self.current_occupancy
    
    @property
    def is_available(self):
        """是否有空床位"""
        return self.current_occupancy < self.capacity
    
    def __repr__(self):
        return f'<Room {self.building}-{self.room_number}>'


class Student(db.Model):
    """学生信息表"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, index=True)  # 学号
    name = db.Column(db.String(100), nullable=False, index=True)  # 姓名
    gender = db.Column(db.String(10))  # 性别
    nationality = db.Column(db.String(50))  # 国籍
    passport_number = db.Column(db.String(50))  # 护照号
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    id_card = db.Column(db.String(50))  # 身份证号
    major = db.Column(db.String(100))  # 专业
    grade = db.Column(db.String(20))  # 年级
    
    # 住宿信息
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    check_in_date = db.Column(db.Date)  # 入住日期
    check_out_date = db.Column(db.Date)  # 预计离开日期
    
    # 费用信息
    fee_standard_id = db.Column(db.Integer, db.ForeignKey('fee_standards.id'))
    payment_due_date = db.Column(db.Date)  # 缴费到期日期
    payment_status = db.Column(db.String(20), default='paid')  # paid, unpaid, overdue
    
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated
    notes = db.Column(db.Text)  # 备注
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联缴费记录
    fee_records = db.relationship('FeeRecord', backref='student', lazy='dynamic')
    
    def calculate_payment_due_date(self, payment_amount):
        """根据缴费金额计算到期日期"""
        if not self.fee_standard_id or not payment_amount:
            return None
        
        fee_std = FeeStandard.query.get(self.fee_standard_id)
        if not fee_std or fee_std.price <= 0:
            return None
        
        # 计算可以住多少个单位时间
        units = payment_amount / fee_std.price
        
        if fee_std.unit == '月':
            days = int(units * 30)
        elif fee_std.unit == '学期':
            days = int(units * 120)
        elif fee_std.unit == '年':
            days = int(units * 365)
        else:
            days = int(units * 30)
        
        if self.payment_due_date:
            new_due_date = self.payment_due_date + timedelta(days=days)
        else:
            new_due_date = date.today() + timedelta(days=days)
        
        return new_due_date
    
    def is_payment_overdue(self):
        """是否已过期"""
        if not self.payment_due_date:
            return False
        return date.today() > self.payment_due_date
    
    def days_until_due(self):
        """距离到期还有多少天"""
        if not self.payment_due_date:
            return None
        delta = self.payment_due_date - date.today()
        return delta.days
    
    def __repr__(self):
        return f'<Student {self.student_id}: {self.name}>'


class FeeRecord(db.Model):
    """缴费记录表"""
    __tablename__ = 'fee_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # 缴费金额
    payment_date = db.Column(db.Date, nullable=False)  # 缴费日期
    payment_method = db.Column(db.String(50))  # 缴费方式
    payment_period_start = db.Column(db.Date)  # 缴费期间开始
    payment_period_end = db.Column(db.Date)  # 缴费期间结束
    receipt_number = db.Column(db.String(50))  # 收据编号
    operator = db.Column(db.String(100))  # 经办人
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FeeRecord {self.id}: {self.amount}>'


class Reservation(db.Model):
    """入住计划表 - 存储未来入住计划（以房间为单位）"""
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    # 新增字段：按用户需求设计
    department = db.Column(db.String(100))  # 部门
    group_name = db.Column(db.String(200))  # 国籍/团体名称
    person_count = db.Column(db.Integer, default=0)  # 入住人数
    rooms_needed = db.Column(db.Integer, default=1)  # 需要房间数（核心字段）
    
    # 保留原有字段（兼容）
    student_name = db.Column(db.String(100))  # 学生姓名（可选）
    student_id = db.Column(db.String(50))  # 学号（可选）
    phone = db.Column(db.String(20))
    nationality = db.Column(db.String(50))
    gender = db.Column(db.String(10))
    room_type = db.Column(db.String(50))  # 房间类型偏好
    check_in_date = db.Column(db.Date, nullable=False)  # 计划入住日期
    check_out_date = db.Column(db.Date)  # 计划离开日期
    duration_days = db.Column(db.Integer)  # 预计入住天数
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Reservation {self.group_name or self.student_name}: {self.check_in_date} ({self.rooms_needed}房)>'


class Alert(db.Model):
    """系统提醒表 - 存储到期提醒"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    alert_type = db.Column(db.String(50), nullable=False)  # payment_due, payment_overdue, check_out
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    is_read = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.Date)  # 关联的到期日期
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    # 关联学生
    student = db.relationship('Student', backref='alerts')
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<Alert {self.alert_type}: {self.title}>'
