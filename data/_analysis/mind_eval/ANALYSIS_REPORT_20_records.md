# BÁO CÁO PHÂN TÍCH CUỐI CÙNG — Dim-A (MindEval), Pilot N=20

**Phạm vi dữ liệu**: 32 file judgment JSONL · 6 dataset (cactus, simpsydial, Psy-Insight, PsyDial, SoulChat, KMI) · 3 setting (S1/S2/S3) · 2 judge (GPT-5.1, Claude Sonnet) · 1.120 judgment records · 0 lỗi parse.

**Cách đọc báo cáo**: Cấp 0 là tóm tắt một đoạn. Cấp 1 là các quyết định cần chốt. Cấp 2 là 12 finding chính, mỗi finding có giải thích dễ hiểu + bằng chứng. Cấp 3 là chi tiết kỹ thuật và khuyến nghị thực thi. Cuối cùng là bảng chú giải thuật ngữ.

---

# CẤP 0 — Tóm tắt một đoạn

Sáu dataset xếp hạng ổn định **cactus > simpsydial > Psy-Insight > PsyDial > SoulChat ≈ KMI** bất kể judge nào chấm và setting ngôn ngữ nào — đây là kết quả vững nhất. Trục đánh giá nên chốt là **S3** (văn bản gốc + judge tiếng Anh) vì nó cho cùng ranking với S1 nhưng không chứa bước dịch — bước đã được chứng minh là nguồn nhiễu chính (artifact KMI với GPT; translation-polish với Claude). Nỗi lo "GPT dịch rồi GPT tự khen" **không có bằng chứng** (kiểm định DiD cho kết quả ngược chiều). Hai judge lệch nhau về độ khắt khe nhưng trùng nhau gần tuyệt đối về hồ sơ thế mạnh tương đối (r=0.94), nên dùng một judge chính là hợp lệ. Hai vấn đề cần sửa trước khi chạy full: (1) rubric AIComm mơ hồ khiến hai judge chấm hai khái niệm khác nhau (đồng thuận chỉ ρ=0.29); (2) hiệu ứng halo lớn cho thấy 5 metric thực chất chỉ đo ~2 chiều.

---

# CẤP 1 — Các quyết định (Decisions)

## D1. Trục chính cho toàn bộ pipeline (Dim-A full run, WAI, Trajectory): **S3**

| Lý do | Bằng chứng |
|---|---|
| Ranking trùng S1 gần tuyệt đối | Spearman dataset-rank S1↔S3: GPT 0.943, Claude 1.000 |
| Không chứa bước dịch → miễn nhiễm 2 artifact dịch | Finding F4, F5 |
| Judge EN đọc văn bản gốc KO/ZH không lệch so với judge bản ngữ | S3−S2 ≈ 0 trên hầu hết dataset (KMI: −0.02/+0.05) |
| Đồng thuận giữa 2 judge cao nhất | record-level ρ: S3=0.59 > S1=0.57 ≫ S2=0.34 |
| Discriminative power (độ phân biệt) không thua S1 sau khi sửa artifact | GPT S1-đã-sửa-KMI = 0.246 < S3 = 0.254; Claude 0.356 ≈ 0.360 |
| Rẻ nhất | Không tốn phí dịch ~600 hội thoại khi scale full 200; KMI không cần dịch lại |

Vai trò các trục còn lại: **S1** = robustness check (kiểm tra độ bền) trên mẫu nhỏ; **S2** = fidelity reference (đối chiếu bản ngữ), tuyệt đối không dùng xếp hạng chéo.

## D2. Chiến lược judge

- **Judge chính: GPT-5.1** là hợp lệ — strength profile bất biến theo judge (F7) nghĩa là kết luận không phụ thuộc lựa chọn này.
- **Claude Sonnet**: giữ làm robustness judge trên mẫu 25–30% nếu ngân sách hạn chế (Sonnet có giá trị riêng: thang điểm rộng hơn, phân biệt record tốt hơn).
- **Claude Haiku**: KHÔNG thay thế trực tiếp khi chưa kiểm chứng. Chạy validation pilot 120 records S3 hiện có (≈ chi phí không đáng kể) rồi so với Sonnet/GPT. Tiêu chí đạt: dataset-rank Spearman ≥ 0.9 với cả hai judge cũ; đồng thuận record-level với GPT ≈ 0.59 (mức Sonnet↔GPT). Đạt → Haiku làm robustness judge; không đạt → dùng phương án mẫu 25–30% với Sonnet.
- **Không bao giờ trộn điểm raw giữa các judge** (F6) — mọi so sánh chéo judge qua z-score (điểm chuẩn hóa) nội-judge.

