# -*- coding: utf-8 -*-
"""
仪表盘路由模块
提供系统首页和数据统计功能
"""
from flask import render_template, Blueprint, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func, or_
from app.models import db
from app.models import Room, Student, FeeRecord, Reservation, Alert

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # 获取统计数据
    stats = get_dashboard_stats()
    
    # 获取未读提醒
    alerts = Alert.query.filter_by(is_read=False).order_by(Alert.created_at.desc()).limit(10).all()
    
    # 获取近期入住计划
    upcoming_reservations = Reservation.query.filter(
        Reservation.check_in_date >= date.today(),
        Reservation.status == 'pending'
    ).order_by(Reservation.check_in_date).limit(5).all()
    
    # 缴费即将到期提醒
    upcoming_due = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date <= date.today() + timedelta(days=7),
        Student.payment_due_date >= date.today()
    ).all()
    
    # 居留许可即将到期提醒（30天内）
    residence_permit_expiring = Student.query.filter(
        Student.residence_permit_expiry != None,
        Student.residence_permit_expiry <= date.today() + timedelta(days=30),
        Student.residence_permit_expiry >= date.today()
    ).all()
    
    # 检查是否需要显示居留许可到期提醒（当天只显示一次）
    show_residence_alert = True
    if session.get('residence_alert_dismissed_date') == str(date.today()):
        show_residence_alert = False
    
    # 欠费学生列表
    all_students = Student.query.filter(Student.status == 'active').all()
    arrears_students = [s for s in all_students if s.has_arrears()]
    
    # 检查是否需要显示欠费提醒（当天只显示一次）- 问题5优化
    show_arrears_alert = True
    if session.get('arrears_alert_dismissed_date') == str(date.today()):
        show_arrears_alert = False
    
    return render_template('dashboard/index.html', 
                         title='仪表盘',
                         stats=stats,
                         alerts=alerts,
                         upcoming_reservations=upcoming_reservations,
                         upcoming_due=upcoming_due,
                         residence_permit_expiring=residence_permit_expiring,
                         show_residence_alert=show_residence_alert,
                         show_arrears_alert=show_arrears_alert,
                         arrears_students=arrears_students)


@bp.route('/dismiss-residence-alert')
@login_required
def dismiss_residence_alert():
    """关闭居留许可到期提醒（当天不再显示）"""
    session['residence_alert_dismissed_date'] = str(date.today())
    flash('提醒已关闭', 'info')
    return redirect(url_for('dashboard.index'))


@bp.route('/dismiss-arrears-alert')
@login_required
def dismiss_arrears_alert():
    """关闭欠费提醒（当天不再显示）- 问题5优化"""
    session['arrears_alert_dismissed_date'] = str(date.today())
    flash('欠费提醒已关闭，今天不再显示', 'info')
    return redirect(url_for('dashboard.index'))


