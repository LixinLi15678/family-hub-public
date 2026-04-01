"""
Socket.io event handlers for real-time communication
"""
import socketio
from jose import JWTError, jwt

from app.config import settings

# Create Socket.io server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS,
    logger=settings.DEBUG,
    engineio_logger=settings.DEBUG
)


def verify_socket_token(token: str) -> dict:
    """Verify JWT token for socket connection"""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# Store user-to-socket mapping
user_sockets = {}  # user_id -> set of sids


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    if not auth or 'token' not in auth:
        print(f"Connection rejected: No auth token for {sid}")
        return False
    
    payload = verify_socket_token(auth['token'])
    if not payload:
        print(f"Connection rejected: Invalid token for {sid}")
        return False
    
    user_id = payload.get('user_id')
    
    # Store user-socket mapping
    if user_id not in user_sockets:
        user_sockets[user_id] = set()
    user_sockets[user_id].add(sid)
    
    # Store user info in session (family_id will be set when client calls join_family)
    await sio.save_session(sid, {
        'user_id': user_id,
        'family_id': None  # Will be set by join_family event
    })
    
    print(f"Client connected: {sid}, user: {user_id}")
    return True


@sio.event
async def join_family(sid, data):
    """
    Client calls this after connection to join their family room.
    data: { family_id: number }
    """
    session = await sio.get_session(sid)
    if not session:
        return
    
    family_id = data.get('family_id')
    if family_id:
        # Leave previous family room if any
        old_family_id = session.get('family_id')
        if old_family_id:
            await sio.leave_room(sid, f"family_{old_family_id}")
        
        # Join new family room
        await sio.enter_room(sid, f"family_{family_id}")
        
        # Update session
        session['family_id'] = family_id
        await sio.save_session(sid, session)
        
        print(f"User {session['user_id']} joined family_{family_id}")
        
        # Acknowledge
        await sio.emit('family:joined', {'family_id': family_id}, to=sid)


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    session = await sio.get_session(sid)
    if session:
        user_id = session.get('user_id')
        if user_id and user_id in user_sockets:
            user_sockets[user_id].discard(sid)
            if not user_sockets[user_id]:
                del user_sockets[user_id]
    
    print(f"Client disconnected: {sid}")


# ============== Shopping Events ==============

@sio.event
async def shopping_item_added(sid, data):
    """Broadcast when a shopping item is added"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'shopping:item_added',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def shopping_item_updated(sid, data):
    """Broadcast when a shopping item is updated"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'shopping:item_updated',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def shopping_item_checked(sid, data):
    """Broadcast when a shopping item is checked/unchecked"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'shopping:item_checked',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def shopping_item_deleted(sid, data):
    """Broadcast when a shopping item is deleted"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'shopping:item_deleted',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


# ============== Expense Events ==============

@sio.event
async def expense_created(sid, data):
    """Broadcast when an expense is created"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'expense:created',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def expense_updated(sid, data):
    """Broadcast when an expense is updated"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'expense:updated',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def expense_deleted(sid, data):
    """Broadcast when an expense is deleted"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'expense:deleted',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


# ============== Chore Events ==============

@sio.event
async def chore_created(sid, data):
    """Broadcast when a chore is created"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'chore:created',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def chore_completed(sid, data):
    """Broadcast when a chore is completed"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'chore:completed',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def chore_updated(sid, data):
    """Broadcast when a chore is updated"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'chore:updated',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


# ============== Points Events ==============

@sio.event
async def points_updated(sid, data):
    """Broadcast when points are updated"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'points:updated',
            data,
            room=f"family_{session['family_id']}"
        )


@sio.event
async def product_purchased(sid, data):
    """Broadcast when a product is purchased"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'product:purchased',
            data,
            room=f"family_{session['family_id']}"
        )


# ============== Trip Events ==============

@sio.event
async def trip_created(sid, data):
    """Broadcast when a trip is created"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'trip:created',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def trip_updated(sid, data):
    """Broadcast when a trip is updated"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'trip:updated',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def trip_deleted(sid, data):
    """Broadcast when a trip is deleted"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'trip:deleted',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def trip_expense_added(sid, data):
    """Broadcast when a trip expense is added"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'trip:expense_added',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def trip_budget_added(sid, data):
    """Broadcast when a trip budget is added"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'trip:budget_added',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


@sio.event
async def trip_budget_updated(sid, data):
    """Broadcast when a trip budget is updated"""
    session = await sio.get_session(sid)
    if session and session.get('family_id'):
        await sio.emit(
            'trip:budget_updated',
            data,
            room=f"family_{session['family_id']}",
            skip_sid=sid
        )


# ============== Sync Events ==============

@sio.event
async def sync_request(sid, data):
    """Handle full sync request"""
    session = await sio.get_session(sid)
    if session:
        # Client requests full data sync
        # Response would contain all relevant data for the family
        await sio.emit(
            'sync:response',
            {'status': 'pending', 'message': 'Sync request received'},
            to=sid
        )


# Helper function to emit events from API handlers
async def emit_to_family(family_id: int, event: str, data: dict):
    """Emit an event to all members of a family"""
    await sio.emit(event, data, room=f"family_{family_id}")


async def emit_to_user(user_id: int, event: str, data: dict):
    """Emit an event to a specific user"""
    if user_id in user_sockets:
        for sid in user_sockets[user_id]:
            await sio.emit(event, data, to=sid)


# Trip-specific emit helper
async def emit_trip_event(event: str, data: dict, family_id: int):
    """
    广播旅行事件到家庭房间
    
    Events:
    - trip:created - 创建旅行
    - trip:updated - 更新旅行
    - trip:deleted - 删除旅行
    - trip:expense_added - 添加旅行支出
    - trip:budget_added - 添加预算分类
    - trip:budget_updated - 更新预算分类
    """
    await sio.emit(f"trip:{event}", data, room=f"family_{family_id}")


def register_socket_handlers():
    """Register any additional socket handlers - called on startup"""
    print("Socket.io handlers registered")

