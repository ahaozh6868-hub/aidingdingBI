@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ============================================================
echo   PMS Sync Tool - Windows .exe 构建 ^& 发布脚本
echo ============================================================
echo.

:: ====== 检查 Python ======
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    echo        下载: https://www.python.org/downloads/
    echo        安装时必须勾选 "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [OK] Python %%v
echo.

:: ====== 安装依赖 ======
echo [1/4] 安装打包依赖...
pip install pyinstaller certifi --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo [错误] pip 安装失败，请检查网络
    pause
    exit /b 1
)
echo [OK] pyinstaller + certifi 已就绪
echo.

:: ====== 清理旧构建 ======
echo [2/4] 清理旧构建产物...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "release_pms_sync" rmdir /s /q "release_pms_sync"
echo [OK] 清理完成
echo.

:: ====== 构建 exe ======
echo [3/4] 构建 pms_sync.exe (约 1-3 分钟，请耐心等待)...
pyinstaller pms_sync.spec --clean --noconfirm --log-level WARN
if %errorlevel% neq 0 (
    echo.
    echo [错误] 构建失败！请检查上方错误信息
    echo        常见原因: 缺少依赖 / 杀毒软件拦截 / 磁盘空间不足
    pause
    exit /b 1
)
echo [OK] 构建完成
echo.

:: ====== 打包发布文件夹 ======
echo [4/4] 准备发布包...
if not exist "dist\pms_sync.exe" (
    echo [错误] dist\pms_sync.exe 未找到
    pause
    exit /b 1
)

:: 创建发布目录
mkdir "release_pms_sync" 2>nul

:: 复制 exe
copy /y "dist\pms_sync.exe" "release_pms_sync\" >nul

:: 生成 使用说明.txt
(
echo PMS同步工具 - 使用说明
echo ======================
echo.
echo 一、环境要求
echo   - Windows 7/10/11 (64位)
echo   - 必须安装 dws CLI 工具（见下方说明）
echo.
echo 二、安装 dws CLI（二选一）
echo   方式A: npm install -g dingtalk-workspace-cli
echo   方式B: 从 GitHub 下载 dws.exe 放到 pms_sync.exe 同级目录
echo          https://github.com/open-dingtalk/dingtalk-workspace-cli/releases
echo.
echo 三、运行命令
echo   :: 增量同步昨天的数据（每日例行）
echo   pms_sync.exe --token "Bearer YOUR_TOKEN"
echo.
echo   :: 只检查不写入（验证数据是否正确）
echo   pms_sync.exe --token "Bearer YOUR_TOKEN" --dry-run
echo.
echo   :: 全量同步所有历史数据（首次使用时）
echo   pms_sync.exe --token "Bearer YOUR_TOKEN" --full
echo.
echo   :: 如果 dws.exe 不在 PATH 中，指定路径
echo   pms_sync.exe --token "Bearer YOUR_TOKEN" --dws-path "C:\tools\dws.exe"
echo.
echo 四、执行日志
echo   每次运行后会在程序所在目录下创建 logs\ 文件夹
echo   日志文件格式: logs\sync_YYYYMMDD_HHMMSS.log
echo   控制台输出简洁摘要，日志文件包含完整的 DEBUG 级别记录
echo   方便后期排查问题
echo.
echo 五、Windows 定时任务（每天自动执行）
echo   1. 打开"任务计划程序"
echo   2. 创建基本任务 → 名称: PMS每日同步
echo   3. 触发器: 每天 2:00
echo   4. 操作: 启动程序 → pms_sync.exe
echo   5. 参数: --token "Bearer YOUR_TOKEN"
) > "release_pms_sync\使用说明.txt"

:: 生成 一键运行.bat
(
echo @echo off
echo chcp 65001 ^>nul
echo echo ============================================
echo echo   PMS 增量同步 - 拉取昨天数据到钉钉AI表格
echo echo ============================================
echo echo.
echo echo 请粘贴 PMS Bearer Token 后按回车...
echo echo.
echo set /p TOKEN="Token: "
echo echo.
echo echo 正在同步，请勿关闭此窗口...
echo pms_sync.exe --token "!TOKEN!"
echo echo.
echo echo 同步完成！
echo echo 日志文件: %~dp0logs\
echo echo.
echo pause
) > "release_pms_sync\一键运行.bat"

echo.
echo ============================================================
echo   构建 ^& 打包完成！
echo ============================================================
echo.
echo   输出文件:
for %%A in ("dist\pms_sync.exe") do echo     dist\pms_sync.exe  (%%~zA 字节)
echo.
echo   发布包 (release_pms_sync\):
echo     +-- pms_sync.exe      主程序
echo     +-- 使用说明.txt      部署文档
echo     +-- 一键运行.bat      交互式启动脚本
echo.
echo   === 交付给对方的步骤 ===
echo   1. 将 release_pms_sync\ 整个文件夹发给对方
echo   2. 对方需安装: npm install -g dingtalk-workspace-cli
echo      (或下载 dws.exe 放到 pms_sync.exe 同级目录)
echo   3. 双击"一键运行.bat" 或命令行执行
echo.
echo   每次运行自动在 pms_sync.exe 同级目录生成 logs\ 文件夹
echo ============================================================
echo.
pause