## D3. Sửa rubric trước khi chạy full 200 (đặc biệt AIComm)

Vấn đề: judge tự suy ra nguồn gốc dữ liệu (human vs simulated) từ văn phong, và vì rubric không có quy tắc xử lý, mỗi judge tự chọn cách diễn giải khác nhau (F9). Blind evaluation (đánh giá mù) hoàn toàn là bất khả thi — văn bản tự lộ nguồn gốc; và "làm sạch" văn bản để giấu nguồn gốc chính là cơ chế tạo ra artifact KMI (F4). Giải pháp: sửa **decision rule (quy tắc quyết định)** trong rubric, ví dụ:

> "Đánh giá therapist trong transcript như thể đó là một AI assistant, bất kể văn phong. Không suy đoán nguồn gốc dữ liệu. Disfluency tự nhiên (um, hmm) không bị phạt và không được thưởng ở AIComm. Self-disclosure trải nghiệm cá nhân của therapist luôn được tính là vi phạm AI-specific. Định dạng bullet/header và câu mở công thức bị trừ ở AIComm."

(Nội dung cụ thể do nhóm chọn — điều bắt buộc là *phải chọn một quy tắc thống nhất* cho từng điểm mơ hồ ở trên.)

## D4. Trình tự thực thi đề xuất

1. Sửa rubric AIComm (D3) → 2. Chạy full N=200 Dim-A trên S3 với GPT-5.1 (rẻ, không dịch) → 3. Song song: Haiku validation pilot (D2) → 4. Nếu ranking giữ vững ở N=200: chạy Dim-B (WAI) trên S3, pilot dual-judge trước → 5. Kiểm tra tương quan WAI ↔ Alliance của Dim-A (F8) trước khi chạy WAI toàn bộ → 6. Dim-C (Trajectory) tương tự.

---

# CẤP 2 — 12 Finding chính

## F1. Ranking dataset cực kỳ ổn định — kết quả vững nhất của pilot

**Giải thích đơn giản**: Dù đổi judge (GPT↔Claude) hay đổi ngôn ngữ đánh giá (S1/S2/S3), thứ tự mạnh–yếu của 6 dataset gần như không đổi.

**Bằng chứng**: cactus (3.27–3.51) > simpsydial > Psy-Insight > PsyDial > SoulChat ≈ KMI (2.13–2.49). Spearman dataset-rank giữa mọi cặp setting: Claude = 1.000; GPT = 0.943 (S1↔S3). Dải điểm 2.13–3.51 trên thang 1–6: mọi dataset ở mức "cơ bản đến trung bình" theo rubric trị liệu.

**Lưu ý**: ổn định chỉ đúng ở **mức dataset**. Ở mức từng record, thứ hạng xê dịch nhiều theo ngôn ngữ (Spearman record-level giữa các setting chỉ ~0.5, có dataset chỉ 0.13) → mọi claim trong paper phải phát biểu ở mức dataset.

## F2. S2 bị loại khỏi ranking chéo — cả phương pháp lẫn số liệu đều xác nhận

**Giải thích**: S2 dùng judge bằng ngôn ngữ gốc của từng dataset (ZH judge cho dataset ZH, KO cho KO...) nên các điểm số không cùng một "thước đo" — không thể so chéo. Số liệu cũng xác nhận: S2 phân biệt dataset kém nhất (std 0.16–0.33) và hai judge bất đồng nhất ở S2 (ρ=0.34).

## F3. Không có self-preference bias (thiên vị tự ưu ái) "GPT dịch → GPT chấm"

**Giải thích**: Lo ngại là GPT-5.1 vừa dịch vừa chấm thì sẽ "tự khen" bản dịch của mình. Kiểm định difference-in-differences (so sánh hiệu của hiệu): nếu có bias, hiệu (điểm bản dịch − điểm bản gốc) của GPT judge phải lớn hơn của Claude judge.

