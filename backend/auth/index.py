"""
Backend: Система авторизации с JWT токенами
Args: event - HTTP запрос с методом, телом и заголовками
      context - объект контекста с request_id и метаданными
Returns: HTTP ответ с токенами или ошибкой
"""

import json
import os
import hashlib
import hmac
import base64
import time
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    method: str = event.get('httpMethod', 'POST')
    
    # Handle CORS OPTIONS request
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-User-Id, X-Auth-Token, Authorization, Cookie',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    conn = None
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        
        if method == 'POST':
            body_data = json.loads(event.get('body', '{}'))
            action = body_data.get('action')
            
            if action == 'register':
                return handle_register(conn, body_data)
            elif action == 'login':
                return handle_login(conn, body_data)
            elif action == 'reset_password':
                return handle_reset_password(conn, body_data)
            elif action == 'confirm_reset':
                return handle_confirm_reset(conn, body_data)
            else:
                return error_response('Invalid action', 400)
        
        elif method == 'GET':
            # Проверка токена в cookies
            headers = event.get('headers', {})
            cookies = headers.get('Cookie', '')
            token = extract_token_from_cookies(cookies)
            
            if token:
                user_data = verify_jwt_token(token)
                if user_data:
                    # Получаем полную информацию о пользователе
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute('''
                            SELECT id, email, first_name, last_name
                            FROM users WHERE id = %s
                        ''', (user_data['user_id'],))
                        
                        user = cur.fetchone()
                        if user:
                            return success_response({
                                'user': {
                                    'id': user['id'],
                                    'email': user['email'],
                                    'first_name': user['first_name'],
                                    'last_name': user['last_name']
                                },
                                'valid': True
                            })
            
            return error_response('Invalid token', 401)
        
        elif method == 'DELETE':
            # Выход из системы - очистка cookie
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': 'true',
                    'Set-Cookie': 'auth_token=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0'
                },
                'body': json.dumps({'message': 'Logged out successfully'}, ensure_ascii=False),
                'isBase64Encoded': False
            }
        
        else:
            return error_response('Method not allowed', 405)
            
    except Exception as e:
        return error_response(f'Server error: {str(e)}', 500)
    finally:
        if conn:
            conn.close()

def handle_register(conn, data: Dict[str, Any]) -> Dict[str, Any]:
    """Регистрация нового пользователя"""
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    
    if not email or not password:
        return error_response('Email and password are required', 400)
    
    if len(password) < 6:
        return error_response('Password must be at least 6 characters', 400)
    
    try:
        # Проверка существования пользователя
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                return error_response('User already exists', 409)
            
            # Хеширование пароля
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Создание пользователя
            cur.execute('''
                INSERT INTO users (email, password_hash, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, first_name, last_name, created_at
            ''', (email, password_hash, first_name, last_name))
            
            user = cur.fetchone()
            conn.commit()
            
            # Создание JWT токена
            token = create_jwt_token({
                'user_id': user['id'],
                'email': user['email']
            })
            
            return success_response({
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name']
                }
            })
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Registration failed: {str(e)}', 500)

