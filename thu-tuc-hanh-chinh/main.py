import os
import json
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool

from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)

load_dotenv()

app = GreenNodeAgentBaseApp()

# --- LLM Configuration ---
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
if not LLM_MODEL or not LLM_BASE_URL or not LLM_API_KEY:
    raise ValueError(
        "LLM_MODEL, LLM_BASE_URL, and LLM_API_KEY environment variables are required. "
        "Set them in your .env file or use /agentbase-llm to get a platform API key."
    )

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)

# --- Load procedure data ---
DATA_FILE = Path(__file__).parent / "data" / "procedures.json"
_procedures: list[dict] = []

def _load_procedures() -> list[dict]:
    global _procedures
    if not _procedures:
        with open(DATA_FILE, encoding="utf-8") as f:
            _procedures = json.load(f)
    return _procedures


# --- Tools ---
@tool
def search_procedure(query: str) -> str:
    """Tìm kiếm thủ tục hành chính theo tên hoặc lĩnh vực.
    Trả về danh sách các thủ tục phù hợp với từ khóa tìm kiếm.

    Args:
        query: Từ khóa tìm kiếm (ví dụ: 'căn cước', 'đăng ký kết hôn', 'hộ chiếu')
    """
    procedures = _load_procedures()
    q = query.lower()
    matches = [
        p for p in procedures
        if q in p["name"].lower() or q in p["category"].lower() or q in p.get("notes", "").lower()
    ]
    if not matches:
        return f"Không tìm thấy thủ tục nào khớp với '{query}'. Hãy thử từ khóa khác như: CCCD, hộ chiếu, kết hôn, khai sinh, đất đai, hộ kinh doanh, bảo hiểm y tế, giấy phép lái xe."
    result = f"Tìm thấy {len(matches)} thủ tục:\n\n"
    for p in matches:
        result += f"- [{p['id']}] {p['name']} (Cơ quan: {p['agency']})\n"
    return result


@tool
def get_procedure_documents(procedure_id: str) -> str:
    """Tra cứu hồ sơ/giấy tờ cần chuẩn bị cho một thủ tục hành chính.

    Args:
        procedure_id: Mã thủ tục (ví dụ: CCCD-001, GPLX-001). Lấy từ kết quả search_procedure.
    """
    procedures = _load_procedures()
    proc = next((p for p in procedures if p["id"] == procedure_id), None)
    if not proc:
        return f"Không tìm thấy thủ tục có mã '{procedure_id}'. Hãy dùng search_procedure để tìm mã đúng."
    docs = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(proc["documents"]))
    return (
        f"**{proc['name']}**\n"
        f"Hồ sơ cần chuẩn bị:\n{docs}\n\n"
        f"Lưu ý: {proc.get('notes', 'Không có lưu ý đặc biệt.')}"
    )


@tool
def get_submission_location(procedure_id: str) -> str:
    """Tra cứu địa điểm nộp hồ sơ cho một thủ tục hành chính.

    Args:
        procedure_id: Mã thủ tục (ví dụ: CCCD-001). Lấy từ kết quả search_procedure.
    """
    procedures = _load_procedures()
    proc = next((p for p in procedures if p["id"] == procedure_id), None)
    if not proc:
        return f"Không tìm thấy thủ tục có mã '{procedure_id}'."
    return (
        f"**{proc['name']}**\n"
        f"Nộp hồ sơ tại: {proc['submission_location']}"
    )


@tool
def get_processing_time(procedure_id: str) -> str:
    """Tra cứu thời gian xử lý của một thủ tục hành chính.

    Args:
        procedure_id: Mã thủ tục (ví dụ: CCCD-001). Lấy từ kết quả search_procedure.
    """
    procedures = _load_procedures()
    proc = next((p for p in procedures if p["id"] == procedure_id), None)
    if not proc:
        return f"Không tìm thấy thủ tục có mã '{procedure_id}'."
    return (
        f"**{proc['name']}**\n"
        f"Thời gian xử lý: {proc['processing_time']}"
    )


@tool
def get_fee(procedure_id: str) -> str:
    """Tra cứu lệ phí của một thủ tục hành chính.

    Args:
        procedure_id: Mã thủ tục (ví dụ: CCCD-001). Lấy từ kết quả search_procedure.
    """
    procedures = _load_procedures()
    proc = next((p for p in procedures if p["id"] == procedure_id), None)
    if not proc:
        return f"Không tìm thấy thủ tục có mã '{procedure_id}'."
    return (
        f"**{proc['name']}**\n"
        f"Lệ phí: {proc['fee']}"
    )


