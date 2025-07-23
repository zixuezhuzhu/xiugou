# 用 Python 3.9 环境
FROM python:3.9-slim

# 设定工作目录为 /app（代码会放在这里）
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制所有项目文件到 /app
COPY . .

# 暴露 80 端口（和云托管配置一致）
EXPOSE 80

# 启动 Django 项目
CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]
