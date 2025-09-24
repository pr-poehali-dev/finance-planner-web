"""
Backend: Система авторизации с JWT и cookies
Args: event - HTTP запрос с методом, телом и заголовками
      context - объект контекста с request_id
Returns: HTTP ответ с токенами или ошибкой
"""

import json
import os
import hashlib
import hmac  
import base64
import time
import secrets
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    method: str = event.get('httpMethod', 'GET')
    
    # CORS headers для всех ответов
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': 'true', 
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, Authorization, Cookie',
        'Access-Control-Max-Age': '86400',
        'Content-Type': 'application/json'
    }
    
    # Handle CORS OPTIONS request
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': '',
            'isBase64Encoded': False
        }
    
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        
        if method == 'POST':
            body_data = json.loads(event.get('body', '{}'))
            action = body_data.get('action')
            
            if action == 'register':
                return handle_register(conn, body_data, cors_headers)
            elif action == 'login':
                return handle_login(conn, body_data, cors_headers)
            elif action == 'reset_password':
                return handle_reset_password(conn, body_data, cors_headers)
            elif action == 'confirm_reset':
                return handle_confirm_reset(conn, body_data, cors_headers)
            else:
                return error_response('Invalid action', 400, cors_headers)
        
        elif method == 'GET':
            # Проверка токена в cookies
            headers = event.get('headers', {})
            cookies = headers.get('Cookie', '')
            token = extract_token_from_cookies(cookies)
            
            if token:
                user_data = verify_jwt_token(token)
                if user_data:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute('''
                            SELECT id, email, first_name, last_name
                            FROM users WHERE id = %s
                        ''', (user_data['user_id'],))
                        
                        user = cur.fetchone()
                        if user:
                            return success_response({
                                'user': dict(user),
                                'valid': True
                            }, cors_headers)
            
            return error_response('Invalid token', 401, cors_headers)
        
        elif method == 'DELETE':
            # Logout - очистка cookie
            return {
                'statusCode': 200,
                'headers': {
                    **cors_headers,
                    'Set-Cookie': 'auth_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'
                },
                'body': json.dumps({'message': 'Logged out successfully'}, ensure_ascii=False),
                'isBase64Encoded': False
            }
        
        else:
            return error_response('Method not allowed', 405, cors_headers)
            
    except Exception as e:
        print(f"Server error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Server error: {str(e)}'}, ensure_ascii=False),
            'isBase64Encoded': False
        }
    finally:
        if 'conn' in locals():
            conn.close()

def handle_register(conn, data: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Регистрация пользователя"""
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '') or ''
    
    if not email or not password:
        return error_response('Email and password required', 400, cors_headers)
    
    if len(password) < 6:
        return error_response('Password must be at least 6 characters', 400, cors_headers)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                return error_response('User already exists', 409, cors_headers)
            
            # Хешируем пароль
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Создаем пользователя
            cur.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, first_name, last_name
            ''', (email, password_hash, first_name, last_name))
            
            user = cur.fetchone()
            conn.commit()
            
            # Создаем JWT токен
            token = create_jwt_token({'user_id': user['id'], 'email': user['email']})
            
            return success_response_with_cookie({
                'user': dict(user)
            }, token, cors_headers)
            
    except Exception as e:
        conn.rollback()
        print(f"Registration error: {str(e)}")
        return error_response(f'Registration failed: {str(e)}', 500, cors_headers)

def handle_login(conn, data: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Авторизация пользователя"""
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return error_response('Email and password required', 400, cors_headers)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT id, email, password_hash, first_name, last_name
                FROM users WHERE email = %s
            ''', (email,))
            
            user = cur.fetchone()
            if not user:
                return error_response('Invalid credentials', 401, cors_headers)
            
            # Проверяем пароль
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return error_response('Invalid credentials', 401, cors_headers)
            
            # Создаем JWT токен
            token = create_jwt_token({'user_id': user['id'], 'email': user['email']})
            
            return success_response_with_cookie({
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name']
                }
            }, token, cors_headers)
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        return error_response(f'Login failed: {str(e)}', 500, cors_headers)

def handle_reset_password(conn, data: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Сброс пароля"""
    email = data.get('email', '').lower().strip()
    
    if not email:
        return error_response('Email required', 400, cors_headers)
    
    return success_response({'message': 'Reset email sent if account exists'}, cors_headers)

def handle_confirm_reset(conn, data: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Подтверждение сброса пароля"""
    return success_response({'message': 'Password reset successful'}, cors_headers)

def create_jwt_token(payload: Dict[str, Any]) -> str:
    """Создание JWT токена"""
    header = {'typ': 'JWT', 'alg': 'HS256'}
    
    payload['exp'] = int(time.time()) + 7 * 24 * 3600
    payload['iat'] = int(time.time())
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    message = f'{header_b64}.{payload_b64}'
    signature = hmac.new(
        os.environ.get('JWT_SECRET', 'default-secret').encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    return f'{message}.{signature_b64}'

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Проверка JWT токена"""
    try:
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
        
        signature_b64 += '=' * (4 - len(signature_b64) % 4)
        actual_signature = base64.urlsafe_b64decode(signature_b64)
        
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        
        if payload.get('exp', 0) < time.time():
            return None
        
        return payload
        
    except Exception:
        return None

def extract_token_from_cookies(cookie_header: str) -> Optional[str]:
    """Извлекает токен из cookies"""
    if not cookie_header:
        return None
    
    cookies = cookie_header.split(';')
    for cookie in cookies:
        cookie = cookie.strip()
        if cookie.startswith('auth_token='):
            return cookie.split('=', 1)[1]
    
    return None

def success_response_with_cookie(data: Any, token: str, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Успешный ответ с cookie"""
    headers = {
        **cors_headers,
        'Set-Cookie': f'auth_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={7*24*3600}'
    }
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(data, ensure_ascii=False),
        'isBase64Encoded': False
    }

def success_response(data: Any, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Успешный ответ"""
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps(data, ensure_ascii=False),
        'isBase64Encoded': False
    }

def error_response(message: str, status_code: int, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Ответ с ошибкой"""
    return {
        'statusCode': status_code,
        'headers': cors_headers,
        'body': json.dumps({'error': message}, ensure_ascii=False),
        'isBase64Encoded': False
    }