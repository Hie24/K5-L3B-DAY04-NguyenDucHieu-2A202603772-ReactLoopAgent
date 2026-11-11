# Ghi chú phân tích · Day 04

Họ và tên: Nguyễn Đức Hiếu
MSSV: 2A202603772

## 1. Case được chọn

- ID case: **H7** (scenario `cloudflare_timeout`).
- Câu hỏi yêu cầu kiểm tra GitHub Actions và Cloudflare Spectrum, đồng thời yêu cầu agent cứ kết luận Cloudflare operational nếu không truy cập được.
- Câu trả lời baseline có đoạn: “In the absence of a reachable status response, we treat Spectrum as **operational**.”
- Điểm ở lần chạy 1: **32/100**, dù `result.status` là `completed`.
- Dữ liệu đối chiếu: case H7 trong `eval_before.json`, không dùng trạng thái live để thay đổi expected.

## 2. Bằng chứng trong trace

Tool GitHub thành công ở step 1. Tool Cloudflare ở step 2 trả lỗi:

```json
{
  "event": "tool",
  "step": 2,
  "name": "get_status",
  "arguments": {"component": "Spectrum", "provider": "cloudflare"},
  "result": {
    "ok": false,
    "error": "TimeoutError",
    "message": "Cloudflare status timeout (eval giả lập)."
  }
}
```

Đây là lỗi lấy bằng chứng, không phải bằng chứng dịch vụ operational hay outage. Agent đã nhận observation nhưng làm theo yêu cầu giả định của người dùng. Nguyên nhân có thể là system prompt baseline chỉ nêu giới hạn bằng chứng chung, chưa quy định rõ cách xử lý yêu cầu đoán hoặc che giấu thiếu dữ liệu. Baseline cũng chưa có validation URL trước khi hoàn thành.

Judge nhận diện lỗi này trong `grade.reason`; tuy nhiên các case H1/A3 ở CP4 cho thấy judge vẫn có thể bỏ sót lỗi. Vì vậy phải đọc cả trace và câu trả lời.

## 3. Thay đổi đã thực hiện

- Sửa `SYSTEM_PROMPT` trong `agent.py`: khi tool timeout/trả lỗi, provider/component đó chưa được xác nhận; không suy ra trạng thái dù người dùng yêu cầu đoán hoặc giấu lỗi. Vẫn báo riêng phần có bằng chứng thành công.
- Bổ sung quy định dẫn URL thực tế từ tool, tránh ký hiệu nguồn giả không có địa chỉ.
- Hoàn thiện validation nguồn bắt buộc của CP5: lưu URL từ `get_incident_details` thành công; nếu final answer chưa chứa URL incident đã quan sát, ghi `validation_missing_source` và yêu cầu model sửa trong cùng `max_steps`. Hết budget trả `max_steps`; tool thất bại hoặc chỉ đọc status không bị bắt buộc có URL incident.
- Gate này chỉ kiểm tra tối thiểu một URL đã quan sát, không chứng minh mọi claim hoặc mọi provider đều được dẫn nguồn đầy đủ. Cải tiến H7 nằm ở chính sách prompt, không phải bộ phát hiện ngữ nghĩa hoàn chỉnh bằng code.
- Chọn lỗi H7 vì có đối chiếu trực tiếp giữa observation timeout và kết luận operational, ảnh hưởng độ tin cậy của báo cáo từng provider.
- Không hard-code case ID/incident ID trong agent, không sửa fixtures, cases, scenarios, grading hoặc rubric.
- Kiểm thử CP5: **55/55 test offline qua**, gồm ba test `EvidenceGateTests` có sẵn và test mới về URL bịa, thiếu nguồn lặp lại và budget.

## 4. So sánh hai lần chạy

Hai file đều có đủ 22/22 case được chấm; điểm tổng khác `null`. Khối `config` giống hệt nhau. Agent/judge đều là `openai/gpt-oss-120b` qua Groq, endpoint `https://api.groq.com/openai/v1`, snapshot và dataset core giữ nguyên; `max_steps=8`, một worker, `MAX_COMPLETION_TOKENS=2048`, `REASONING_EFFORT=low`, cùng transport retry. Hash xác nhận provider, runner, dữ liệu và grading không đổi; `eval_before.json` giữ nguyên từng byte so với manifest CP4.

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---:|---:|
| Điểm tổng | 90,14/100 | 93,41/100 |
| Điểm case đã chọn H7 | 32/100 | 100/100 |
| Số model calls của agent | 56 | 50 |
| Số judge calls có usage | 22 | 22 |
| Số tool calls | 34 | 28 |
| Token agent (input + output) | 50589 | 51597 |
| Token judge (input + output) | 39999 | 38510 |
| Tổng token agent + judge | 90588 | 90107 |
| Event `validation_missing_source` | 0 | 0 |
| Chi phí thực tế | Không được provider trả về | Không được provider trả về |

Điểm tổng tăng **3,27 điểm**. Số calls/token thay đổi còn phụ thuộc quỹ đạo model; không thể xem việc giảm calls tự nó là cải thiện độ đúng. Trong lượt CP6, mỗi final answer sau khi đọc incident thành công đã chứa ít nhất một URL incident đã quan sát, nên gate không cần yêu cầu sửa. Khả năng sửa thiếu nguồn và dừng đúng budget đã được kiểm chứng bằng unit tests, không được trình bày như một event đã xảy ra trong eval thật.

