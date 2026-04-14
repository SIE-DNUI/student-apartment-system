from flask import render_template, Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func
from app import db
from app.models import Room, Student, FeeRecord, Reservation, Alert, FeeStandard

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
    
    return render_template('dashboard/index.html', 
                         title='仪表盘',
                         stats=stats,
                         alerts=alerts,
                         upcoming_reservations=upcoming_reservations,
                         upcoming_due=upcoming_due)


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
    total_students = Student.query.filter_by(status='active').count()
    
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
    
    # 待确认的入住计划
    pending_reservations = Reservation.query.filter_by(status='pending').count()
    
    return {
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'total_capacity': total_capacity,
        'total_occupancy': total_occupancy,
        'available_beds': available_beds,
        'total_students': total_students,
        'today_checkins': today_checkins,
        'due_soon': due_soon,
        'overdue': overdue,
        'pending_reservations': pending_reservations,
        'occupancy_rate': round(total_occupancy / total_capacity * 100, 1) if total_capacity > 0 else 0
    }


@bp.route('/alerts')
@login_required
def alerts():
    """提醒列表"""
    alert_list = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template('dashboard/alerts.html', title='提醒中心', alerts=alert_list)


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
