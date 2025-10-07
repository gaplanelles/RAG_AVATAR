from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.context import set_request_id
import uuid

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get conversation_id from request body if it exists
        if request.method == "POST":
            try:
                body = await request.json()
                conversation_id = body.get("conversation_id")
            except:
                conversation_id = None
        else:
            conversation_id = None
        
        # If no conversation_id, generate one
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Set the context
        set_request_id(conversation_id)
        
        response = await call_next(request)
        return response 