**Bằng chứng**: Ngược lại trên cả 4 dataset non-EN. GPT chấm bản dịch ≈ bản gốc (Δ ≈ 0 trên ZH); Claude mới là judge chấm bản dịch CAO hơn bản gốc (+0.10 đến +0.16; DiD sig. ở simpsydial p=0.010, SoulChat p=0.021). → Quyết định chạy thêm Claude judge là đúng đắn: không tìm thấy bias như dự đoán, nhưng tìm thấy bias khác (F5).

**Giới hạn**: DiD chỉ loại được bias gắn với bước dịch; thiên vị chung với "văn phong LLM" tác động đều mọi setting thì không bắt được (xem F10).

## F4. Artifact KMI `utterance_en`: bản EN "làm sạch" sẵn trong dataset gốc làm mất điểm oan

**Giải thích**: Bản tiếng Anh có sẵn của KMI (trường `utterance_en`) là bản dịch phẳng, mất sắc thái → GPT chấm S1 của KMI thấp hơn hẳn S2/S3 (−0.26, p=0.0001, sig. trên cả 5 metric). Claude xác nhận cùng chiều nhưng yếu hơn (−0.09/−0.14, n.s.).

**Chi tiết quan trọng**: phần mất mát có ý nghĩa thống kê ở **Ethics với cả hai judge** (GPT −0.36*, Claude −0.40*) → nhiều khả năng bản phẳng làm mất sắc thái kính ngữ/lịch sự tiếng Hàn mà judge đọc thành "professional conduct". Thí nghiệm trong PLAN (dịch lại KO→EN bằng GPT-5.1: 2.672 → 3.038, gần S2) khẳng định chẩn đoán. **Bài học lớn**: chuẩn hóa/làm sạch văn bản chính là một cơ chế tạo bias — liên hệ trực tiếp đến D3.

## F5. Translation-polish bias (thiên vị do bản dịch "đánh bóng") — phụ thuộc judge

**Giải thích**: Bản dịch LLM thường mượt hơn văn gốc. Claude judge "thưởng" độ mượt này: chấm bản dịch EN cao hơn bản gốc ZH (simpsydial +0.275*, SoulChat +0.16*), tập trung đúng vào các metric đo độ trơn tru: **AIComm** (+0.51*) và **Alliance** (+0.29*). GPT judge không có hiệu ứng này.

**Hệ quả**: S1 mang artifact dịch hai chiều tùy judge (KMI bị kéo xuống với GPT; ZH bị kéo lên với Claude) → luận cứ độc lập thứ hai cho việc chọn S3.

## F6. Hai judge khác thang nghiêm khắc — lệch tập trung vào metric cụ thể

GPT chấm cao hơn Claude ~0.3 điểm, nhưng không đều: **Ethics +0.65, Clinical +0.46**, Assess +0.30, còn Alliance +0.06 và AIComm +0.02 gần như trùng. Claude dùng dải điểm rộng hơn (1.0–5.0, std 0.58) so với GPT nén (1.5–4.5, std 0.44) → Claude phân biệt record tốt hơn. **Quy tắc thực hành**: không trộn điểm raw; so sánh chéo judge chỉ qua z-score nội-judge.

## F7. Strength profile (hồ sơ thế mạnh) bất biến theo judge — judge-robust

**Giải thích**: Tuy mức điểm khác nhau, "hình dạng" mạnh–yếu tương đối của từng dataset theo 5 metric gần như trùng giữa hai judge: tương quan z-score trên 30 ô = **0.943** (từng metric: 0.88–0.99).

**Chữ ký được cả hai judge xác nhận độc lập**:
- cactus: mạnh toàn diện (z > +1 mọi metric)
- simpsydial: cân bằng, trên trung bình mọi metric
- Psy-Insight: mạnh Clinical/AIComm, Alliance là điểm hai judge lệch nhất
- PsyDial: Ethics là điểm yếu rõ (z ≈ −0.85 cả hai judge), Alliance quanh trung bình — "thân thiện nhưng lỏng chuẩn mực"
- SoulChat: yếu sâu Clinical/Assess (z ≈ −1.5) — bản chất emotional support bị rubric trị liệu phạt
- KMI: **Ethics là metric dương duy nhất** (+0.51/+0.55), Alliance/AIComm yếu nhất — "đúng mực nhưng kém kết nối", hợp bản chất MI

