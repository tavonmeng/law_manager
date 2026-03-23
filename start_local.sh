#!/bin/bash
echo "=== 启动本地前后端系统 ==="

# 确保在 venv 且安装了新的依赖
source venv/bin/activate
# 安装刚刚新增到 requirements.txt 的依赖
pip install -r requirements.txt -q

echo "1/2 启动后端 API (FastAPI)..."
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 &
PID_BACKEND=$!
cd ..

echo "2/2 启动前端 UI (Streamlit)..."
cd frontend
export STREAMLIT_SERVER_HEADLESS=true
python start_streamlit.py &
PID_FRONTEND=$!

echo ""
echo "🔥 所有服务已启动。按 [CTRL+C] 安全退出并关闭服务。"
echo "- Streamlit => http://localhost:8501"
echo "- FastAPI => http://localhost:8000/docs (Swagger UI 文档)"
trap "echo '正在关闭服务...'; kill $PID_BACKEND $PID_FRONTEND; exit" INT
wait
