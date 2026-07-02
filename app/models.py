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
    fee_type = db.Column(db.String(20), default='学年')  # 学年(10月)/自然年(12月)
    description = db.Column(db.Text)  # 备注说明
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    rooms = db.relationship('Room', backref='fee_standard', lazy='dynamic')
    students = db.relationship('Student', backref='fee_standard', lazy='dynamic')
    
    def get_unit_days(self):
        """获取1个单位对应的天数"""
        if self.unit == '月':
            return 30
        elif self.unit == '学期':
            return 120
        elif self.unit == '年':
            if self.fee_type == '自然年':
                return 365
            else:  # 学年（10个月，不含寒暑假）
                return 300
        elif self.unit == '次':
            return 30  # 每次按30天计算
        return 30
    
    @property
    def daily_rate(self):
        """计算日费率"""
        if self.price <= 0:
            return 0
        return self.price / self.get_unit_days()
    
    def is_holiday_fee(self):
        """是否为假期附加费"""
        return self.unit == '次'
    
    def is_academic_year(self):
        """是否为学年制（跳过2月8月）"""
        return self.unit == '年' and self.fee_type == '学年'
    
    def count_billing_days(self, start_date, end_date):
        """计算两个日期之间的计费天数
        
        学年制：跳过2月和8月（寒暑假不计费）
        自然年制或其他：按自然天数计算
        """
        if not self.is_academic_year():
            return max(0, (end_date - start_date).days)
        
        # 学年制：逐日遍历，跳过2月和8月
        billing_days = 0
        current = start_date
        while current < end_date:
            if current.month not in [2, 8]:
                billing_days += 1
            current += timedelta(days=1)
        return billing_days
    
    def add_billing_days(self, start_date, billing_days):
        """从start_date开始，经过billing_days个计费日后的日期
        
        学年制：跳过2月和8月
        自然年制或其他：直接加自然天
        """
        if not self.is_academic_year():
            return start_date + timedelta(days=billing_days)
        
        if billing_days <= 0:
            return start_date
        
        # 学年制：逐日遍历，跳过2月和8月
        current = start_date
        counted = 0
        while counted < billing_days:
            if current.month not in [2, 8]:
                counted += 1
                if counted == billing_days:
                    return current
            current += timedelta(days=1)
        return current
    
    def __repr__(self):
        return f'<FeeStandard {self.name}: {self.price}/{self.unit} ({self.fee_type})>'


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
    archived_room = db.relationship('Room', foreign_keys='Student.archived_room_id')  # 归档后显示退房房间
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
    

    
    def get_remaining_days_info(self):
        """获取有效到期日期：手动填写优先，否则返回自动计算的"""
        if self.payment_due_date:
            return self.payment_due_date
        return self.calculate_auto_due_date()
    
    def get_effective_due_date(self):
        """获取有效到期日期：手动填写优先，否则返回自动计算的"""
        if self.payment_due_date:
            return self.payment_due_date
        return self.calculate_auto_due_date()

    
    
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
        
        学年制：已消费计费天数跳过2月8月
        """
        if not self.fee_standard_id or not self.check_in_date:
            return 0
        
        fee_std = FeeStandard.query.get(self.fee_standard_id)
        if not fee_std or fee_std.price <= 0:
            return 0
        
        from datetime import date as date_module
        today = date_module.today()
        
        # 计算已消费计费天数（学年制跳过2月8月）
        billing_days = fee_std.count_billing_days(self.check_in_date, today)
        
        if billing_days <= 0:
            return 0
        
        unit_days = fee_std.get_unit_days()
        units = billing_days / unit_days
        
        # 无论单人间(bed_occupancy=2)还是双人间(bed_occupancy=1)，房费都按1人计算
        # bed_occupancy只影响房间床位占用情况，不影响个人房费
        should_pay = units * fee_std.price
        arrears = should_pay - (self.total_paid or 0)
        
        return max(0, round(arrears, 2))
    
    def has_arrears(self):
        """是否有欠费"""
        return self.calculate_arrears() > 0
    
    def calculate_base_paid(self):
        """计算基础房费已缴金额（不含假期附加费）
        
        遍历缴费记录，只统计非假期费（unit != '次'）的缴费金额。
        退费记录会扣减对应的金额。
        """
        base_paid = 0
        for record in self.fee_records.order_by(FeeRecord.payment_date).all():
            if record.record_type == 'refund':
                base_paid -= abs(record.amount)
            else:
                # 判断是否为假期费：通过关联的收费标准或备注
                is_holiday = False
                if record.notes and '假期' in record.notes:
                    is_holiday = True
                if not is_holiday:
                    base_paid += record.amount
        return max(0, base_paid)
    
    def calculate_auto_due_date(self):
        """根据基础已缴金额和收费标准，从入住日期自动计算到期日期
        
        只计算基础房费（不含假期附加费）覆盖的天数。
        学年制：智能跳过2月和8月（寒暑假不计费）
        自然年制：按自然天数连续计算
        """
        if not self.fee_standard_id or not self.check_in_date:
            return None
        
        fee_std = FeeStandard.query.get(self.fee_standard_id)
        if not fee_std or fee_std.price <= 0:
            return None
        
        base_paid = self.calculate_base_paid()
        if base_paid <= 0:
            return None
        
        unit_days = fee_std.get_unit_days()
        units = base_paid / fee_std.price
        billing_days = int(units * unit_days)
        
        # 智能计算到期日期（学年制跳过2月8月）
        return fee_std.add_billing_days(self.check_in_date, billing_days)
    
    
    def get_remaining_days_info(self):
        """获取剩余天数详细信息，用于页面展示"""
        if not self.fee_standard_id or not self.check_in_date:
            return None
        
        fee_std = FeeStandard.query.get(self.fee_standard_id)
        if not fee_std or fee_std.price <= 0:
            return None
        
        base_paid = self.calculate_base_paid()
        if base_paid <= 0:
            return None
        
        unit_days = fee_std.get_unit_days()
        
        # 已缴费可覆盖的总计费天数
        total_paid_days = (base_paid / fee_std.price) * unit_days
        
        # 已消费计费天数（学年制跳过2月8月）
        today = date.today()
        end_date = self.check_out_date if self.check_out_date and self.check_out_date < today else today
        consumed_days = fee_std.count_billing_days(self.check_in_date, end_date)
        
        # 剩余天数
        remaining_days = total_paid_days - consumed_days
        
        return {
            'total_paid_days': round(total_paid_days, 1),
            'consumed_days': consumed_days,
            'remaining_days': round(remaining_days, 1),
            'refund_amount': self.calculate_remaining_refund(),
            'is_academic_year': fee_std.is_academic_year(),
        }
    
    def preview_room_switch(self, new_fee_standard_id, switch_date):
        """预览换房型/收费标准的费用结算
        
        计算逻辑：
        1. 旧标准日费率 × 已住计费天数 = 已消费金额（学年制跳过2月8月）
        2. 基础已缴 - 已消费 = 剩余价值
        3. 新标准日费率 × 需覆盖计费天数（从switch_date到原到期日）= 需补金额
        4. 差额 = 需补金额 - 剩余价值
        
        Returns: dict with preview details, or None if cannot calculate
        """
        old_fee_std = FeeStandard.query.get(self.fee_standard_id)
        new_fee_std = FeeStandard.query.get(new_fee_standard_id)
        
        if not old_fee_std or not new_fee_std or not self.check_in_date:
            return None
        
        old_unit_days = old_fee_std.get_unit_days()
        new_unit_days = new_fee_std.get_unit_days()
        old_daily = old_fee_std.price / old_unit_days
        new_daily = new_fee_std.price / new_unit_days
        
        base_paid = self.calculate_base_paid()
        
        # 已消费计费天数和金额（学年制跳过2月8月）
        consumed_days = old_fee_std.count_billing_days(self.check_in_date, switch_date)
        consumed_value = consumed_days * old_daily
        
        # 剩余价值
        remaining_value = max(0, base_paid - consumed_value)
        
        # 原计划到期日
        original_due = self.get_effective_due_date()
        
        # 计算从切换日期到原到期日需要的费用（用新标准的计费方式）
        if original_due and original_due > switch_date:
            days_to_cover = new_fee_std.count_billing_days(switch_date, original_due)
            needed_for_period = days_to_cover * new_daily
        else:
            days_to_cover = 0
            needed_for_period = 0
        
        difference = needed_for_period - remaining_value
        
        # 新标准下剩余价值可住计费天数
        if new_daily > 0 and remaining_value > 0:
            new_remaining_days = remaining_value / new_daily
        else:
            new_remaining_days = 0
        
        # 新标准下预计到期日（用新标准的智能计费）
        new_due = new_fee_std.add_billing_days(switch_date, int(new_remaining_days)) if new_remaining_days > 0 else switch_date
        
        return {
            'old_fee': old_fee_std,
            'new_fee': new_fee_std,
            'switch_date': switch_date,
            'consumed_days': consumed_days,
            'consumed_value': round(consumed_value, 2),
            'base_paid': base_paid,
            'remaining_value': round(remaining_value, 2),
            'original_due': original_due,
            'days_to_cover': days_to_cover,
            'needed_for_period': round(needed_for_period, 2),
            'difference': round(difference, 2),
            'needs_payment': difference > 0.01,
            'new_remaining_days': round(new_remaining_days, 1),
            'new_due_date': new_due,
        }
    
    def execute_room_switch(self, new_fee_standard_id, new_room_id, switch_date, preview_data):
        """执行换房型操作
        
        Args:
            new_fee_standard_id: 新收费标准ID
            new_room_id: 新房间ID
            switch_date: 切换日期
            preview_data: preview_room_switch()的返回值
        
        Returns:
            dict with switch result
        """
        old_room = self.room
        new_room = Room.query.get(new_room_id) if new_room_id else None
        
        difference = preview_data['difference']
        
        # 更新已缴金额
        if preview_data['needs_payment']:
            self.total_paid = (self.total_paid or 0) + difference
        elif difference < -0.01:
            # 有余额，加到total_paid里（结转）
            self.total_paid = (self.total_paid or 0) + difference
        
        # 记录费用调整
        fee_record = FeeRecord()
        fee_record.student_id = self.id
        fee_record.payment_date = switch_date
        fee_record.payment_method = '费用结转'
        
        if preview_data['needs_payment']:
            fee_record.amount = difference
            fee_record.record_type = 'payment'
            fee_record.notes = f'换房型补差价：{preview_data["old_fee"].name} → {preview_data["new_fee"].name}（{switch_date}起）'
        elif difference < -0.01:
            fee_record.amount = difference
            fee_record.record_type = 'refund'
            fee_record.notes = f'换房型退差价：{preview_data["old_fee"].name} → {preview_data["new_fee"].name}（{switch_date}起）'
        else:
            fee_record.amount = 0
            fee_record.record_type = 'payment'
            fee_record.notes = f'换房型（无差价）：{preview_data["old_fee"].name} → {preview_data["new_fee"].name}（{switch_date}起）'
        
        db.session.add(fee_record)
        
        # 更新房间（处理入住人数）
        if new_room and new_room.id != (old_room.id if old_room else None):
            if old_room:
                old_room.current_occupancy = max(0, old_room.current_occupancy - self.bed_occupancy)
                if old_room.current_occupancy < old_room.capacity:
                    old_room.status = 'available'
            new_room.current_occupancy += self.bed_occupancy
            if new_room.current_occupancy >= new_room.capacity:
                new_room.status = 'full'
            self.room_id = new_room.id
        
        # 更新收费标准和到期日期
        self.fee_standard_id = new_fee_standard_id
        self.payment_due_date = preview_data['new_due_date']
        
        db.session.commit()
        
        return {
            'difference': abs(round(difference, 2)),
            'needs_payment': preview_data['needs_payment'],
            'new_due_date': preview_data['new_due_date'],
            'old_room': old_room,
            'new_room': new_room,
        }
    
    def __repr__(self):
        return f'<Student {self.student_id}: {self.name}>'


class FeeRecord(db.Model):
    """缴费记录表"""
    __tablename__ = 'fee_records'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # 缴费金额（退费为负数）
    record_type = db.Column(db.String(20), default='payment')  # payment=缴费, refund=退费
    payment_date = db.Column(db.Date, nullable=False)  # 缴费日期
    payment_method = db.Column(db.String(50))  # 缴费方式
    payment_period_start = db.Column(db.Date)  # 缴费期间开始
    payment_period_end = db.Column(db.Date)  # 缴费期间结束
    receipt_number = db.Column(db.String(50))  # 收据编号
    operator = db.Column(db.String(100))  # 经办人
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_refund(self):
        """是否为退费记录"""
        return self.record_type == 'refund'
    
    def __repr__(self):
        return f'<FeeRecord {self.id}: {self.amount} ({self.record_type})>'


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
