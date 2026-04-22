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
    role = db.Column(db.String(20), default='read_write')  # admin, read_only, read_write
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin_role(self):
        """检查是否为管理员角色"""
        return self.role == 'admin' or self.is_admin
    
    def can_read(self):
        """是否有读权限"""
        return self.role in ['admin', 'read_only', 'read_write'] or self.is_admin
    
    def can_write(self):
        """是否有写权限"""
        return self.role in ['admin', 'read_write'] or self.is_admin
    
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
    
    # 关联（明确指定使用 room_id 外键）
    students = db.relationship('Student', backref='room', lazy='dynamic', foreign_keys='Student.room_id')
    
    @property
    def available_beds(self):
        """剩余床位数"""
        return self.capacity - self.current_occupancy
    
    @property
    def is_available(self):
        """是否有空床位"""
        return self.current_occupancy < self.capacity
    
    @property
    def occupancy_rate(self):
        """入住率（百分比）"""
        if self.capacity == 0:
            return 0
        return round((self.current_occupancy / self.capacity) * 100, 1)
    
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
    department = db.Column(db.String(50))  # 所属业务部
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    id_card = db.Column(db.String(50))  # 身份证号
    major = db.Column(db.String(100))  # 专业
    grade = db.Column(db.String(20))  # 年级
    
    # 住宿信息
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    archived_room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))  # 归档时保存的房间ID（用于成本统计）
    check_in_date = db.Column(db.Date)  # 入住日期
    check_out_date = db.Column(db.Date)  # 预计离开日期
    
    # 费用信息
    fee_standard_id = db.Column(db.Integer, db.ForeignKey('fee_standards.id'))
    payment_due_date = db.Column(db.Date)  # 缴费到期日期
    payment_status = db.Column(db.String(20), default='paid')  # paid, unpaid, overdue
    
    # 居留许可信息
    residence_permit_expiry = db.Column(db.Date)  # 居留许可到期时间
    
    # 床位和缴费信息
    bed_occupancy = db.Column(db.Integer, default=1)  # 床位占用数：1=双人间, 2=单人间
    total_paid = db.Column(db.Float, default=0)  # 已缴房费总计
    
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated, checked_out, archived
    deleted_at = db.Column(db.DateTime)  # 删除/归档时间
    retention_until = db.Column(db.Date)  # 保留截止日期（删除后3年）
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
    
    def is_residence_permit_expiring(self, days=30):
        """居留许可是否即将到期（默认30天）"""
        if not self.residence_permit_expiry:
            return False
        return 0 <= (self.residence_permit_expiry - date.today()).days <= days
    
    def is_residence_permit_expired(self):
        """居留许可是否已过期"""
        if not self.residence_permit_expiry:
            return False
        return date.today() > self.residence_permit_expiry
    
    def days_until_residence_permit_expiry(self):
        """距离居留许可到期还有多少天"""
        if not self.residence_permit_expiry:
            return None
        delta = self.residence_permit_expiry - date.today()
        return delta.days
    
    def calculate_arrears(self):
        """计算欠费金额
        
        注意：单人间的bed_occupancy=2表示占用2个床位，但房费仍按1人计算
        因为只有1个人住在里面，只是占用了更多的床位资源
        """
        if not self.fee_standard_id or not self.check_in_date:
            return 0
        
        fee_std = FeeStandard.query.get(self.fee_standard_id)
        if not fee_std or fee_std.price <= 0:
            return 0
        
        from datetime import date as date_module
        today = date_module.today()
        days = (today - self.check_in_date).days
        
        if days <= 0:
            return 0
        
        if fee_std.unit == '月':
            units = days / 30
        elif fee_std.unit == '学期':
            units = days / 120
        elif fee_std.unit == '年':
            units = days / 365
        else:
            units = days
        
        # 无论单人间(bed_occupancy=2)还是双人间(bed_occupancy=1)，房费都按1人计算
        # bed_occupancy只影响房间床位占用情况，不影响个人房费
        should_pay = units * fee_std.price
        arrears = should_pay - (self.total_paid or 0)
        
        return max(0, round(arrears, 2))
    
    def has_arrears(self):
        """是否有欠费"""
        return self.calculate_arrears() > 0
    
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
    alert_type = db.Column(db.String(50), nullable=False)  # payment_due, payment_overdue, check_out, residence_permit_expiry
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


class MonthlyRent(db.Model):
    """每月房租记录"""
    __tablename__ = 'monthly_rents'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('year', 'month', name='uix_year_month'),)
    
    def __repr__(self):
        return f'<MonthlyRent {self.year}-{self.month:02d}: {self.amount}>'
