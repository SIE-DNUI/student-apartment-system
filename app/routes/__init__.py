# -*- coding: utf-8 -*-
"""
路由模块
"""
from flask import Blueprint

# 导入各个路由模块
from app.routes import auth, dashboard, students, rooms, fees, reservations, users

__all__ = ['auth', 'dashboard', 'students', 'rooms', 'fees', 'reservations', 'users']
