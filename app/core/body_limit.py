from starlette.responses import JSONResponse


class RequestBodyLimitMiddleware:
    """Bound request buffering before multipart parsing; no filename-based writes."""
    def __init__(self, app, max_bytes: int = 4 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        chunks=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':
                return
            body=message.get('body',b'')
            size+=len(body)
            if size>self.max_bytes:
                response=JSONResponse({'detail':'Request body exceeds 4 MiB'},status_code=413)
                return await response(scope,receive,send)
            chunks.append(body)
            if not message.get('more_body',False): break
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        await self.app(scope,replay,send)
