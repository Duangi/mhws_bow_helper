import aiohttp
import asyncio
import os
import ssl
import certifi

class ImageDownloader:
    @staticmethod
    async def download(url, save_path):
        print(f"[INFO] 开始下载图片: {url}")
        # 增加 headers，兼容更多图片服务器
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': url  # 可根据需要调整
        }
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        print(f"[INFO] 创建 aiohttp 会话")
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            print(f"[INFO] 发送 GET 请求")
            async with session.get(url, headers=headers) as resp:
                print(f"[INFO] 响应状态: {resp.status}")
                resp.raise_for_status()
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                print(f"[INFO] 保存图片到: {save_path}")
                with open(save_path, 'wb') as f:
                    while True:
                        chunk = await resp.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                print(f"[INFO] 图片下载完成: {save_path}")

    @staticmethod
    async def download_image_by_url(
        url: str, post: bool = False, post_data: dict = None, path=None
    ) -> str:
        print(f"[INFO] 开始下载图片: {url}")
        def save_temp_img(content):
            import tempfile
            fd, temp_path = tempfile.mkstemp(suffix='.img')
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
            print(f"[INFO] 临时图片已保存: {temp_path}")
            return temp_path
        try:
            ssl_context = ssl.create_default_context(
                cafile=certifi.where()
            )
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            print(f"[INFO] 创建 aiohttp 会话")
            async with aiohttp.ClientSession(trust_env=True, connector=connector) as session:
                if post:
                    print(f"[INFO] 发送 POST 请求")
                    async with session.post(url, json=post_data) as resp:
                        print(f"[INFO] 响应状态: {resp.status}")
                        content = await resp.read()
                        if not path:
                            return save_temp_img(content)
                        else:
                            with open(path, "wb") as f:
                                f.write(content)
                            print(f"[INFO] 图片已保存: {path}")
                            return path
                else:
                    print(f"[INFO] 发送 GET 请求")
                    async with session.get(url) as resp:
                        print(f"[INFO] 响应状态: {resp.status}")
                        content = await resp.read()
                        if not path:
                            return save_temp_img(content)
                        else:
                            with open(path, "wb") as f:
                                f.write(content)
                            print(f"[INFO] 图片已保存: {path}")
                            return path
        except (aiohttp.ClientConnectorSSLError, aiohttp.ClientConnectorCertificateError):
            print(f"[WARN] SSL 证书错误，尝试关闭 SSL 验证")
            ssl_context = ssl.create_default_context()
            ssl_context.set_ciphers("DEFAULT")
            async with aiohttp.ClientSession() as session:
                if post:
                    print(f"[INFO] 发送 POST 请求 (SSL 关闭)")
                    async with session.post(url, json=post_data, ssl=ssl_context) as resp:
                        print(f"[INFO] 响应状态: {resp.status}")
                        content = await resp.read()
                        return save_temp_img(content)
                else:
                    print(f"[INFO] 发送 GET 请求 (SSL 关闭)")
                    async with session.get(url, ssl=ssl_context) as resp:
                        print(f"[INFO] 响应状态: {resp.status}")
                        content = await resp.read()
                        return save_temp_img(content)
        except Exception as e:
            print(f"[ERROR] 下载图片异常: {e}")
            raise e