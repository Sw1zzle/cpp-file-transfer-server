# Socket
# 服务端：创建 socket → bind → listen → accept → 接收 → 回传
# 客户端：                         连接 → 发送 → 接收

# 接收请求头 → 读取长度 → 补收正文 → 选择响应 → 发送
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 8080))
    server.listen()

    print("等待客户端连接……", flush=True)

    while True:
        # 接受tcp连接
        conn, addr = server.accept()
        with conn:
            print("客户端已连接：", addr)
            #充当接收缓冲区（receive buffer）：暂存每次收到的字节。
            # request = b""       # 初始为空
            # request += data     # 把新收到的字节追加进去
            request = b""

            #未出现\r\n\r\n,继续接受正文
            while b"\r\n\r\n" not in request:
                data = conn.recv(1024)

                if data == b"":
                    break

                request += data

            #已出现\r\n\r\n，请求头已收齐。正文不一定收齐
            if b"\r\n\r\n" in request:
                print("收到请求：", request)
                request_headers, request_body = request.split(b"\r\n\r\n", 1)
                first_line = request_headers.split(b"\r\n", 1)[0]
                method = first_line.split()[0]
                path = first_line.split()[1]

                print("请求头：", request_headers)
                print("已收到的正文：", request_body)

                content_length = 0
                has_content_length = False

                try:
                    for line in request_headers.split(b"\r\n"):
                        if line.startswith(b"Content-Length:"):
                            has_content_length = True
                            content_length = int(line.split(b":", 1)[1].strip())
                    if content_length < 0:
                        raise ValueError("正文长度不能为负数")

                except ValueError:
                    conn.sendall(
                        b"HTTP/1.1 400 Bad Request\r\n"
                        b"Content-Length: 0\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                    )
                    continue
                if method == b"POST" and path == b"/echo" and not has_content_length:
                    conn.sendall(
                        b"HTTP/1.1 411 Length Required\r\n"
                        b"Content-Length: 0\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                    )
                    continue    

                print("正文预期字节数：", content_length)
                print("正文已收字节数：", len(request_body))

                request_body = request_body[:content_length]

                # 正文没接收完整的情况
                while len(request_body) < content_length:
                    remaining = content_length - len(request_body)
                    print("正文还差", remaining, "字节，等待接收……", flush=True)

                    data = conn.recv(remaining)

                    if data == b"":
                        break

                    print("本次补收到：", data, flush=True)
                    request_body += data

                if len(request_body) < content_length:
                    print("客户端提前断开，正文未收齐")
                    continue

                print("完整正文：", request_body)

                if path == b"/isActive":
                    status = b"200 OK"
                    body = b"ok"
                elif method == b"POST" and path == b"/echo":
                    status = b"200 OK"
                    body = request_body
                else:
                    status = b"404 Not Found"
                    body = b"not found"

                response = (
                    b"HTTP/1.1 " + status + b"\r\n"
                    b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    + body
                )

                conn.sendall(response)