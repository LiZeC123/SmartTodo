from typing import Dict

from flask import Blueprint, request, Response

from app import llm_manager

llm_bp = Blueprint('llm', __name__)


@llm_bp.post('/api/llm/stream')
def chat_stream():
    f: Dict = request.get_json()
    prompt = f.get('prompt', '')
    
    return Response(
        llm_manager.generate_stream(prompt),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用Nginx缓冲
        }
    )