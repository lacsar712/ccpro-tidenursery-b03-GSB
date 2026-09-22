# TideNursery-01 · 潮汐育苗台账

海水育苗场「塘口水质采样与投喂事件」台账种子项目（非库存 / 电商 / 医院）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2 · Pydantic v2 · python-jose · passlib(bcrypt) · uvicorn |
| 前端 | React 18 · Vite · TypeScript · React Router v6 |
| 数据库 | PostgreSQL 15 |
| 部署 | docker-compose · 前端 Nginx 反代 `/api` |

## 端口与账号

| 服务 | 端口 |
| --- | --- |
| 前端 | **3400** |
| 后端 API | **8400** |
| PostgreSQL | **5434** |

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 场长 |
| `technician` | `123456` | 水质技术员 |

## 一键启动

```bash
cd TideNursery-01
docker compose up --build
```

启动后访问：

- 前端：http://localhost:3400
- 后端健康检查：http://localhost:8400/api/health
- API 文档：http://localhost:8400/docs

后端 entrypoint 流程：等待数据库就绪 → `create_all` 建表 → seed 初始数据 → 启动 uvicorn。

## 功能模块

1. **Auth**：JWT 登录（OAuth2 Password），`/api/auth/login`、`/api/auth/me`
2. **Hatchery 育苗场**：`name`、`seawaterSource`、`notes`
3. **Pond 育苗塘**：`hatcheryId`、`pondCode`、`species`、`volumeM3`、`status(stocked|dry|quarantine)`；同场 `pondCode` 唯一
4. **WaterSample 水质样**：`pondId`、`sampledAt`、`tempC`、`salinityPpt`、`doMgL`、`ph`、`notes`；`doMgL > 0` 且 `ph ∈ [6,9]`，否则返回 **400**
5. **FeedEvent 投喂**：`pondId`、`fedAt`、`feedType`、`amountKg`、`operatorName`
6. **VolumeChangeRequest 塘口体积变更审批**：见下方「体积变更审批口径」
7. **Dashboard**：塘总数、quarantine 数、近 24h 采样数、近 7 日投喂总量 kg

## 前端页面

Login · Dashboard · Hatcheries · Ponds · WaterSamples · FeedEvents · 体积变更审批

## 体积变更审批口径

**塘口体积（volumeM3）不允许直接改库**，建档后只能通过「体积变更审批单」落地：

- **审批单字段**：所属塘口、原体积（申请时快照）、申请体积、理由、状态（`pending` 待审 / `approved` 通过 / `rejected` 驳回）、申请人、审批人（待审时为空）、审批意见（可选）、申请时间、审批时间。
- **申请校验**：申请体积必须为正数且与原体积不同；理由去空白后至少 6 个字，否则返回 **400**。
- **唯一待审**：同一塘口同时只允许一张待审单，重复申请返回 **409**（数据库有 `WHERE status='pending'` 部分唯一索引兜底）。
- **权限**：水质技术员（technician）发起申请；场长（admin）通过或驳回；越权返回 **403**。
- **通过**：在同一事务内把塘口 `volumeM3` 更新为申请体积，并记录审批人与审批时间。
- **驳回**：塘口体积不变，仅置审批单为驳回态。
- **终态锁定**：已通过/驳回的单子不可再改，重复审批返回 **409**。
- **直改封堵**：`PUT /api/ponds/{id}` 请求体若携带与现值不同的 `volumeM3`，直接返回 **403**，正文提示「塘口体积不可直接修改，请发起体积变更审批单……」；体积之外的字段（塘口号、品种、状态等）仍可正常编辑。
- **入口**：侧栏「体积变更审批」页可发起申请；塘页每行有「申请改体积」按钮，跳转时带 `pondId` 预选塘口。审批页支持按状态、塘口筛选；场长在待审单上看到「通过 / 驳回」按钮。
- **接口**：`GET/POST /api/volume-change-requests`（支持 `?status=&pondId=` 过滤）、`POST /api/volume-change-requests/{id}/approve`、`POST /api/volume-change-requests/{id}/reject`。
- **种子**：初始数据含一张待审单（A-01 塘口 80 → 95 m³，技术员申请）。

## 本地开发（可选）

```bash
# 数据库（或用 compose 只起 db）
docker compose up -d db

# 后端
cd backend
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://tidenursery:tidenursery@localhost:5434/tidenursery
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8400

# 前端
cd frontend
npm install
npm run dev
```

## 目录结构

```
TideNursery-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── auth.py
│       ├── seed.py
│       ├── models/
│       ├── schemas/
│       └── routers/
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── pages/
        ├── components/
        └── api/
```