Đây là kết quả nên nhấn mạnh trong paper: ranking chính không phụ thuộc judge.

## F8. Halo effect (hiệu ứng hào quang): 5 metric thực chất ≈ 2 chiều

**Giải thích**: Khi judge ấn tượng tốt/xấu tổng thể, mọi metric bị kéo theo. Tương quan giữa 5 metric ở mức record: trung bình 0.71 (GPT) / 0.76 (Claude); Clinical↔Assess lên tới **0.92** (Claude) — gần như một metric. **Ethics tách biệt nhất** (tương quan 0.57–0.68 với phần còn lại) và là nơi hồ sơ dataset đảo chiều (KMI dương, PsyDial âm).

**Hệ quả**: (1) không được trình bày Clinical và Assessment như hai bằng chứng độc lập; (2) ở full N=200 nên chạy PCA/factor analysis (phân tích nhân tố); (3) khi sang WAI: kiểm tra ngay WAI↔Alliance — nếu tương quan quá cao, Dim-B thêm ít tín hiệu độc lập (bản thân điều đó cũng là finding).

## F9. AIComm: hai judge chấm hai khái niệm khác nhau dưới cùng một tên metric

**Giải thích**: Đồng thuận judge ở AIComm chỉ ρ=0.29 — thấp nhất trong 5 metric. Phân tích thinking_trace (240 đoạn lập luận) cho thấy nguyên nhân không phải nhiễu mà là **construct divergence (phân kỳ khái niệm đo)**:

| Khía cạnh trong lập luận AIComm | GPT | Claude |
|---|---|---|
| Lặp lại / công thức | 99% | 97% |
| Generic / sáo rỗng | 63% | 38% |
| Tự nhiên / giống người | 61% | 82% |
| Cấu trúc bullet/list | 13% | 54% |
| Verbosity (dài dòng) | 4% | 26% |
| Giả làm người / bịa trải nghiệm | 2% | 9% |

GPT vận hành AIComm như "độ trôi chảy − độ sáo rỗng"; Claude vận hành như **checklist failure-mode của AI** (format, verbosity, bịa trải nghiệm cá nhân) và thưởng "naturalness".

**Hai case minh họa cơ chế** (chênh lớn nhất trong 120 records):
- `psyinsight_000856` (transcript người thật, nhiều "um/hmm"): GPT 2.5 ("stilted, mechanical") vs Claude 5.0 ("remarkably natural") — cùng một đặc điểm, hai cách đọc ngược nhau.
- `psydial_511` (therapist kể ký ức cá nhân): Claude 1.5 ("fabricating personal experiences = major hallucination") vs GPT 3.0 ("subtle anthropomorphizing flavor") — Claude áp luật AI nghiêm cả lên transcript người; GPT khoan dung.

20/120 records lệch ≥1.0 điểm; lệch lớn nhất ở Psy-Insight (|Δ|=0.82) — đúng dataset human transcript nhiều disfluency. Liên kết: construct "thưởng naturalness" của Claude giải thích luôn translation-polish bias (F5) dồn vào AIComm.

**Caveat (lưu ý giới hạn) chuẩn cho paper**: "AIComm có inter-rater agreement (độ đồng thuận giữa người chấm) thấp nhất do hai judge vận hành construct khác nhau và rubric không định nghĩa cách xử lý transcript gốc human; các khác biệt trên metric này cần diễn giải thận trọng." → Sửa được bằng D3.

## F10. Confound nguồn gốc (provenance): dataset LLM-simulated chiếm trọn top-2

cactus và simpsydial — hai dataset LLM-simulated — đứng top-2 dưới *cả hai* judge, mọi setting. Vì hai judge khác gia đình cho cùng kết quả, đây không phải thiên vị theo gia đình model, nhưng nhất quán với **thiên vị chung của LLM judge với văn bản do LLM sinh** (trôi chảy, "đúng sách"). Không tách được khỏi chất lượng thật ở thiết kế hiện tại → paper phải trình bày ranking là "hồ sơ thế mạnh tương đối dưới góc nhìn LLM judge", không phải chất lượng tuyệt đối.

