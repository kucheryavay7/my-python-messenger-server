"""
Сервер-ретранслятор для Python Мессенджера
Принимает сообщения от клиентов и пересылает их всем остальным
"""

import socketio
import uvicorn

# Создаём асинхронный сервер Socket.IO
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
app = socketio.ASGIApp(sio)

# Хранилище подключённых пользователей
# Формат: {sid: {"user": "никнейм"}}
connected_users = {}


# ===== ОБРАБОТЧИКИ СОБЫТИЙ =====

@sio.event
async def connect(sid, environ):
    """Клиент подключился"""
    print(f'✅ Клиент {sid} подключился')
    connected_users[sid] = {"user": None}


@sio.event
async def disconnect(sid):
    """Клиент отключился"""
    print(f'❌ Клиент {sid} отключился')

    # Если пользователь был авторизован, сообщаем всем что он ушёл
    if sid in connected_users and connected_users[sid]["user"]:
        username = connected_users[sid]["user"]
        del connected_users[sid]

        # Отправляем всем оставшимся обновлённый список
        await _broadcast_users_update()
        await sio.emit('left', {
            'msg': f'{username} покинул чат',
            'users': _get_users_list()
        })
    else:
        if sid in connected_users:
            del connected_users[sid]


@sio.event
async def join(sid, data):
    """Пользователь входит в чат"""
    username = data.get('user', 'Гость')
    connected_users[sid]["user"] = username

    print(f'👤 {username} вошёл в чат')

    # Отправляем приветствие самому пользователю
    await sio.emit('joined', {
        'msg': f'Ты вошёл как {username}',
        'users': _get_users_list()
    }, to=sid)

    # Сообщаем всем остальным о новом пользователе
    await sio.emit('message', {
        'user': 'СИСТЕМА',
        'msg': f'{username} присоединился к чату'
    }, skip_sid=sid)

    # Обновляем список пользователей у всех
    await _broadcast_users_update()


@sio.event
async def leave(sid, data):
    """Пользователь покидает чат"""
    if sid in connected_users:
        username = connected_users[sid]["user"]
        connected_users[sid]["user"] = None

        await _broadcast_users_update()
        await sio.emit('left', {
            'msg': f'{username} покинул чат',
            'users': _get_users_list()
        })


@sio.event
async def message(sid, data):
    """Получено новое сообщение"""
    if sid in connected_users and connected_users[sid]["user"]:
        username = connected_users[sid]["user"]
        text = data.get('msg', '')

        print(f'💬 {username}: {text}')

        # Отправляем сообщение ВСЕМ клиентам
        await sio.emit('message', {
            'user': username,
            'msg': text
        })


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def _get_users_list():
    """Возвращает список имён всех онлайн-пользователей"""
    users = []
    for sid, data in connected_users.items():
        if data["user"]:
            users.append(data["user"])
    return list(set(users))  # Убираем дубликаты


async def _broadcast_users_update():
    """Отправляет всем клиентам обновлённый список пользователей"""
    await sio.emit('users_update', {
        'users': _get_users_list()
    })


# ===== ЗАПУСК СЕРВЕРА =====
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 СЕРВЕР МЕССЕНДЖЕРА ЗАПУЩЕН")
    print("=" * 50)
    print("📍 Адрес: http://localhost:8000")
    print("💡 Нажми CTRL+C для остановки")
    print("=" * 50)

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )