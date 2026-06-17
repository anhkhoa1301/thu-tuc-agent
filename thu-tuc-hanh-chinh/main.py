import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from starlette.requests import Request
from starlette.responses import HTMLResponse
from duckduckgo_search import DDGS
from greennode_agentbase.memory import MemoryClient
from greennode_agentbase.memory.models import MemoryRecordSearchRequest

from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)

load_dotenv()

app = GreenNodeAgentBaseApp()

# --- Memory Configuration ---
MEMORY_ID = os.environ.get("AGENTBASE_MEMORY_ID", "")
MEMORY_STRATEGY_ID = os.environ.get("MEMORY_STRATEGY_ID", "")
_SHARED_ACTOR = "shared"
memory_client = MemoryClient() if MEMORY_ID else None


def _memory_namespace() -> str:
    return f"/strategies/{MEMORY_STRATEGY_ID}/actors/{_SHARED_ACTOR}"


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


# --- Memory & Web Search Tools ---

@tool
def recall_from_memory(query: str) -> str:
    """Tìm kiếm trong bộ nhớ dài hạn các câu hỏi và câu trả lời đã được lưu trước đó.
    Gọi tool này ĐẦU TIÊN trước khi trả lời bất kỳ câu hỏi nào.

    Args:
        query: Nội dung câu hỏi cần tìm trong bộ nhớ.
    """
    if not memory_client or not MEMORY_ID or not MEMORY_STRATEGY_ID:
        return "Memory chưa được cấu hình."
    try:
        results = asyncio.run(
            memory_client.search_memory_records_async(
                id=MEMORY_ID,
                namespace=_memory_namespace(),
                request=MemoryRecordSearchRequest(query=query, limit=5, scoreThreshold=0.55),
            )
        )
        if not results:
            return "Không tìm thấy thông tin liên quan trong bộ nhớ."
        return "\n".join(f"- [{r.score:.2f}] {r.memory}" for r in results)
    except Exception as e:
        return f"Lỗi khi truy xuất bộ nhớ: {str(e)}"


@tool
def web_search(query: str) -> str:
    """Tìm kiếm thông tin trên internet khi câu hỏi không có trong dữ liệu sẵn có và bộ nhớ.
    Dùng khi câu hỏi về thủ tục hành chính không thuộc 12 thủ tục đã biết.

    Args:
        query: Từ khóa tìm kiếm tiếng Việt, nên thêm 'thủ tục hành chính' vào query.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5, region="vn-vi"))
        if not results:
            return "Không tìm thấy kết quả tìm kiếm."
        output = []
        for r in results:
            output.append(f"**{r['title']}**\n{r['body']}\nNguồn: {r['href']}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Lỗi khi tìm kiếm: {str(e)}"


@tool
def remember_answer(question: str, answer: str) -> str:
    """Lưu câu hỏi và câu trả lời mới vào bộ nhớ dài hạn để dùng cho các lần sau.
    Gọi tool này SAU KHI đã trả lời xong bằng thông tin từ web_search.

    Args:
        question: Câu hỏi của người dùng.
        answer: Câu trả lời đầy đủ đã cung cấp cho người dùng.
    """
    if not memory_client or not MEMORY_ID or not MEMORY_STRATEGY_ID:
        return "Memory chưa được cấu hình."
    try:
        fact = f"Câu hỏi: {question}\nCâu trả lời: {answer}"
        asyncio.run(
            memory_client.insert_memory_records_directly_async(
                id=MEMORY_ID,
                namespace=_memory_namespace(),
                request=[fact],
            )
        )
        return "Đã lưu vào bộ nhớ thành công."
    except Exception as e:
        return f"Lỗi khi lưu vào bộ nhớ: {str(e)}"


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
9. Luôn nhắc người dùng kiểm tra lại với cơ quan có thẩm quyền vì quy định có thể thay đổi.
10. Nếu câu hỏi KHÔNG liên quan đến thủ tục hành chính (ví dụ: hỏi về thời tiết, nấu ăn, lập trình, v.v.), hãy trả lời ĐÚNG nội dung sau và không thêm gì khác:
"Tôi không thể trả lời câu hỏi này vì không nằm trong phạm vi hỗ trợ, hãy liên hệ với chủ nhân của tôi.
Phone : 0938432601
Email : khoana10@vng.com.vn"
11. QUY TRÌNH XỬ LÝ MỖI CÂU HỎI (bắt buộc theo thứ tự):
    a. LUÔN gọi recall_from_memory với nội dung câu hỏi — để kiểm tra bộ nhớ có câu trả lời phù hợp không.
    b. Nếu recall_from_memory trả về kết quả có score ≥ 0.6 → dùng thông tin đó để trả lời.
    c. Nếu không có trong bộ nhớ → dùng các tools thủ tục (search_procedure, get_full_procedure_info, v.v.).
    d. Nếu không có trong tools thủ tục → dùng web_search để tìm kiếm trên internet.
    e. Sau khi trả lời bằng thông tin mới từ web_search → LUÔN gọi remember_answer để lưu Q&A vào bộ nhớ.
12. Cuối MỖI câu trả lời (kể cả câu hỏi làm rõ), thêm đúng một dòng theo định dạng sau, không thêm bất kỳ ký tự nào khác:
[GỢI Ý]: <câu hỏi 1> | <câu hỏi 2> | <câu hỏi 3>
Yêu cầu: 2-3 gợi ý, mỗi gợi ý liên quan trực tiếp đến thủ tục hành chính, không quá 60 ký tự, viết dưới dạng câu hỏi ngắn gọn."""

# --- Create Agent ---
agent = create_agent(
    llm,
    tools=[
        recall_from_memory,
        web_search,
        remember_answer,
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
    raw = result["messages"][-1].content

    suggestions = []
    match = re.search(r'\[GỢI Ý\]:\s*(.+)$', raw, re.MULTILINE)
    if match:
        suggestions = [s.strip() for s in match.group(1).split('|') if s.strip()]
        raw = raw[:match.start()].strip()

    return {
        "status": "success",
        "response": raw,
        "suggestions": suggestions,
        "timestamp": datetime.now().isoformat(),
        "session_id": context.session_id,
    }


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


_UI_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trợ lý Thủ tục Hành chính</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;height:100vh;display:flex;flex-direction:column}
header{background:#1a56db;color:#fff;padding:14px 20px;display:flex;align-items:center;gap:10px;flex-shrink:0}
header h1{font-size:16px;font-weight:600}
header span{font-size:12px;opacity:.8}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:80%;padding:10px 14px;border-radius:12px;font-size:14px;line-height:1.6}
.msg.user{background:#1a56db;color:#fff;align-self:flex-end;border-bottom-right-radius:3px}
.msg.bot{background:#fff;color:#111;align-self:flex-start;border-bottom-left-radius:3px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.msg.bot p{margin:0 0 8px}.msg.bot p:last-child{margin:0}
.msg.bot ul,.msg.bot ol{padding-left:20px;margin:6px 0}
.msg.bot a{color:#1a56db}
.msg.bot strong{font-weight:600}
.msg.typing{color:#888;font-style:italic}
footer{background:#fff;border-top:1px solid #e5e7eb;padding:12px 16px;display:flex;gap:8px;flex-shrink:0}
#inp{flex:1;padding:10px 14px;border:1px solid #d1d5db;border-radius:8px;font-size:14px;outline:none}
#inp:focus{border-color:#1a56db}
#btn{background:#1a56db;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:14px;cursor:pointer;font-weight:500}
#btn:disabled{background:#93c5fd;cursor:not-allowed}
.suggestions{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 10px}
.sug{background:#fff;border:1px solid #d1d5db;border-radius:20px;padding:6px 12px;font-size:12px;cursor:pointer;color:#374151}
.sug:hover{border-color:#1a56db;color:#1a56db}
.reply-sugs{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;margin-bottom:4px;padding-left:4px;align-self:flex-start;max-width:80%}
.reply-sug{background:#eff6ff;border:1px solid #bfdbfe;border-radius:20px;padding:5px 12px;font-size:12px;cursor:pointer;color:#1d4ed8;transition:background .15s}
.reply-sug:hover{background:#dbeafe;border-color:#93c5fd}
</style>
</head>
<body>
<header>
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12h6M9 16h6M17 2H7a2 2 0 00-2 2v16l4-2 3 2 3-2 4 2V4a2 2 0 00-2-2z"/></svg>
  <div><h1>Trợ lý Thủ tục Hành chính</h1><span>Hỏi bằng tiếng Việt tự nhiên</span></div>
</header>
<div class="suggestions" id="sugs">
  <span class="sug" onclick="ask(this)">Làm CCCD cần giấy tờ gì?</span>
  <span class="sug" onclick="ask(this)">Làm hộ chiếu mất bao lâu?</span>
  <span class="sug" onclick="ask(this)">Đăng ký kết hôn cần gì?</span>
  <span class="sug" onclick="ask(this)">Phí làm giấy phép lái xe?</span>
</div>
<div id="chat"></div>
<footer>
  <input id="inp" type="text" placeholder="Ví dụ: Đăng ký hộ kinh doanh cần hồ sơ gì?" onkeydown="if(event.key==='Enter')send()">
  <button id="btn" onclick="send()">Gửi</button>
</footer>
<script>
const chat=document.getElementById('chat');
const inp=document.getElementById('inp');
const btn=document.getElementById('btn');

function addMsg(text,role){
  const d=document.createElement('div');
  d.className='msg '+role;
  if(role==='bot') d.innerHTML=marked.parse(text);
  else d.textContent=text;
  chat.appendChild(d);
  chat.scrollTop=chat.scrollHeight;
  return d;
}

async function send(){
  const msg=inp.value.trim();
  if(!msg)return;
  document.getElementById('sugs').style.display='none';
  inp.value='';btn.disabled=true;
  addMsg(msg,'user');
  const typing=addMsg('Đang tra cứu...','bot typing');
  try{
    const r=await fetch('/invocations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const d=await r.json();
    typing.className='msg bot';
    typing.innerHTML=marked.parse(d.response||d.error||'Có lỗi xảy ra.');
    if(d.suggestions&&d.suggestions.length){
      const wrap=document.createElement('div');
      wrap.className='reply-sugs';
      d.suggestions.forEach(s=>{
        const b=document.createElement('button');
        b.className='reply-sug';
        b.textContent=s;
        b.onclick=()=>{inp.value=s;send();};
        wrap.appendChild(b);
      });
      chat.appendChild(wrap);
    }
  }catch(e){
    typing.className='msg bot';
    typing.textContent='Không thể kết nối đến máy chủ. Vui lòng thử lại.';
  }
  btn.disabled=false;
  inp.focus();
  chat.scrollTop=chat.scrollHeight;
}

function ask(el){inp.value=el.textContent;send();}
inp.focus();
</script>
</body>
</html>"""


async def _ui(request: Request) -> HTMLResponse:
    return HTMLResponse(content=_UI_HTML)


app.add_route("/", _ui, methods=["GET"])


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