## F11. Vị trí cuối bảng: SoulChat, không phải KMI

Ở S3 (không artifact), cả hai judge xếp SoulChat cuối; với Claude cách biệt SoulChat–KMI có ý nghĩa mạnh (2.13 vs 2.49, p=0.001). KMI đứng cuối ở GPT-S1 chỉ là hệ quả artifact F4.

## F12. Ethics cao nhất ở mọi nơi — "an toàn bề mặt, nông về can thiệp"

Cả hai judge đều cho Ethics điểm cao nhất (GPT 3.79, Claude 3.08) trong khi Assess/AIComm thấp nhất. Diễn giải: các hội thoại giữ tone an toàn/chuyên nghiệp tốt hơn nhiều so với năng lực đánh giá lâm sàng và can thiệp sâu — một luận điểm tổng quát đáng đưa vào paper.

---

# CẤP 3 — Chi tiết kỹ thuật & vai trò thinking_trace

## 3.1 thinking_trace là gì và dùng để làm gì

thinking_trace là **bản ghi chuỗi lập luận của judge trước khi chốt điểm** — không phải tiêu chí đánh giá, không được chấm điểm, không cộng vào kết quả. Vai trò của nó là **lớp audit quy trình** áp dụng cho cả 5 metric:

1. **Construct validity audit (kiểm toán độ giá trị khái niệm)**: xác minh judge đang chấm đúng cái rubric muốn đo — chính cách này phát hiện F9.
2. **Error analysis (phân tích lỗi) trên records bất đồng**: đọc trace song song hai judge ở mọi record lệch ≥1.0 điểm để phân loại nguyên nhân (khác construct / khác mức nghiêm khắc / một bên đọc sót dữ kiện).
3. **Phát hiện rubric mơ hồ**: khi trace chứa câu tự vấn kiểu "if this is an AI… or a human transcript…" → đó là tín hiệu rubric thiếu decision rule.
4. **Bằng chứng định tính cho paper**: trích dẫn ngắn từ trace thuyết phục hơn một con số tương quan.

**Giới hạn cần khai báo**: trace là lời tự thuật của model — có thể không phản ánh trung thực hoàn toàn tính toán bên trong (vấn đề faithfulness). Dùng làm bằng chứng hỗ trợ, không phải chân lý. Trace cũng dài/ngắn khác nhau theo judge (Claude ~2.3k ký tự/metric, GPT ~0.9k) — không so độ dài như một tín hiệu chất lượng.

**Khuyến nghị**: ở full run, lặp quy trình trace-audit cho (a) Ethics — metric phân biệt tốt nhất, cần biết hai judge có cùng construct không; (b) toàn bộ records bất đồng ≥1.0; (c) WAI khi triển khai Dim-B — vì WAI có 36 items/dialogue, trace-audit trên pilot nhỏ sẽ phát hiện sớm construct divergence trước khi đốt ngân sách.

## 3.2 Vì sao luận cứ "S1 phân biệt tốt hơn" không đứng vững

GPT S1 std = 0.311 nhưng được "bơm" bởi chính artifact KMI (KMI tụt sâu làm dải điểm giãn). Tính lại với điều kiện KMI dùng bản dịch lại (S1-llm = 3.038): std = **0.246 < S3 = 0.254**. Claude non-EN: 0.383 → 0.356 ≈ S3 = 0.360. Tức sau khi tự nhất quán với điều kiện "phải sửa KMI", S1 mất hoàn toàn lợi thế phân biệt.

## 3.3 Decomposition (phân rã) hiệu ứng ngôn ngữ

- **S1−S3** = hiệu ứng bản dịch (cùng judge EN, khác input): nơi chứa mọi khác biệt đáng kể (KMI với GPT; ZH polish với Claude).
- **S3−S2** = hiệu ứng ngôn ngữ judge (cùng input gốc, khác ngôn ngữ judge): ≈ 0 ở hầu hết dataset, cả hai judge → judge EN đọc văn bản bản ngữ không lệch.
- Kết luận phân rã: **nguồn nhiễu chính là bước dịch, không phải ngôn ngữ của judge** → củng cố D1.

