"""
Backend: Управление финансовыми целями пользователя
Args: event - HTTP запрос с методом, телом и заголовками
      context - объект контекста с request_id и метаданными
Returns: HTTP ответ с данными целей или ошибкой
"""

import json
import os
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    method: str = event.get('httpMethod', 'GET')
    
    # Handle CORS OPTIONS request
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, Cookie',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    # Извлечение userId из cookie
    user_id = extract_user_id_from_cookies(event)
    if not user_id:
        return error_response('Authentication required', 401)
    
    conn = None
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        
        if method == 'GET':
            return get_goals(conn, user_id)
        elif method == 'POST':
            body_data = json.loads(event.get('body', '{}'))
            return create_goal(conn, user_id, body_data)
        elif method == 'PUT':
            body_data = json.loads(event.get('body', '{}'))
            return update_goal(conn, user_id, body_data)
        elif method == 'DELETE':
            params = event.get('queryStringParameters', {}) or {}
            goal_id = params.get('id')
            if not goal_id:
                return error_response('Goal ID is required', 400)
            return delete_goal(conn, user_id, int(goal_id))
        else:
            return error_response('Method not allowed', 405)
            
    except Exception as e:
        return error_response(f'Server error: {str(e)}', 500)
    finally:
        if conn:
            conn.close()

def get_goals(conn, user_id: int) -> Dict[str, Any]:
    """Получение всех целей пользователя"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT id, title, target_amount, current_amount, target_date, 
                       description, priority, status, created_at, updated_at
                FROM goals 
                WHERE user_id = %s 
                ORDER BY priority DESC, created_at DESC
            ''', (user_id,))
            
            goals = cur.fetchall()
            
            # Преобразуем даты в строки для JSON
            goals_list = []
            for goal in goals:
                goal_dict = dict(goal)
                if goal_dict['target_date']:
                    goal_dict['target_date'] = goal_dict['target_date'].isoformat()
                goal_dict['created_at'] = goal_dict['created_at'].isoformat()
                goal_dict['updated_at'] = goal_dict['updated_at'].isoformat()
                goals_list.append(goal_dict)
            
            return success_response({'goals': goals_list})
            
    except Exception as e:
        return error_response(f'Failed to get goals: {str(e)}', 500)

def create_goal(conn, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Создание новой цели"""
    title = data.get('title', '').strip()
    target_amount = data.get('target_amount', 0)
    target_date = data.get('target_date')
    description = data.get('description', '').strip()
    priority = data.get('priority', 'medium')
    
    if not title:
        return error_response('Title is required', 400)
    
    if target_amount <= 0:
        return error_response('Target amount must be positive', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO goals (user_id, title, target_amount, current_amount, 
                                 target_date, description, priority, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, title, target_amount, current_amount, target_date, 
                          description, priority, status, created_at, updated_at
            ''', (user_id, title, target_amount, 0, target_date, description, priority, 'active'))
            
            goal = cur.fetchone()
            conn.commit()
            
            # Преобразуем даты в строки для JSON
            goal_dict = dict(goal)
            if goal_dict['target_date']:
                goal_dict['target_date'] = goal_dict['target_date'].isoformat()
            goal_dict['created_at'] = goal_dict['created_at'].isoformat()
            goal_dict['updated_at'] = goal_dict['updated_at'].isoformat()
            
            return success_response({'goal': goal_dict})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Failed to create goal: {str(e)}', 500)

def update_goal(conn, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Обновление цели"""
    goal_id = data.get('id')
    if not goal_id:
        return error_response('Goal ID is required', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем принадлежность цели пользователю
            cur.execute('SELECT id FROM goals WHERE id = %s AND user_id = %s', (goal_id, user_id))
            if not cur.fetchone():
                return error_response('Goal not found', 404)
            
            # Обновляем поля
            update_fields = []
            params = []
            
            if 'title' in data:
                update_fields.append('title = %s')
                params.append(data['title'].strip())
            
            if 'target_amount' in data:
                if data['target_amount'] <= 0:
                    return error_response('Target amount must be positive', 400)
                update_fields.append('target_amount = %s')
                params.append(data['target_amount'])
            
            if 'current_amount' in data:
                update_fields.append('current_amount = %s')
                params.append(data['current_amount'])
            
            if 'target_date' in data:
                update_fields.append('target_date = %s')
                params.append(data['target_date'])
            
            if 'description' in data:
                update_fields.append('description = %s')
                params.append(data['description'].strip())
            
            if 'priority' in data:
                update_fields.append('priority = %s')
                params.append(data['priority'])
            
            if 'status' in data:
                update_fields.append('status = %s')
                params.append(data['status'])
            
            if not update_fields:
                return error_response('No fields to update', 400)
            
            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            params.extend([goal_id, user_id])
            
            query = f'''
                UPDATE goals 
                SET {', '.join(update_fields)}
                WHERE id = %s AND user_id = %s
                RETURNING id, title, target_amount, current_amount, target_date, 
                          description, priority, status, created_at, updated_at
            '''
            
            cur.execute(query, params)
            goal = cur.fetchone()
            conn.commit()
            
            # Преобразуем даты в строки для JSON
            goal_dict = dict(goal)
            if goal_dict['target_date']:
                goal_dict['target_date'] = goal_dict['target_date'].isoformat()
            goal_dict['created_at'] = goal_dict['created_at'].isoformat()
            goal_dict['updated_at'] = goal_dict['updated_at'].isoformat()
            
            return success_response({'goal': goal_dict})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Failed to update goal: {str(e)}', 500)

def delete_goal(conn, user_id: int, goal_id: int) -> Dict[str, Any]:
    """Удаление цели"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем принадлежность цели пользователю и удаляем
            cur.execute('''
                DELETE FROM goals 
                WHERE id = %s AND user_id = %s
                RETURNING id
            ''', (goal_id, user_id))
            
            deleted_goal = cur.fetchone()
            if not deleted_goal:
                return error_response('Goal not found', 404)
            
            conn.commit()
            return success_response({'message': 'Goal deleted successfully', 'id': deleted_goal['id']})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Failed to delete goal: {str(e)}', 500)

def extract_user_id_from_cookies(event: Dict[str, Any]) -> Optional[int]:
    """Извлекает user_id из JWT токена в cookies"""
    try:
        import hashlib
        import hmac
        import base64
        import time
        
        headers = event.get('headers', {})
        cookies = headers.get('Cookie', '')
        
        if not cookies:
            return None
        
        # Извлекаем токен из cookies
        token = None
        for cookie in cookies.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('auth_token='):
                token = cookie.split('=', 1)[1]
                break
        
        if not token:
            return None
        
        # Проверяем JWT токен
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, signature_b64 = parts
        
        # Проверка подписи
        message = f'{header_b64}.{payload_b64}'
        expected_signature = hmac.new(
            os.environ.get('JWT_SECRET', 'default-secret').encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        # Добавляем отсутствующие символы '='
        signature_b64 += '=' * (4 - len(signature_b64) % 4)
        actual_signature = base64.urlsafe_b64decode(signature_b64)
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        
        # Декодирование payload
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        
        # Проверка срока действия
        if payload.get('exp', 0) < time.time():
            return None
        
        return payload.get('user_id')
        
    except Exception:
        return None

def success_response(data: Any) -> Dict[str, Any]:
    """Успешный ответ"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps(data, ensure_ascii=False),
        'isBase64Encoded': False
    }

def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Ответ с ошибкой"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        'body': json.dumps({'error': message}, ensure_ascii=False),
        'isBase64Encoded': False
    }