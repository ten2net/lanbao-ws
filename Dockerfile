# 揽宝智能投研交易平台 - Docker镜像
FROM ros:humble-ros-base-jammy

# 设置工作目录
WORKDIR /workspace

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    python3-rosdep \
    git \
    wget \
    curl \
    vim \
    nano \
    htop \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt /workspace/
RUN pip3 install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 创建工作目录
RUN mkdir -p /workspace/src /workspace/data /workspace/logs /workspace/config

# 复制项目代码
COPY src/ /workspace/src/
COPY config/ /workspace/config/
COPY notebooks/ /workspace/notebooks/
COPY scripts/ /workspace/scripts/

# 设置环境变量
ENV PYTHONPATH="/workspace/src:/opt/ros/humble/lib/python3.10/site-packages:/opt/ros/humble/local/lib/python3.10/dist-packages"
ENV ROS_DOMAIN_ID=0
ENV LANBAO_LOG_LEVEL=INFO

# 构建ROS2包
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    cd /workspace && \
    colcon build --packages-select lanbao_interfaces lanbao_core lanbao_data lanbao_strategy lanbao_backtest lanbao_risk lanbao_monitor"

# 复制启动脚本
COPY entrypoint.sh /workspace/entrypoint.sh
RUN chmod +x /workspace/entrypoint.sh

# 暴露端口
# 8888 - Jupyter, 8501 - Streamlit
EXPOSE 8888
EXPOSE 8501

# 入口点
ENTRYPOINT ["/workspace/entrypoint.sh"]
CMD ["/bin/bash"]
