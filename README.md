# 宁夏文旅 AI · 后端

FastAPI 服务：景区数据来自 MySQL `ningxia_tourism.scenic_spots`，AI 问答走 DeepSeek。

## 目录

```
backend/
├─ app/
│  ├─ config.py          # 读取 .env（DeepSeek Key）
│  ├─ db.py              # SQLAlchemy 连接 MySQL
│  ├─ models.py          # ScenicSpot 模型
│  ├─ schemas.py         # 响应模型
│  ├─ main.py            # 启动、CORS、挂路由
│  ├─ routers/
│  │  ├─ scenic.py       # 景区接口（已实现）
│  │  └─ chat.py 等      # 空文件，写好内容会自动挂载
│  └─ services/
│     └─ ai_service.py   # DeepSeek 调用
├─ .env                  # DEEPSEEK_API_KEY / DATABASE_URL
└─ venv/                 # 已建好的虚拟环境
```

## 启动

```powershell
cd D:\Ningxia-Tourism\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

打开 http://127.0.0.1:8000/docs

## 环境变量（.env）

```
DEEPSEEK_API_KEY=sk-xxxx
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/ningxia_tourism?charset=utf8mb4
```

`DATABASE_URL` 不填时默认 `root:123456@127.0.0.1:3306/ningxia_tourism`。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/scenic` | 列表，支持 `city` / `level` / `keyword` / `page` / `size` |
| GET | `/api/scenic/{id}` | 详情 |
| GET | `/api/scenic/stats` | 总数、有地址数、按等级 / 按城市统计 |
| GET | `/health` | 健康检查 |

## 后续扩展

`app/routers/chat.py` 里放一个 `router = APIRouter()` 和问答接口，
`main.py` 会自动把它挂到 `/api/chat`，不用改启动代码。
