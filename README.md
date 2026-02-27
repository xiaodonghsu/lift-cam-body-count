# Lift-Cam-body-count 电梯摄像头人数检测系统

基于RTSP视频流的电梯人数检测与监控系统。通过抓取电梯摄像头画面，利用百度AI进行人体分析，实现电梯内人数实时检测与数据分发。

## 功能特性

- **多摄像头并发采集** - 支持同时抓取多个电梯摄像头的RTSP视频流
- **智能连接管理** - 图像连续相同5次时自动释放RTSP连接，节省网络资源
- **人体人数检测** - 使用百度AI人体分析API实时检测电梯内人数
- **多种数据分发** - 支持Redis Pub/Sub、ActiveMQ消息队列、云端存储
- **进程自愈机制** - 主控程序监控子进程状态，崩溃自动重启
- **双分辨率存储** - 同时保存原始分辨率和缩小版图像

## 项目结构

```
lift-cam/
├── main.py                                       # 主控程序
├── cam-capture.py  # 摄像头图像采集模块
├── person-detect.py                 # 人体检测分析模块
├── logging_config.py                             # 日志配置
├── lift_cams.json                                 # 摄像头配置文件
├── pyproject.toml                                 # 项目依赖配置
└── README.md
```

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Main Process                          │
│         (进程监控 & 自动重启 - main.py)                      │
└──────┬──────────────────────────────────────────┬───────────┘
       │                                          │
       ▼                                          ▼
┌──────────────────────────┐      ┌────────────────────────────┐
│   Camera Capture         │      │   Person Detection       │
│   (多线程抓取RTSP)        │      │   (多线程AI分析)          │
└──────┬───────────────────┘      └──────┬─────────────────────┘
       │                               │
       │  Redis Pub/Sub               │
       ├──────────────────────────────►│
       │   liftPersonImage             │
       │                               │
       │                               │
       │                        ┌──────▼────────────┐
       │                        │   Baidu AI API    │
       │                        │   (人体分析)       │
       │                        └──────┬────────────┘
       │                               │
       │                    ┌──────────┼──────────┐
       │                    ▼          ▼          ▼
       │              ┌─────────┐ ┌────────┐ ┌──────────┐
       │              │Redis    │ │ActiveMQ│ │  Cloud   │
       │              │Remote   │ │Queue   │ │  Cache   │
       │              └─────────┘ └────────┘ └──────────┘
```

## 环境要求

- Python >= 3.12
- Redis (本地和远程)
- ActiveMQ (可选)
- RTSP视频流摄像头

## 安装

```bash
# 使用 uv 安装依赖
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 依赖说明

- `baidu-aip` - 百度AI SDK
- `opencv-python` - 视频流处理
- `redis` - Redis客户端
- `stomp-py` - ActiveMQ客户端
- `psutil` - 进程管理
- `pillow` - 图像处理
- `chardet` - 编码检测

## 配置

### 1. 摄像头配置 (lift_cams.json)

```json
{
    "lift_1": "rtsp://admin:admin123@10.0.0.99:554",
    "lift_2": "rtsp://admin:admin123@10.0.0.239:554",
    "lift_3": "rtsp://admin:admin123@10.0.0.240:554",
    "lift_4": "rtsp://admin:admin123@10.0.0.98:554",
    "lift_5": "rtsp://admin:admin123@10.0.0.102:554"
}
```

### 2. Redis配置

修改.env以下文件中的Redis连接信息：

- LIFT_READER_IP : 电梯楼层检测服务IP
- LIFT_READER_REDIS_PORT : 电梯楼层检测服务端口

### 3. 百度AI配置

修改 `.env` 中的API密钥：

BAIDU_APP_ID = 'your_app_id'
BAIDU_API_KEY = 'your_api_key'
BAIDU_SECRET_KEY = 'your_secret_key'

### 4. ActiveMQ配置 (可选)

修改 `.env` 中的MQ连接信息：

MQ_IP = 'messge_queue_ip'
MQ_PORT = 61613
MQ_USER = 'admin'
MQ_PASS = 'admin'
MQ_CHANNEL = '/queue/lift_cam_frame'

## 运行

```bash
# 运行主程序
uv run main.py
```

## 运行机制

### 主控程序 (main.py)

- 启动两个子进程：`cam-capture` 和 `person_detect`
- 每10秒检查一次进程状态
- 自动重启崩溃的进程

### 摄像头采集模块

- 每个摄像头独立线程采集
- 采集周期：2秒
- 连续5帧相同图像时释放RTSP连接
- 通过Redis Pub/Sub发布图像数据

### 人体检测模块

- 订阅Redis消息队列
- 使用百度AI检测人数
- 结果分发到：
  - 远程Redis（3秒过期）
  - 云端缓存
  - ActiveMQ消息队列

## 日志

日志文件位于 `log/` 目录：

- `app.log` - 主控程序日志
- `app_cap.log` - 摄像头采集日志
- `app_det.log` - 人体检测日志

## Redis数据结构

| Key | 类型 | 说明 |
|-----|------|------|
| `liftPersonImage` | Channel | 图像发布/订阅频道 |
| `{camera_name}` | Hash | 临时存储图像数据 (2秒过期) |
| `LiftPerson_{camera}` | String | 人数检测结果 (3秒过期) |

## 注意事项

1. **RTSP连接稳定性** - 网络波动可能导致连接中断，程序会自动重连
2. **API配额限制** - 百度AI有调用频率限制，需合理设置采集周期
3. **敏感信息** - 配置文件中包含密码和API密钥，请妥善保管
4. **资源占用** - 多摄像头并发采集会占用较大带宽和CPU资源

## 许可证

MIT License