def get_dashboard_stats():
    """获取仪表盘统计数据"""
    total_rooms = Room.query.count()
    available_rooms = Room.query.filter(Room.current_occupancy < Room.capacity).count()
    occupied_rooms = total_rooms - available_rooms
    
    # 计算总床位数和已用床位数
    total_capacity = db.session.query(func.sum(Room.capacity)).scalar() or 0
    total_occupancy = db.session.query(func.sum(Room.current_occupancy)).scalar() or 0
    available_beds = total_capacity - total_occupancy
    
    # 学生统计
    total_students = Student.query.filter(Student.status == 'active').count()
    
    # 已入住学生
    housed_students = Student.query.filter(
        Student.status == 'active',
        Student.room_id != None
    ).count()
    
    # 未入住学生
    unhoused_students = Student.query.filter(
        Student.status == 'active',
        Student.room_id == None
    ).count()
    
    # 今日入住
    today_checkins = Student.query.filter_by(check_in_date=date.today()).count()
    
    # 即将到期
    due_soon = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date <= date.today() + timedelta(days=7),
        Student.payment_due_date >= date.today()
    ).count()
    
    # 已过期
    overdue = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date < date.today()
    ).count()
    
    # 居留许可即将到期（30天内）
    residence_expiring = Student.query.filter(
        Student.residence_permit_expiry != None,
        Student.residence_permit_expiry <= date.today() + timedelta(days=30),
        Student.residence_permit_expiry >= date.today()
    ).count()
    
    # 居留许可已过期
    residence_expired = Student.query.filter(
        Student.residence_permit_expiry != None,
        Student.residence_permit_expiry < date.today()
    ).count()
    
    # 待确认的入住计划
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    
    # 总计划房间数（未来90天）
    future_date = date.today() + timedelta(days=90)
    future_rooms = db.session.query(func.sum(Reservation.rooms_needed)).filter(
        Reservation.status != 'cancelled',
        Reservation.check_in_date <= future_date
    ).scalar() or 0
    
    # 今日计划房间占用
    today_rooms = db.session.query(func.sum(Reservation.rooms_needed)).filter(
        Reservation.check_in_date <= date.today(),
        db.or_(Reservation.check_out_date > date.today(), Reservation.check_out_date == None),
        Reservation.status != 'cancelled'
    ).scalar() or 0
    
    # 欠费学生统计
    all_students = Student.query.filter(Student.status == 'active').all()
    arrears_students = [s for s in all_students if s.has_arrears()]
    arrears_count = len(arrears_students)
    total_arrears = sum(s.calculate_arrears() for s in arrears_students)
    
    return {
        'arrears_count': arrears_count,
        'total_arrears': total_arrears,
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'total_capacity': total_capacity,
        'total_occupancy': total_occupancy,
        'available_beds': available_beds,
        'total_students': total_students,
        'housed_students': housed_students,
        'unhoused_students': unhoused_students,
        'today_checkins': today_checkins,
        'due_soon': due_soon,
        'overdue': overdue,
        'residence_expiring': residence_expiring,
        'residence_expired': residence_expired,
        'pending_reservations': pending_reservations,
        'occupancy_rate': round(total_occupancy / total_capacity * 100, 1) if total_capacity > 0 else 0,
        'today_rooms_used': today_rooms,
        'future_rooms_planned': future_rooms
    }


@bp.route('/alerts')
@login_required
def alerts():
    """提醒列表"""
    alert_list = Alert.query.order_by(Alert.created_at.desc()).all()
    # 获取各类提醒统计
    stats = get_alert_stats()
    return render_template('dashboard/alerts.html', title='提醒中心', alerts=alert_list, 
                          filter_type=None, stats=stats)


@bp.route('/alerts/type/<alert_type>')
@login_required
def alerts_by_type(alert_type):
    """按类型筛选提醒 - 问题4"""
    # 获取各类提醒统计
    stats = get_alert_stats()
    
    # 根据类型筛选提醒
    if alert_type == 'payment_due':
        # 费用即将到期（7天内）
        alert_list = Alert.query.filter_by(alert_type='payment_due').order_by(Alert.created_at.desc()).all()
        # 同时获取即将到期的学生
        upcoming_students = Student.query.filter(
            Student.payment_due_date != None,
            Student.payment_due_date <= date.today() + timedelta(days=7),
            Student.payment_due_date >= date.today()
        ).all()
        if upcoming_students:
            # 为学生创建提醒
            for student in upcoming_students:
                existing = Alert.query.filter_by(
                    student_id=student.id,
                    alert_type='payment_due',
                    is_read=False
                ).first()
                if not existing:
                    alert = Alert()
                    alert.student_id = student.id
                    alert.alert_type = 'payment_due'
                    alert.title = f'{student.name} 费用即将到期'
                    alert.message = f'预计到期日期: {student.payment_due_date} (还有{(student.payment_due_date - date.today()).days}天)'
                    alert.priority = 'high'
                    alert.due_date = student.payment_due_date
                    db.session.add(alert)
            db.session.commit()
            alert_list = Alert.query.filter_by(alert_type='payment_due').order_by(Alert.created_at.desc()).all()
    elif alert_type == 'payment_overdue':
        # 欠费提醒
        alert_list = Alert.query.filter_by(alert_type='payment_overdue').order_by(Alert.created_at.desc()).all()
        # 同时获取欠费学生并创建提醒
        all_students = Student.query.filter(Student.status == 'active').all()
        arrears_students = [s for s in all_students if s.has_arrears()]
        for student in arrears_students:
            existing = Alert.query.filter_by(
                student_id=student.id,
                alert_type='payment_overdue',
                is_read=False
            ).first()
            if not existing:
                alert = Alert()
                alert.student_id = student.id
                alert.alert_type = 'payment_overdue'
                alert.title = f'{student.name} 欠费'
                alert.message = f'欠费金额: ¥{student.calculate_arrears():.2f}'
                alert.priority = 'urgent'
                alert.due_date = student.payment_due_date
                db.session.add(alert)
        db.session.commit()
        alert_list = Alert.query.filter_by(alert_type='payment_overdue').order_by(Alert.created_at.desc()).all()
    elif alert_type == 'residence_permit_expiry':
        # 居留许可到期
        alert_list = Alert.query.filter_by(alert_type='residence_permit_expiry').order_by(Alert.created_at.desc()).all()
        # 同时获取即将到期的学生并创建提醒
        expiring_students = Student.query.filter(
            Student.residence_permit_expiry != None,
            Student.residence_permit_expiry <= date.today() + timedelta(days=30),
            Student.residence_permit_expiry >= date.today()
        ).all()
        for student in expiring_students:
            existing = Alert.query.filter_by(
                student_id=student.id,
                alert_type='residence_permit_expiry',
                is_read=False
            ).first()
            if not existing:
                alert = Alert()
                alert.student_id = student.id
                alert.alert_type = 'residence_permit_expiry'
                alert.title = f'{student.name} 居留许可即将到期'
                alert.message = f'到期日期: {student.residence_permit_expiry} (还有{student.days_until_residence_permit_expiry()}天)'
                alert.priority = 'high'
                alert.due_date = student.residence_permit_expiry
                db.session.add(alert)
        db.session.commit()
        alert_list = Alert.query.filter_by(alert_type='residence_permit_expiry').order_by(Alert.created_at.desc()).all()
    else:
        alert_list = Alert.query.order_by(Alert.created_at.desc()).all()
    
    return render_template('dashboard/alerts.html', title='提醒中心', alerts=alert_list, 
                          filter_type=alert_type, stats=stats)


