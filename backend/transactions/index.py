"""
Backend: Управление транзакциями с тегами
Args: event - HTTP запрос с методом, телом, заголовками, включая Authorization
      context - объект контекста с request_id
Returns: HTTP ответ с транзакциями, тегами или результатом операции
"""

import json
import os
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
import sys
sys.path.append('/opt')
from auth.index import verify_jwt_token

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    method: str = event.get('httpMethod', 'GET')
    
    # Handle CORS OPTIONS request
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    # Проверка авторизации
    auth_header = event.get('headers', {}).get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return error_response('Authorization required', 401)
    
    token = auth_header[7:]
    user_data = verify_jwt_token(token)
    if not user_data:
        return error_response('Invalid token', 401)
    
    user_id = user_data['user_id']
    
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        
        if method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            action = query_params.get('action', 'list')
            
            if action == 'list':
                return get_transactions(conn, user_id, query_params)
            elif action == 'tags':
                return get_tags(conn, user_id)
            elif action == 'statistics':
                return get_statistics(conn, user_id, query_params)
            else:
                return error_response('Invalid action', 400)
        
        elif method == 'POST':
            body_data = json.loads(event.get('body', '{}'))
            action = body_data.get('action')
            
            if action == 'create_transaction':
                return create_transaction(conn, user_id, body_data)
            elif action == 'create_tag':
                return create_tag(conn, user_id, body_data)
            else:
                return error_response('Invalid action', 400)
        
        elif method == 'PUT':
            body_data = json.loads(event.get('body', '{}'))
            transaction_id = body_data.get('id')
            return update_transaction(conn, user_id, transaction_id, body_data)
        
        elif method == 'DELETE':
            query_params = event.get('queryStringParameters') or {}
            transaction_id = query_params.get('id')
            if not transaction_id:
                return error_response('Transaction ID required', 400)
            return delete_transaction(conn, user_id, int(transaction_id))
        
        else:
            return error_response('Method not allowed', 405)
            
    except Exception as e:
        return error_response(f'Server error: {str(e)}', 500)
    finally:
        if 'conn' in locals():
            conn.close()

def get_transactions(conn, user_id: int, params: Dict[str, str]) -> Dict[str, Any]:
    """Получение списка транзакций с фильтрацией"""
    try:
        limit = int(params.get('limit', '50'))
        offset = int(params.get('offset', '0'))
        tag_filter = params.get('tag')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        transaction_type = params.get('type')  # income/expense
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Базовый запрос
            query = '''
                SELECT t.id, t.type, t.amount, t.category, t.description, t.date, t.created_at,
                       COALESCE(
                           json_agg(
                               json_build_object('id', tag.id, 'name', tag.name, 'color', tag.color)
                           ) FILTER (WHERE tag.id IS NOT NULL), 
                           '[]'::json
                       ) as tags
                FROM transactions t
                LEFT JOIN transaction_tags tt ON t.id = tt.transaction_id
                LEFT JOIN tags tag ON tt.tag_id = tag.id
                WHERE t.user_id = %s
            '''
            
            params_list = [user_id]
            
            # Добавление фильтров
            if tag_filter:
                query += ' AND tag.name = %s'
                params_list.append(tag_filter)
            
            if date_from:
                query += ' AND t.date >= %s'
                params_list.append(date_from)
            
            if date_to:
                query += ' AND t.date <= %s'
                params_list.append(date_to)
            
            if transaction_type:
                query += ' AND t.type = %s'
                params_list.append(transaction_type)
            
            query += '''
                GROUP BY t.id, t.type, t.amount, t.category, t.description, t.date, t.created_at
                ORDER BY t.date DESC, t.created_at DESC
                LIMIT %s OFFSET %s
            '''
            params_list.extend([limit, offset])
            
            cur.execute(query, params_list)
            transactions = cur.fetchall()
            
            # Преобразование в удобный формат
            result = []
            for trans in transactions:
                result.append({
                    'id': trans['id'],
                    'type': trans['type'],
                    'amount': float(trans['amount']),
                    'category': trans['category'],
                    'description': trans['description'],
                    'date': trans['date'].isoformat() if trans['date'] else None,
                    'tags': trans['tags'] if trans['tags'] else [],
                    'created_at': trans['created_at'].isoformat() if trans['created_at'] else None
                })
            
            return success_response({'transactions': result})
            
    except Exception as e:
        return error_response(f'Failed to get transactions: {str(e)}', 500)

