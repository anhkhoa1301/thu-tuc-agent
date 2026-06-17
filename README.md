# Trợ Lý AI Tra Cứu Thủ Tục Hành Chính Việt Nam

Agent AI giúp người dùng tra cứu nhanh các thủ tục hành chính phổ biến tại Việt Nam — hồ sơ cần chuẩn bị, nơi nộp, thời gian xử lý, lệ phí và biểu mẫu.

**Demo trực tiếp:** (https://endpoint-2f657255-d9ea-4144-9299-437868714ade.agentbase-runtime.aiplatform.vngcloud.vn/)

---

## Tính năng

- Tra cứu hồ sơ, giấy tờ cần chuẩn bị cho từng thủ tục
- Địa điểm nộp hồ sơ (trực tiếp hoặc trực tuyến)
- Thời gian xử lý theo quy định
- Lệ phí chính thức
- Link tải biểu mẫu từ nguồn pháp lý
- Hỗ trợ 12+ thủ tục: CCCD, hộ chiếu, đăng ký kết hôn/khai sinh/khai tử, hộ khẩu, giấy phép lái xe, sổ đỏ, hộ kinh doanh, bảo hiểm y tế hộ gia đình

## Kiến trúc

```
Người dùng
    │
    ▼
Next.js Web App (Vercel)
    │  POST /api/chat  {"message": "..."}
    ▼
GreenNode AgentBase Runtime  ◄── Docker image
    │
    ├── LangChain Agent (qwen3-5-27b via GreenNode AIP)
    └── Tools:
        ├── search_procedure           # Tìm thủ tục theo tên/từ khóa
        ├── get_procedure_documents    # Danh sách hồ sơ cần nộp
        ├── get_submission_location    # Nơi nộp hồ sơ
        ├── get_processing_time        # Thời gian xử lý
        ├── get_fee                    # Lệ phí
        ├── get_procedure_forms        # Biểu mẫu và văn bản
        └── get_full_procedure_info    # Thông tin đầy đủ
```

## Stack công nghệ

| Thành phần | Công nghệ |
|-----------|-----------|
| **Agent Backend** | Python, LangChain, GreenNode AgentBase SDK |
| **LLM** | Qwen3-5-27b qua GreenNode AIP (OpenAI-compatible) |
| **Runtime** | GreenNode AgentBase (Docker container, autoscaling) |
| **Frontend** | Next.js 14, Tailwind CSS, TypeScript |
| **Hosting** | Vercel (frontend) + GreenNode AgentBase (backend) |

## Cấu trúc repo

```
thu-tuc-agent/
├── thu-tuc-hanh-chinh/     # Backend: AI Agent
│   ├── main.py              # Agent entrypoint + LangChain tools
│   ├── data/
│   │   └── procedures.json  # Dữ liệu 12+ thủ tục hành chính
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
└── thu-tuc-ui/
    └── web/                 # Frontend: Next.js app
        ├── app/
        │   ├── page.tsx     # Giao diện chat
        │   └── api/chat/    # API route → AgentBase endpoint
        └── .env.local.example
```

## Chạy local

### Backend

```bash
cd thu-tuc-hanh-chinh
python -m venv venv && source venv/bin/activate  # hoặc venv\Scripts\Activate.ps1 trên Windows
pip install -r requirements.txt
cp .env.example .env      # Điền LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
python main.py            # Agent khởi động tại http://localhost:8080
```

```bash
# Test
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Làm căn cước công dân cần giấy tờ gì?"}'
```

### Frontend

```bash
cd thu-tuc-ui/web
npm install
cp .env.local.example .env.local  # Điền AGENT_ENDPOINT
npm run dev                        # http://localhost:3000
```

## Deploy

- **Backend:** GreenNode AgentBase — [console](https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime)
- **Frontend:** Vercel — tự động qua `vercel --prod`

## API Endpoint

Backend AgentBase nhận POST request:

```json
POST /invocations
{"message": "Câu hỏi của người dùng"}

// Response
{"status": "success", "response": "Trả lời của agent", "timestamp": "..."}
```