def get_alert_stats():
    """获取各类提醒统计 - 问题4"""
    # 费用即将到期
    due_soon_count = Student.query.filter(
        Student.payment_due_date != None,
        Student.payment_due_date <= date.today() + timedelta(days=7),
        Student.payment_due_date >= date.today()
    ).count()
    
    # 欠费学生
    all_students = Student.query.filter(Student.status == 'active').all()
    arrears_count = len([s for s in all_students if s.has_arrears()])
    
    # 居留许可到期
    residence_count = Student.query.filter(
        Student.residence_permit_expiry != None,
        Student.residence_permit_expiry <= date.today() + timedelta(days=30),
        Student.residence_permit_expiry >= date.today()
    ).count()
    
    return {
        'due_soon_count': due_soon_count,
        'arrears_count': arrears_count,
        'residence_count': residence_count
    }


@bp.route('/alerts/<int:alert_id>/read')
@login_required
def mark_alert_read(alert_id):
    """标记提醒为已读"""
    alert = Alert.query.get_or_404(alert_id)
    alert.mark_as_read()
    db.session.commit()
    flash('已标记为已读', 'success')
    return redirect(url_for('dashboard.alerts'))


@bp.route('/alerts/read-all')
@login_required
def mark_all_alerts_read():
    """标记所有提醒为已读"""
    Alert.query.filter_by(is_read=False).update({'is_read': True})
    db.session.commit()
    flash('已标记所有提醒为已读', 'success')
    return redirect(url_for('dashboard.alerts'))


@bp.route('/room-status')
@login_required
def room_status():
    """房间状态总览"""
    rooms = Room.query.order_by(Room.building, Room.room_number).all()
    
    # 按楼栋分组
    buildings = {}
    for room in rooms:
        if room.building not in buildings:
            buildings[room.building] = {
                'total_rooms': 0,
                'available_rooms': 0,
                'total_capacity': 0,
                'total_occupancy': 0,
                'rooms': []
            }
        buildings[room.building]['total_rooms'] += 1
        buildings[room.building]['total_capacity'] += room.capacity
        buildings[room.building]['total_occupancy'] += room.current_occupancy
        if room.is_available:
            buildings[room.building]['available_rooms'] += 1
        buildings[room.building]['rooms'].append(room)
    
    return render_template('dashboard/room_status.html', title='房间状态', buildings=buildings)