def handle_login(conn, data: Dict[str, Any]) -> Dict[str, Any]:
    """Авторизация пользователя"""
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return error_response('Email and password are required', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT id, email, password_hash, first_name, last_name
                FROM users WHERE email = %s
            ''', (email,))
            
            user = cur.fetchone()
            if not user:
                return error_response('Invalid credentials', 401)
            
            # Проверка пароля
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return error_response('Invalid credentials', 401)
            
            # Создание JWT токена
            token = create_jwt_token({
                'user_id': user['id'],
                'email': user['email']
            })
            
            return success_response({
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name']
                }
            })
            
    except Exception as e:
        return error_response(f'Login failed: {str(e)}', 500)

def handle_reset_password(conn, data: Dict[str, Any]) -> Dict[str, Any]:
    """Отправка ссылки для сброса пароля"""
    email = data.get('email', '').lower().strip()
    
    if not email:
        return error_response('Email is required', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            
            if not user:
                # Возвращаем успех даже если пользователь не найден (безопасность)
                return success_response({'message': 'Reset email sent if account exists'})
            
            # Генерация токена сброса
            reset_token = secrets.token_urlsafe(32)
            expires_at = time.time() + 3600  # 1 час
            
            cur.execute('''
                UPDATE users 
                SET reset_token = %s, reset_token_expires = to_timestamp(%s)
                WHERE id = %s
            ''', (reset_token, expires_at, user['id']))
            conn.commit()
            
            # Отправка email (если настроены SMTP параметры)
            try:
                send_reset_email(email, reset_token)
            except Exception as email_error:
                print(f"Email sending failed: {email_error}")
                # Не возвращаем ошибку пользователю
            
            return success_response({'message': 'Reset email sent if account exists'})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Reset failed: {str(e)}', 500)

def handle_confirm_reset(conn, data: Dict[str, Any]) -> Dict[str, Any]:
    """Подтверждение сброса пароля"""
    token = data.get('token', '')
    new_password = data.get('password', '')
    
    if not token or not new_password:
        return error_response('Token and new password are required', 400)
    
    if len(new_password) < 6:
        return error_response('Password must be at least 6 characters', 400)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT id, email FROM users 
                WHERE reset_token = %s AND reset_token_expires > CURRENT_TIMESTAMP
            ''', (token,))
            
            user = cur.fetchone()
            if not user:
                return error_response('Invalid or expired token', 400)
            
            # Обновление пароля
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cur.execute('''
                UPDATE users 
                SET password_hash = %s, reset_token = NULL, reset_token_expires = NULL
                WHERE id = %s
            ''', (password_hash, user['id']))
            conn.commit()
            
            return success_response({'message': 'Password reset successful'})
            
    except Exception as e:
        conn.rollback()
        return error_response(f'Password reset failed: {str(e)}', 500)

def create_jwt_token(payload: Dict[str, Any]) -> str:
    """Создание JWT токена"""
    header = {
        'typ': 'JWT',
        'alg': 'HS256'
    }
    
    # Добавляем время истечения (7 дней)
    payload['exp'] = int(time.time()) + 7 * 24 * 3600
    payload['iat'] = int(time.time())
    
    # Кодирование в base64
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    
    # Создание подписи
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
        
        return payload
        
    except Exception:
        return None

def send_reset_email(email: str, reset_token: str):
    """Отправка email для сброса пароля"""
    if not all([os.environ.get('EMAIL_HOST'), os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASSWORD')]):
        raise Exception("Email configuration not set")
    
    smtp_server = os.environ['EMAIL_HOST']
    smtp_port = int(os.environ.get('EMAIL_PORT', '587'))
    sender_email = os.environ['EMAIL_USER']
    sender_password = os.environ['EMAIL_PASSWORD']
    
    # Создание письма
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = 'Сброс пароля - FinPlan'
    
    reset_url = f"https://your-domain.com/reset-password?token={reset_token}"
    
    body = f"""
    Здравствуйте!
    
    Вы запросили сброс пароля для вашего аккаунта в FinPlan.
    
    Перейдите по ссылке для создания нового пароля:
    {reset_url}
    
    Ссылка действительна в течение 1 часа.
    
    Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
    
    С уважением,
    Команда FinPlan
    """
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Отправка
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

def success_response_with_cookie(data: Any, token: str) -> Dict[str, Any]:
    """Успешный ответ с установкой cookie"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true',
            'Set-Cookie': f'auth_token={token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age={7*24*3600}'
        },
        'body': json.dumps(data, ensure_ascii=False),
        'isBase64Encoded': False
    }

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

def extract_token_from_cookies(cookie_header: str) -> Optional[str]:
    """Извлекает токен из заголовка Cookie"""
    if not cookie_header:
        return None
    
    cookies = cookie_header.split(';')
    for cookie in cookies:
        cookie = cookie.strip()
        if cookie.startswith('auth_token='):
            return cookie.split('=', 1)[1]
    
    return None

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