## 3.4 Số liệu tham chiếu nhanh

| Chỉ số | Giá trị |
|---|---|
| Spearman dataset-rank S1↔S3 | GPT 0.943 · Claude 1.000 |
| Profile concordance (z, 30 ô) | r = 0.943 |
| Judge agreement record-level theo setting | S1 0.57 · S2 0.34 · S3 0.59 |
| Judge agreement theo metric (S1) | Assess 0.57 · Ethics 0.56 · Alliance 0.50 · Clinical 0.49 · **AIComm 0.29** |
| Halo (tương quan TB giữa metric) | GPT 0.71 · Claude 0.76 (Clinical↔Assess 0.82/0.92) |
| Gap nghiêm khắc GPT−Claude | Ethics +0.65 · Clinical +0.46 · Assess +0.30 · Alliance +0.06 · AIComm +0.02 |
| DiD self-preference | âm cả 4 dataset; sig. simpsydial p=0.010, SoulChat p=0.021 |
| KMI artifact | GPT S1−S3 = −0.255 (p=0.0001); Ethics sig. cả 2 judge (−0.36*/−0.40*) |
| AIComm bất đồng ≥1.0 điểm | 20/120 records; Psy-Insight |Δ| TB = 0.82 |

## 3.5 Caveats tổng (giới hạn của toàn bộ phân tích)

1. N=20/dataset — khác biệt nhỏ giữa setting nằm dưới noise record-level; cần xác nhận ở N=200.
2. Toàn bộ là LLM-judgment, chưa có human ground truth — "chất lượng" = chất lượng theo rubric MindEval dưới góc nhìn LLM judge.
3. Confound provenance (F10) không khử được bằng chuẩn hóa.
4. Kết luận về Haiku chưa tồn tại — phải pilot trước khi dùng.
5. thinking_trace có giới hạn faithfulness (3.1).

---

# CHÚ GIẢI THUẬT NGỮ (EN → VI)

| Thuật ngữ | Nghĩa |
|---|---|
| judge | model chấm điểm |
| setting S1/S2/S3 | S1: hội thoại dịch sang EN + judge EN · S2: bản gốc + judge bản ngữ · S3: bản gốc + judge EN |
| discriminative power | độ phân biệt — khả năng tách bạch dataset mạnh/yếu (đo bằng std của các mean) |
| robustness check | kiểm tra độ bền — chạy lại theo cách khác để xem kết luận có đứng vững |
| self-preference bias | thiên vị tự ưu ái — model "khen" sản phẩm do chính nó/họ hàng nó tạo ra |
| translation-polish bias | thiên vị do bản dịch được "đánh bóng" mượt hơn bản gốc |
| difference-in-differences (DiD) | so sánh hiệu của hiệu — kỹ thuật tách một hiệu ứng khỏi các yếu tố nền |
| artifact | nhiễu giả tạo do quy trình xử lý dữ liệu, không phải tín hiệu thật |
| halo effect | hiệu ứng hào quang — ấn tượng tổng thể kéo mọi tiêu chí con theo cùng hướng |
| construct / construct validity | khái niệm đo / độ giá trị khái niệm — metric có thực sự đo đúng cái nó tuyên bố đo |
| construct divergence | phân kỳ khái niệm đo — hai người chấm hiểu cùng một metric theo hai cách khác nhau |
| inter-rater agreement | độ đồng thuận giữa các người chấm (đo bằng Spearman ρ record-level) |
| provenance | nguồn gốc dữ liệu (human transcript / LLM-simulated / single-turn) |
| confound | yếu tố gây nhiễu trộn lẫn vào kết quả, không tách được khỏi tín hiệu chính |
| blind evaluation | đánh giá mù — người chấm không biết nguồn gốc/danh tính đối tượng |
| decision rule | quy tắc quyết định — chỉ thị cụ thể trong rubric về cách xử lý tình huống mơ hồ |
| z-score | điểm chuẩn hóa — (giá trị − trung bình)/độ lệch chuẩn, cho phép so sánh khác thang |
| caveat | lưu ý giới hạn đính kèm kết luận để tránh diễn giải quá mức |
| faithfulness (của trace) | độ trung thực — lập luận viết ra có phản ánh đúng "suy nghĩ" thật của model không |
| disfluency | từ đệm/ngập ngừng tự nhiên trong lời nói ("um", "hmm") |
| fidelity reference | bản đối chiếu trung thực với bản ngữ |
| sensitivity analysis | phân tích độ nhạy — kiểm tra kết luận thay đổi thế nào khi đổi một giả định |
| factor analysis / PCA | phân tích nhân tố / phân tích thành phần chính — tìm số chiều tiềm ẩn thật sự của bộ metric |


