# GeoView / Miner 开发规范

## 交付范围与边界

- 交付主线为 `backend/`、`miner/`、`docker/` 与部署文档；旧 `frontend/` 仅在任务直接涉及时修改。
- 系统面向单管理员内网部署，不新增多用户、角色、云存储、任务队列或模型升级能力。
- 导出、备份、ROI 上传和推理产物只能写入服务端配置的受控根目录，并按项目或任务标识分目录。

## 代码与接口

- Python 使用 4 空格、显式异常处理和单一职责函数；新增或修改的文件使用 Ruff 检查与格式化。
- Miner 使用 ES Module、单引号、分号和 `<script setup>`；组件使用 PascalCase，变量和函数使用 camelCase。
- 所有 FID 必须是正整数。文件名只能是 basename，且必须符合接口允许的后缀；客户端不得提交绝对路径或 `..` 路径。ROI 推理仅接受受控数据根目录中的 TIF/KML 文件名。
- 项目导出和备份由服务端生成固定路径；`output_dir` 不再是可用参数，传入非空值返回 400。

## 配置与安全

- 密钥只通过未跟踪的 `.env` 或部署环境传入；`.env.example` 仅含占位符，禁止提交真实凭据。
- 对历史上已跟踪的环境文件，执行 `git rm --cached .env` 后保留本地文件，避免删除本机部署配置。
- Compose 默认不发布 MySQL 端口。容器部署只使用容器内路径；Windows 本地路径只可作为开发回退。
- Shell 脚本必须使用 `set -euo pipefail`，变量必须双引号包裹，并在失败时说明下一步操作。
- 独立 MySQL 初始化使用 SQL 字面量创建账号；`MYSQL_ROOT_PASSWORD`、`MYSQL_PASSWORD` 与 `MYSQL_USERNAME` 不得包含单引号或反斜杠，避免初始化失败或注入风险。

## 本地质量门禁

在提交前运行以下命令。格式化命令仅覆盖本次纳入交付的 Miner 文件，避免覆盖未审查的历史改动。

```powershell
cd miner
npm install
npm run format:check
npm run lint
npm test
npm run build
```

```powershell
cd backend
python -m pip install -r requirements-dev.txt
ruff format --check applications/common/utils/safe_paths.py applications/api/analysis.py applications/api/project.py applications/project_hub/service.py test_safe_paths.py test_project_api.py test_new_features.py
ruff check applications/common/utils/safe_paths.py applications/api/analysis.py applications/api/project.py applications/project_hub/service.py test_safe_paths.py test_project_api.py test_new_features.py
python -m unittest discover -p "test_*.py"
```

部署前还须执行 `docker compose -f docker-compose.prod.yml config`，并对 Compose 与单镜像完成健康检查。构建产物、日志、运行数据、环境文件和密钥不得纳入版本控制。

## 开发任务执行顺序

1. 先补充可失败的回归测试，再修改实现。
2. 只改与当前缺陷直接相关的代码、配置和文档；不混入无关重构。
3. 分别执行格式、静态检查、单元测试、构建和部署配置校验。
4. 交付说明必须列出改动、原因、验证结果与尚未验证的限制。