def create_transaction(conn, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Создание новой транзакции"""
    try:
        transaction_type = data.get('type')
        amount = data.get('amount')
        category = data.get('category')
        description = data.get('description', '')
        date_str = data.get('date')
        tag_ids = data.get('tag_ids', [])
        
        if not all([transaction_type, amount, category, date_str]):
            return error_response('Required fields missing', 400)
        
        if transaction_type not in ['income', 'expense']:
            return error_response('Invalid transaction type', 400)
        
        try:
            amount = float(amount)
            transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return error_response('Invalid amount or date format', 400)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Создание транзакции
            cur.execute('''
                INSERT INTO transactions (user_id, type, amount, category, description, date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, type, amount, category, description, date, created_at
            ''', (user_id, transaction_type, amount, category, description, transaction_date))
            
            transaction = cur.fetchone()
            transaction_id = transaction['id']
            
            # Добавление тегов
            if tag_ids:
                for tag_id in tag_ids:
                    try:
                        cur.execute('''
                            INSERT INTO transaction_tags (transaction_id, tag_id)
                            VALUES (%s, %s)
                        ''', (transaction_id, int(tag_id)))
                    except (ValueError, psycopg2.Error):
                        pass  # Игнорируем некорректные теги
            
            conn.commit()
            
            # Получение тегов для ответа
            cur.execute('''
                SELECT tag.id, tag.name, tag.color
                FROM tags tag
                JOIN transaction_tags tt ON tag.id = tt.tag_id
                WHERE tt.transaction_id = %s
            ''', (transaction_id,))
            
            tags = [dict(row) for row in cur.fetchall()]
            
            result = {
                'id': transaction['id'],
                'type': transaction['type'],
                'amount': float(transaction['amount']),
                'category': transaction['category'],
                'description': transaction['description'],
                'date': transaction['date'].isoformat(),
                'tags': tags,
                'created_at': transaction['created_at'].isoformat()
            }
            
            return success_response({'transaction': result})
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return error_response(f'Failed to create transaction: {str(e)}', 500)

def update_transaction(conn, user_id: int, transaction_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Обновление транзакции"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверка владельца
            cur.execute('SELECT id FROM transactions WHERE id = %s AND user_id = %s', 
                       (transaction_id, user_id))
            if not cur.fetchone():
                return error_response('Transaction not found', 404)
            
            # Обновление полей
            update_fields = []
            params = []
            
            if 'amount' in data:
                update_fields.append('amount = %s')
                params.append(float(data['amount']))
            
            if 'category' in data:
                update_fields.append('category = %s')
                params.append(data['category'])
            
            if 'description' in data:
                update_fields.append('description = %s')
                params.append(data['description'])
            
            if 'date' in data:
                update_fields.append('date = %s')
                params.append(datetime.strptime(data['date'], '%Y-%m-%d').date())
            
            if update_fields:
                query = f'UPDATE transactions SET {", ".join(update_fields)} WHERE id = %s'
                params.append(transaction_id)
                cur.execute(query, params)
            
            # Обновление тегов
            if 'tag_ids' in data:
                # Удаление старых тегов
                cur.execute('DELETE FROM transaction_tags WHERE transaction_id = %s', (transaction_id,))
                
                # Добавление новых тегов
                for tag_id in data['tag_ids']:
                    try:
                        cur.execute('''
                            INSERT INTO transaction_tags (transaction_id, tag_id)
                            VALUES (%s, %s)
                        ''', (transaction_id, int(tag_id)))
                    except (ValueError, psycopg2.Error):
                        pass
            
            conn.commit()
            return success_response({'message': 'Transaction updated successfully'})
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return error_response(f'Failed to update transaction: {str(e)}', 500)

def delete_transaction(conn, user_id: int, transaction_id: int) -> Dict[str, Any]:
    """Удаление транзакции"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Проверка владельца и удаление
            cur.execute('''
                DELETE FROM transactions 
                WHERE id = %s AND user_id = %s
                RETURNING id
            ''', (transaction_id, user_id))
            
            if not cur.fetchone():
                return error_response('Transaction not found', 404)
            
            conn.commit()
            return success_response({'message': 'Transaction deleted successfully'})
            
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return error_response(f'Failed to delete transaction: {str(e)}', 500)

def get_tags(conn, user_id: int) -> Dict[str, Any]:
    """Получение тегов пользователя"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT id, name, color, created_at
                FROM tags 
                WHERE user_id = %s 
                ORDER BY name
            ''', (user_id,))
            
            tags = [dict(row) for row in cur.fetchall()]
            return success_response({'tags': tags})
            
    except Exception as e:
        return error_response(f'Failed to get tags: {str(e)}', 500)

def create_tag(conn, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Создание нового тега"""
    try:
        name = data.get('name', '').strip()
        color = data.get('color', '#3B82F6')
        
        if not name:
            return error_response('Tag name is required', 400)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                INSERT INTO tags (user_id, name, color)
                VALUES (%s, %s, %s)
                RETURNING id, name, color, created_at
            ''', (user_id, name, color))
            
            tag = cur.fetchone()
            conn.commit()
            
            result = {
                'id': tag['id'],
                'name': tag['name'],
                'color': tag['color'],
                'created_at': tag['created_at'].isoformat()
            }
            
            return success_response({'tag': result})
            
    except psycopg2.IntegrityError:
        conn.rollback()
        return error_response('Tag with this name already exists', 409)
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        return error_response(f'Failed to create tag: {str(e)}', 500)

def get_statistics(conn, user_id: int, params: Dict[str, str]) -> Dict[str, Any]:
    """Получение статистики по транзакциям"""
    try:
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Базовые условия
            where_conditions = ['user_id = %s']
            query_params = [user_id]
            
            if date_from:
                where_conditions.append('date >= %s')
                query_params.append(date_from)
            
            if date_to:
                where_conditions.append('date <= %s')
                query_params.append(date_to)
            
            where_clause = ' AND '.join(where_conditions)
            
            # Общая статистика
            cur.execute(f'''
                SELECT 
                    type,
                    SUM(amount) as total,
                    COUNT(*) as count
                FROM transactions 
                WHERE {where_clause}
                GROUP BY type
            ''', query_params)
            
            totals = {row['type']: {'total': float(row['total']), 'count': row['count']} 
                     for row in cur.fetchall()}
            
            # Статистика по категориям
            cur.execute(f'''
                SELECT 
                    category,
                    type,
                    SUM(amount) as total,
                    COUNT(*) as count
                FROM transactions 
                WHERE {where_clause}
                GROUP BY category, type
                ORDER BY total DESC
            ''', query_params)
            
            categories = [dict(row) for row in cur.fetchall()]
            
            # Статистика по тегам
            cur.execute(f'''
                SELECT 
                    tag.name,
                    tag.color,
                    SUM(t.amount) as total,
                    COUNT(t.id) as count
                FROM transactions t
                JOIN transaction_tags tt ON t.id = tt.transaction_id
                JOIN tags tag ON tt.tag_id = tag.id
                WHERE {where_clause}
                GROUP BY tag.id, tag.name, tag.color
                ORDER BY total DESC
            ''', query_params)
            
            tags_stats = [dict(row) for row in cur.fetchall()]
            
            result = {
                'totals': totals,
                'by_category': categories,
                'by_tags': tags_stats
            }
            
            return success_response({'statistics': result})
            
    except Exception as e:
        return error_response(f'Failed to get statistics: {str(e)}', 500)

def success_response(data: Any) -> Dict[str, Any]:
    """Успешный ответ"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(data, default=str),
        'isBase64Encoded': False
    }

def error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    """Ответ с ошибкой"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message}),
        'isBase64Encoded': False
    }