-------
kết quả đánh giá trên 3 trục S1/S2/S3 đã chứng minh S3 tốt, do đó có thể gợi ý cho việc xây dựng dataset điều trị tham vấn tâm lý trong miền mental health bằng ngôn ngữ khác EN như ZH hoặc KO không?

15:12

Synthesized S3 findings để đề xuất chiến lược xây dựng dataset đa ngôn ngữ
Synthesized S3 findings để đề xuất chiến lược xây dựng dataset đa ngôn ngữ
Câu trả lời là có — và đây là một trong những hàm ý ứng dụng giá trị nhất của thí nghiệm, nhưng cần tách bạch rõ phần nào dữ liệu đã chứng minh và phần nào là ngoại suy cần kiểm chứng thêm.

Những gì dữ liệu đã chứng minh, và ý nghĩa cho việc xây dataset non-EN
Thứ nhất, rào cản đánh giá đã được gỡ bỏ. Phát hiện S3 ≈ S2 (judge EN đọc thẳng văn bản ZH/KO cho điểm sát judge bản ngữ, chênh ≈ 0 ở cả hai judge) nghĩa là: khi xây dataset tham vấn tâm lý bằng ZH/KO, bạn không cần dịch sang tiếng Anh để chạy quality control — hạ tầng đánh giá (rubric MindEval tiếng Anh + frontier LLM judge) dùng được trực tiếp trên văn bản gốc. Đây vốn là một trong những rào cản chi phí và phương pháp lớn nhất khi làm dataset non-EN, và pilot này cho thấy nó không tồn tại với ZH/KO ở các model hiện tại.

Thứ hai, đừng bao giờ ship bản dịch EN "làm sẵn" kèm dataset — hoặc nếu ship thì phải dùng LLM mạnh và ghi rõ. Bài học KMI: trường utterance_en phẳng làm dataset mất ~0.27 điểm oan, tổn thất tập trung ở Ethics (mất sắc thái kính ngữ tiếng Hàn). Văn bản gốc bản ngữ phải là source of truth; bản dịch kèm theo (nếu có) là tiện ích phụ và phải được QC riêng, vì người dùng dataset về sau có thể đánh giá nhầm chất lượng qua bản dịch tồi.

Thứ ba — quan trọng nhất — ngôn ngữ không phải yếu tố giới hạn chất lượng; phương pháp xây dựng mới là. Nhìn vào ranking: hai dataset ZH nằm ở cả hạng 2 (simpsydial) lẫn hạng 6 (SoulChat). Cùng một ngôn ngữ, khoảng cách gần 1 điểm. Cái phân biệt chúng là cấu trúc: simpsydial là hội thoại nhiều lượt mô phỏng phiên trị liệu đầy đủ; SoulChat thiên về empathy ngắn đơn lượt nên bị rubric phạt nặng ở Clinical/Assessment. Tức dataset ZH/KO hoàn toàn có thể đạt chất lượng cao — nếu thiết kế đúng.

Công thức thiết kế rút ra từ strength profiles
Từ hồ sơ thế mạnh của 6 dataset (đã được hai judge xác nhận độc lập, r=0.94), có thể đảo ngược thành checklist xây dựng:

