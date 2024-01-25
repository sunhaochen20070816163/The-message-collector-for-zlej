# zlej-
集中器api
ws://127.0.0.1:32500/ws?location={your-location}
http://127.0.0.1:32500/send?location={your-location}&username={username}&content={content}
wsapi方法(json)
发送{username,content}
接收{location,username,content}
httpapi例子
http://127.0.0.1:32500/send?location=webtest&username=zlej&content=Hello
ws例子
发送{"username": "zlej", "content": "Hello"}
接收{"location": "web", "username": "UserA", "content": "Hi"}