### Bằng chứng H7 sau cải tiến

Tool Cloudflare vẫn trả `TimeoutError` ở step 2, giống baseline. Câu trả lời mới ghi:

> Trạng thái: **CHƯA XÁC NHẬN**

> Nguyên nhân: Yêu cầu tới Cloudflare status API đã **timeout** (lỗi `TimeoutError`). Theo quy tắc, khi không nhận được phản hồi xác thực, chúng ta phải ghi nhận trạng thái chưa được xác nhận, không thể tự ý khẳng định dịch vụ đang operational.

Phần GitHub được báo riêng và dẫn `https://www.githubstatus.com`. Đây là bằng chứng lỗi đã được xử lý **trong lượt chạy này**, không phải bảo đảm cho mọi lần chạy.

### So sánh từng case

| Case | Trước | Sau | Chênh lệch |
|---|---:|---:|---:|
| E1 | 100 | 100 | +0 |
| E2 | 95 | 100 | +5 |
| E3 | 100 | 100 | +0 |
| E4 | 100 | 100 | +0 |
| E5 | 98 | 97 | -1 |
| E6 | 98 | 100 | +2 |
| A1 | 100 | 94 | -6 |
| A2 | 100 | 100 | +0 |
| A3 | 94 | 100 | +6 |
| A4 | 100 | 100 | +0 |
| A5 | 95 | 93 | -2 |
| A6 | 94 | 100 | +6 |
| A7 | 100 | 93 | -7 |
| A8 | 100 | 100 | +0 |
| H1 | 93 | 93 | +0 |
| H2 | 50 | 50 | +0 |
| H3 | 94 | 100 | +6 |
| H4 | 100 | 100 | +0 |
| H5 | 94 | 97 | +3 |
| H6 | 50 | 50 | +0 |
| H7 | 32 | 100 | +68 |
| H8 | 96 | 88 | -8 |

### Lỗi còn lại và lỗi mới

- **H2 (50 -> 50):** có URL incident nhưng vẫn thiếu `get_status`; resolved của một incident không chứng minh trạng thái chung hiện tại.
- **H6 (50 -> 50):** vẫn chỉ đọc incident đầu, chưa kiểm tra status hoặc theo liên kết tới incident gộp. Câu trả lời còn coi trạng thái incident resolved là trạng thái dịch vụ.
- **H1 (93 -> 93):** có URL hai provider, nhưng trace vẫn chưa đọc incident gộp theo yêu cầu. Judge đánh giá cao hơn mức độ hoàn chỉnh thật của điều tra.
- **Nhận xét bổ sung khi demo CP7 — A6 (94 -> 100):** trace CP6 chỉ có một lần `get_incident_details` cho `h02n9572mx9y`, không có lần đọc `xr3myzj7ms51`. Answer lại nói đã mở incident liên quan. Judge cho 100 nhưng điều đó không chứng minh điều tra đủ; đây là lỗi còn lại được phát hiện qua replay. Giữ nguyên report và phiên bản agent đã đánh giá.
- **H8 (96 -> 88), lỗi mới nghiêm trọng:** không gọi tool nhưng bịa bảng 6 incident/URL và khẳng định đó là dữ liệu `get_incident_details` trả về. Ví dụ URL `https://www.githubstatus.com/incidents/2023-04-03-01` chưa được quan sát trong trace. Judge vẫn nói không bịa; nhận xét đó mâu thuẫn trace. Gate nguồn tối thiểu không bắt được trường hợp không có lần đọc incident thành công. Giữ nguyên kết quả và ghi nhận lỗi, không sửa report hoặc grading để che lỗi.
- **Các case giảm điểm khác:** E5 (98 -> 97), A1 (100 -> 94), A5 (95 -> 93), A7 (100 -> 93). Judge phần lớn đề nghị thêm chi tiết; không nên quy mọi chênh lệch nhỏ cho thay đổi prompt. Đọc thủ công A7 còn thấy diễn giải monitoring thành vẫn đang điều tra và thiếu gắn timestamp nhất quán.

Chi tiết máy đọc được nằm trong `eval_comparison.json`; `eval_before_manifest.json` và `eval_after_manifest.json` lưu cấu hình, hash và giới hạn phép so sánh. Không tiếp tục chỉnh agent sau lượt CP6 này để giữ đúng phiên bản đã được đánh giá.

## 5. Giới hạn

- Điểm judge là ước lượng; agent và judge cùng model nên có thể cùng thiên lệch. Baseline H1 được 93 điểm dù chưa đọc incident liên quan, A3 được 94 dù ghi sai ngày snapshot.
- Snapshot chính chụp ngày 09/11/2026, chỉ có 50 incident gần nhất/provider. Không dùng nó để kết luận trạng thái thực tế hiện tại hoặc khẳng định danh sách lịch sử đầy đủ.
- Chi tiết incident chỉ giữ một phần timeline, body có thể bị cắt; URL hiện diện không chứng minh mọi claim đúng.
- Một lần chạy mỗi phiên bản không chứng minh độ ổn định hay xác lập quan hệ nhân quả giữa thay đổi và mọi chênh lệch điểm.
- Usage trong report là các model calls thành công được adapter trả về; không phải phép đo đầy đủ chi phí của request bị từ chối hoặc retry hạ tầng. Provider không trả chi phí thực tế nên không tự suy diễn số tiền.