Học từ cactus (hạng 1): phiên đầy đủ nhiều lượt, có khung trị liệu tường minh (CBT), tiến trình assess → can thiệp rõ ràng — mạnh đều cả 5 tiêu chí.
Tránh lỗi SoulChat: không gom các cặp hỏi-đáp an ủi ngắn rồi gọi là dữ liệu tham vấn; thiếu chiều sâu lâm sàng sẽ bị phạt ở Clinical/Assessment (z ≈ −1.5).
Tránh lỗi PsyDial: thân thiện không bù được lỏng chuẩn mực — Ethics là điểm yếu nhất quán của nó (z ≈ −0.85); cần guideline chuyên môn rõ cho người tạo hội thoại.
Học từ KMI cả hai chiều: kỹ thuật phản hồi đúng chuẩn (Ethics dương duy nhất) nhưng các đoạn utterance rời rạc làm mất Alliance/AIComm — nếu làm dataset kiểu kỹ thuật MI, vẫn cần ngữ cảnh phiên đủ dài để alliance hiển thị được.
Giữ nguyên đặc trưng bản ngữ: kính ngữ, mức độ gián tiếp, disfluency tự nhiên — bài học KMI cho thấy judge có đọc được các tín hiệu văn hóa này và chúng đóng góp điểm thật (Ethics); làm sạch chúng là tự tạo artifact.
Soạn thẳng bằng ngôn ngữ đích, không dịch từ EN sang: artifact dịch hoạt động hai chiều — dataset dịch từ EN sẽ mang translationese và mất tính bản địa, đúng cơ chế đã quan sát.
Ba điều phải kiểm chứng trước khi ngoại suy
Một, S3 ≈ S2 mới được chứng minh trên ZH và KO — hai ngôn ngữ tài nguyên lớn mà frontier model rất mạnh. Nếu mục tiêu của bạn là một ngôn ngữ khác (ví dụ tiếng Việt — tôi đoán đây có thể là hướng bạn quan tâm), thì bước đầu tiên của dự án nên là lặp lại đúng thí nghiệm S2 vs S3 này trên ~20 hội thoại pilot tiếng Việt: nếu S3 ≈ S2 tái hiện, toàn bộ hạ tầng đánh giá dùng được ngay; thiết kế thí nghiệm bạn đã có sẵn, chi phí rất nhỏ.

Hai, rubric MindEval là khung trị liệu phương Tây viết bằng tiếng Anh. S3 đo "mức tuân thủ chuẩn trị liệu phương Tây của hội thoại bản ngữ" — điều này phù hợp nếu mục tiêu dataset là huấn luyện model theo chuẩn quốc tế, nhưng nếu mục tiêu là tham vấn phù hợp văn hóa bản địa (gia đình nhiều thế hệ, kỳ thị sức khỏe tâm thần, vai trò tôn giáo...), rubric cần lớp adaptation riêng mà thí nghiệm này chưa kiểm chứng.

Ba, cảnh giác với vòng lặp tự khen. Confound provenance (F10) cho thấy LLM judge ưu ái văn bản LLM sinh ra. Nếu bạn xây dataset ZH/KO/VI bằng LLM simulation rồi QC bằng LLM judge, điểm cao một phần là bias chứ không hẳn chất lượng. Phòng vệ: trộn human transcript làm anchor, dual-judge khác gia đình model, và một lớp human expert review trên mẫu nhỏ — đặc biệt cho Ethics và an toàn lâm sàng, vốn là miền không được phép sai trong mental health.

Tóm lại: kết quả S1/S2/S3 không chỉ "cho phép" mà thực sự khuyến khích xây dataset tham vấn tâm lý bằng ngôn ngữ bản địa — vì nó chứng minh khâu đánh giá không còn cần đường vòng qua tiếng Anh, và chỉ ra đích danh những lỗi thiết kế nào sẽ bị trừ điểm. Điều kiện duy nhất là chạy pilot S2-vs-S3 cho ngôn ngữ đích trước khi cam kết, nếu đó không phải ZH/KO. Nếu bạn muốn, tôi có thể phác thiết kế thí nghiệm validation đó cho một ngôn ngữ cụ thể.

---

*File kèm theo: `tables/T13_aicomm_trace_segments.csv` (240 đoạn lập luận AIComm đã trích), `T14_aicomm_disagreements.csv` (chênh lệch per-record), `T15_aicomm_theme_frequency.csv` (tần suất chủ đề). Các bảng T0–T12 và biểu đồ C1–C11 nằm trong gói `mind_eval_analysis_N20.zip` đã giao trước đó.*
