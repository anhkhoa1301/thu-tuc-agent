# thu-tuc-hanh-chinh

Trợ lý AI tra cứu thủ tục hành chính Việt Nam, xây dựng trên GreenNode AgentBase.

Agent trả lời các câu hỏi thường gặp:
- **Hồ sơ gồm gì?** — danh sách giấy tờ cần chuẩn bị
- **Nộp ở đâu?** — cơ quan tiếp nhận, địa chỉ, online hay offline
- **Mất bao lâu?** — thời gian xử lý theo quy định
- **Lệ phí bao nhiêu?** — chi phí chính thức

Các thủ tục được hỗ trợ: CCCD, hộ chiếu, đăng ký kết hôn/khai sinh/khai tử, hộ khẩu thường trú, giấy phép lái xe, sổ đỏ, hộ kinh doanh, bảo hiểm y tế hộ gia đình.

## Yêu cầu

- Python 3.10+
- GreenNode IAM Service Account ([tạo tại đây](https://iam.console.vngcloud.vn/service-accounts))
- LLM API key (GreenNode AIP hoặc OpenAI)

## Cài đặt

```powershell
# Windows PowerShell
cd C:\Users\STARTER-local\thu-tuc-hanh-chinh
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Cấu hình

```powershell
copy .env.example .env
# Mở .env và điền các giá trị:
# GREENNODE_CLIENT_ID, GREENNODE_CLIENT_SECRET
# LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
```

**GreenNode AIP (khuyến nghị):**
```
LLM_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_MODEL=<tên model từ /agentbase-llm models list>
```

**OpenAI:**
```
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
```

## Chạy local

```powershell
python main.py
```

Agent khởi động tại `http://127.0.0.1:8080`.

**Test thử:**
```powershell
curl -X POST http://127.0.0.1:8080/invocations `
  -H "Content-Type: application/json" `
  -d '{"message": "Làm căn cước công dân cần giấy tờ gì?"}'
```

**Health check:**
```powershell
curl http://127.0.0.1:8080/health
```

## Triển khai lên AgentBase

```
/agentbase-deploy
```

Xem console tại: https://aiplatform.console.vngcloud.vn/agent-runtime?tab=runtime

## Cấu trúc project

```
thu-tuc-hanh-chinh/
├── main.py              # Agent entrypoint + LangChain tools
├── data/
│   └── procedures.json  # Dữ liệu thủ tục hành chính
├── Dockerfile
├── requirements.txt
├── .env.example
├── .greennode.json
├── .gitignore
└── .dockerignore
```

## Mở rộng dữ liệu

Thêm thủ tục mới vào `data/procedures.json` theo cấu trúc:

```json
{
  "id": "MA-001",
  "name": "Tên thủ tục",
  "category": "Lĩnh vực",
  "agency": "Cơ quan thực hiện",
  "documents": ["Giấy tờ 1", "Giấy tờ 2"],
  "submission_location": "Nộp ở đâu",
  "processing_time": "Bao lâu",
  "fee": "Lệ phí",
  "notes": "Lưu ý thêm"
}
```
