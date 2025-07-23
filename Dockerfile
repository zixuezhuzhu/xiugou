# 基础镜像，选择合适的 Python 版本，这里以 Python 3.9 为例
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple  # 使用清华镜像加速安装

# 复制项目其他文件到工作目录
COPY . .

# 暴露端口，要和云托管配置的端口一致，这里假设你云托管配置的是 80，若实际应用监听端口不同（比如 Django 默认 8000 ），需修改
EXPOSE 80

# 启动命令，启动 Django 项目（根据实际框架和启动方式调整，若不是 Django ，替换成对应框架的启动命令）
CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]