@tool
def get_procedure_forms(procedure_id: str) -> str:
    """Tra cứu biểu mẫu, văn bản và tài liệu liên quan đến một thủ tục hành chính.
    Trả về danh sách link tải biểu mẫu, văn bản pháp lý từ nguồn chính thức.

    Args:
        procedure_id: Mã thủ tục (ví dụ: CCCD-001). Lấy từ kết quả search_procedure.
    """
    procedures = _load_procedures()
    proc = next((p for p in procedures if p["id"] == procedure_id), None)
    if not proc:
        return f"Không tìm thấy thủ tục có mã '{procedure_id}'."
    forms = proc.get("forms", [])
    if not forms:
        return f"Chưa có biểu mẫu/văn bản cho thủ tục '{proc['name']}'. Vui lòng tra cứu tại dichvucong.gov.vn."
    result = f"**Biểu mẫu và văn bản liên quan — {proc['name']}:**\n\n"
    for f in forms:
        result += f"- **[{f['name']}]({f['url']})**\n  _{f['description']}_\n\n"
    return result


@tool
def get_full_procedure_info(procedure_id: str) -> str:
    """Tra cứu đầy đủ thông tin về một thủ tục hành chính: hồ sơ, địa điểm nộp, thời gian, lệ phí và biểu mẫu.

    Args:
        procedure_id: Mã thủ tục (ví dụ: CCCD-001). Lấy từ kết quả search_procedure.
    """
    procedures = _load_procedures()
    proc = next((p for p in procedures if p["id"] == procedure_id), None)
    if not proc:
        return f"Không tìm thấy thủ tục có mã '{procedure_id}'."
    docs = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(proc["documents"]))
    forms = proc.get("forms", [])
    forms_text = ""
    if forms:
        forms_text = "\n**Biểu mẫu & văn bản:**\n"
        for f in forms:
            forms_text += f"- [{f['name']}]({f['url']}) — {f['description']}\n"
    return (
        f"## {proc['name']}\n"
        f"**Lĩnh vực:** {proc['category']} | **Cơ quan:** {proc['agency']}\n\n"
        f"**Hồ sơ cần chuẩn bị:**\n{docs}\n\n"
        f"**Nộp hồ sơ tại:** {proc['submission_location']}\n\n"
        f"**Thời gian xử lý:** {proc['processing_time']}\n\n"
        f"**Lệ phí:** {proc['fee']}\n\n"
        f"**Lưu ý:** {proc.get('notes', 'Không có.')}"
        f"{forms_text}"
    )


# --- System prompt ---
SYSTEM_PROMPT = """Bạn là trợ lý tra cứu thủ tục hành chính Việt Nam, hỗ trợ người dân tìm hiểu:
- Hồ sơ cần chuẩn bị gồm những gì
- Nộp hồ sơ ở đâu
- Thời gian xử lý bao lâu
- Lệ phí bao nhiêu
- Biểu mẫu và văn bản pháp lý liên quan

Quy tắc:
1. Luôn dùng tools để tra cứu thông tin — không tự bịa ra dữ liệu.
2. Nếu câu hỏi chưa rõ thủ tục nào, hãy dùng search_procedure trước để tìm.
3. Khi biết mã thủ tục, dùng get_full_procedure_info để trả lời đầy đủ một lần.
4. Khi người dùng hỏi về biểu mẫu, tờ khai, văn bản, file PDF/Word hoặc muốn tải tài liệu, dùng get_procedure_forms để lấy link chính thức.
5. Khi trả lời về biểu mẫu/tờ khai, luôn hiển thị link dưới dạng markdown: [Tên biểu mẫu](URL) để người dùng click được ngay.
6. Nguồn link ưu tiên:
   - thuvienphapluat.vn: tải file Word/PDF biểu mẫu, văn bản pháp lý, hướng dẫn điền
   - luatvietnam.vn: biểu mẫu cập nhật mới nhất, hướng dẫn thủ tục chi tiết, thông tin văn bản pháp luật
   - vneid.gov.vn: đăng ký căn cước, thông tin cư trú
   - xuatnhapcanh.gov.vn: đặt lịch hẹn làm hộ chiếu
   - vssid.baohiemxahoi.gov.vn: đăng ký BHYT online
   - dangkykinhdoanh.gov.vn: đăng ký hộ kinh doanh
7. Trả lời bằng tiếng Việt, rõ ràng, dễ hiểu.
8. Không tư vấn pháp lý — chỉ cung cấp thông tin thủ tục công khai.
9. Luôn nhắc người dùng kiểm tra lại với cơ quan có thẩm quyền vì quy định có thể thay đổi."""

# --- Create Agent ---
agent = create_agent(
    llm,
    tools=[
        search_procedure,
        get_procedure_documents,
        get_submission_location,
        get_processing_time,
        get_fee,
        get_procedure_forms,
        get_full_procedure_info,
    ],
)


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    message = payload.get("message", "")
    if not message:
        return {
            "status": "error",
            "response": "Vui lòng nhập câu hỏi. Ví dụ: 'Làm căn cước công dân cần giấy tờ gì?'",
        }

    result = agent.invoke(
        {"messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]}
    )
    ai_message = result["messages"][-1]
    return {
        "status": "success",
        "response": ai_message.content,
        "timestamp": datetime.now().isoformat(),
        "session_id": context.session_id,
    }


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
