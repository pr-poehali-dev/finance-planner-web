"""
Backend: Управление календарными событиями пользователя
Args: event - HTTP запрос с методом, телом и заголовками
      context - объект контекста с request_id и метаданными
Returns: HTTP ответ с событиями календаря или ошибкой
"""

import json
import os
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date

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
            return get_events(conn, user_id, event)
        elif method == 'POST':
            body_data = json.loads(event.get('body', '{}'))
            return create_event(conn, user_id, body_data)
        elif method == 'PUT':
            body_data = json.loads(event.get('body', '{}'))
            return update_event(conn, user_id, body_data)
        elif method == 'DELETE':
            params = event.get('queryStringParameters', {}) or {}
            event_id = params.get('id')
            if not event_id:
                return error_response('Event ID is required', 400)
            return delete_event(conn, user_id, int(event_id))
        else:
            return error_response('Method not allowed', 405)
            
    except Exception as e:
        return error_response(f'Server error: {str(e)}', 500)
    finally:
        if conn:
            conn.close()

def get_events(conn, user_id: int, event: Dict[str, Any]) -> Dict[str, Any]:
    """Получение календарных событий пользователя"""
    try:
        params = event.get('queryStringParameters', {}) or {}
        start_date = params.get('start')
        end_date = params.get('end')
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where_clause = 'WHERE user_id = %s'
            query_params = [user_id]
            
            if start_date:
                where_clause += ' AND start_date >= %s'
                query_params.append(start_date)
            
            if end_date:
                where_clause += ' AND start_date <= %s'
                query_params.append(end_date)
            
            query = f'''
                SELECT id, title, description, start_date, end_date, 
                       all_day, color, created_at, updated_at
                FROM calendar_events 
                {where_clause}
                ORDER BY start_date ASC
            '''
            
            cur.execute(query, query_params)
            events = cur.fetchall()
            
            # Преобразуем даты в строки для JSON и FullCalendar формат
            events_list = []
            for cal_event in events:
                event_dict = {
                    'id': cal_event['id'],
                    'title': cal_event['title'],
                    'description': cal_event['description'],
                    'start': cal_event['start_date'].isoformat() if cal_event['start_date'] else None,
                    'end': cal_event['end_date'].isoformat() if cal_event['end_date'] else None,
                    'allDay': cal_event['all_day'],
                    'backgroundColor': cal_event['color'],
                    'borderColor': cal_event['color'],
                    'created_at': cal_event['created_at'].isoformat(),
                    'updated_at': cal_event['updated_at'].isoformat()
                }
                events_list.append(event_dict)
            
            return success_response({'events': events_list})
            
    except Exception as e:
        return error_response(f'Failed to get events: {str(e)}', 500)

def create_event(conn, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Создание нового события"""
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    start_date = data.get('start_date') or data.get('start')
    end_date = data.get('end_date') or data.get('end')
    all_day = data.get('all_day', False) or data.get('allDay', False)
    color = data.get('color', '#3B82F6')
    
    if not title:
        return error_response('Title is required', 400)
    
    if not start_date:
        return error_response('Start date is required', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO calendar_events (user_id, title, description, start_date, 
                                           end_date, all_day, color)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, title, description, start_date, end_date, 
                          all_day, color, created_at, updated_at
            ''', (user_id, title, description, start_date, end_date, all_day, color))
            
            cal_event = cur.fetchone()
            conn.commit()
            
            # Преобразуем для FullCalendar формата
            event_dict = {
                'id': cal_event['id'],
                'title': cal_event['title'],
                'description': cal_event['description'],
                'start': cal_event['start_date'].isoformat() if cal_event['start_date'] else None,
                'end': cal_event['end_date'].isoformat() if cal_event['end_date'] else None,
                'allDay': cal_event['all_day'],
                'backgroundColor': cal_event['color'],
                'borderColor': cal_event['color'],
                'created_at': cal_event['created_at'].isoformat(),
                'updated_at': cal_event['updated_at'].isoformat()
            }
            
            return success_response({'event': event_dict})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Failed to create event: {str(e)}', 500)

def update_event(conn, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Обновление события"""
    event_id = data.get('id')
    if not event_id:
        return error_response('Event ID is required', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем принадлежность события пользователю
            cur.execute('SELECT id FROM calendar_events WHERE id = %s AND user_id = %s', (event_id, user_id))
            if not cur.fetchone():
                return error_response('Event not found', 404)
            
            # Обновляем поля
            update_fields = []
            params = []
            
            if 'title' in data:
                update_fields.append('title = %s')
                params.append(data['title'].strip())
            
            if 'description' in data:
                update_fields.append('description = %s')
                params.append(data['description'].strip())
            
            if 'start_date' in data or 'start' in data:
                start_date = data.get('start_date') or data.get('start')
                update_fields.append('start_date = %s')
                params.append(start_date)
            
            if 'end_date' in data or 'end' in data:
                end_date = data.get('end_date') or data.get('end')
                update_fields.append('end_date = %s')
                params.append(end_date)
            
            if 'all_day' in data or 'allDay' in data:
                all_day = data.get('all_day', data.get('allDay'))
                update_fields.append('all_day = %s')
                params.append(all_day)
            
            if 'color' in data or 'backgroundColor' in data:
                color = data.get('color', data.get('backgroundColor'))
                update_fields.append('color = %s')
                params.append(color)
            
            if not update_fields:
                return error_response('No fields to update', 400)
            
            update_fields.append('updated_at = CURRENT_TIMESTAMP')
            params.extend([event_id, user_id])
            
            query = f'''
                UPDATE calendar_events 
                SET {', '.join(update_fields)}
                WHERE id = %s AND user_id = %s
                RETURNING id, title, description, start_date, end_date, 
                          all_day, color, created_at, updated_at
            '''
            
            cur.execute(query, params)
            cal_event = cur.fetchone()
            conn.commit()
            
            # Преобразуем для FullCalendar формата
            event_dict = {
                'id': cal_event['id'],
                'title': cal_event['title'],
                'description': cal_event['description'],
                'start': cal_event['start_date'].isoformat() if cal_event['start_date'] else None,
                'end': cal_event['end_date'].isoformat() if cal_event['end_date'] else None,
                'allDay': cal_event['all_day'],
                'backgroundColor': cal_event['color'],
                'borderColor': cal_event['color'],
                'created_at': cal_event['created_at'].isoformat(),
                'updated_at': cal_event['updated_at'].isoformat()
            }
            
            return success_response({'event': event_dict})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Failed to update event: {str(e)}', 500)

def delete_event(conn, user_id: int, event_id: int) -> Dict[str, Any]:
    """Удаление события"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверяем принадлежность события пользователю и удаляем
            cur.execute('''
                DELETE FROM calendar_events 
                WHERE id = %s AND user_id = %s
                RETURNING id
            ''', (event_id, user_id))
            
            deleted_event = cur.fetchone()
            if not deleted_event:
                return error_response('Event not found', 404)
            
            conn.commit()
            return success_response({'message': 'Event deleted successfully', 'id': deleted_event['id']})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Failed to delete event: {str(e)}', 500)

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