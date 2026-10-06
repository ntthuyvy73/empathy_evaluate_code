# Bảng tổng hợp Datasets — Audit đa chiều Empathy Datasets trong Mental Health

> Sắp xếp theo **phổ provenance 4 bậc** (Real → Semi-real → Human role-play → LLM role-play/generated)

---

## Bảng 1 — Multi-turn Datasets (đánh giá trên Dim A · Dim B · Dim C)

| # | Bậc Provenance | Dataset | Năm | Ngôn ngữ | Quy mô | Lý thuyết nền | Availability | Nội dung chính của bài báo | Vai trò trong thiết kế audit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **1 · Real counseling** | **AnnoMI** ★ | 2022 (ext. 2023) | EN | 133 dlg · ~9,700 utterances | Motivational Interviewing (MI) | Public (GitHub, Public Domain) | Dataset transcript MI thật đầu tiên được công bố công khai. Nguồn từ video demo MI chuyên nghiệp, được chuyên gia MI annotate ở cấp utterance (behaviour codes: reflection, question, giving info, MI-adherent/non-adherent). Phân tích thuộc tính ở cấp utterance, dialogue, corpus. Có nhãn chất lượng session (high/low). | **Anchor "real" duy nhất public multi-turn.** Cặp matched với KMI: cùng framework MI, khác provenance → so sánh có kiểm soát. Nhãn high/low quality → kiểm chứng external validity của Dim A. |
| 2 | 1 · Real counseling | **Psy-Insight** | 2025 | EN + ZH | 520 EN + 431 ZH sessions | Tham vấn tâm lý thật, nhiều trường phái | Public (GitHub) | Dataset song ngữ (EN/ZH) đầu tiên với annotation giải thích đa tầng cho hội thoại tham vấn tâm lý nhiều lượt. Cấu trúc phân tầng Case → Session → Turn, mỗi tầng có annotation khác nhau (phân tích ca, kế hoạch tham vấn, chiến lược từng turn). Hỗ trợ multitask learning cho LLM. | **Anchor real thứ hai.** Song ngữ nên dùng được luôn cho phân tích S1/S2/S3 mà không đổi nội dung. Annotation giải thích giúp đối chiếu với thinking trace của judge. |
| 3 | **2 · Semi-real** (tái dựng từ dữ liệu thật) | **PsyDial** | 2025 | ZH | ~2,400 dlg · avg 37.8 turns · ~7M tokens | Humanistic + PD + CBT | Public (GitHub) | Dataset tham vấn tâm lý quy mô lớn, xây dựng bằng pipeline RMRR (Retrieve–Mask–Reconstruct–Refine) từ hội thoại counselor-client thật. Bảo vệ quyền riêng tư bằng masking thông tin nhạy cảm rồi dùng LLM tái dựng. Đánh giá bằng human experts xác nhận chất lượng lâm sàng. | Đại diện bậc 2 chính. So với CPsyCoun trong cùng bậc, cùng ZH: hai pipeline tái dựng khác nhau. |
| 4 | 2 · Semi-real | **CPsyCoun** ★ | 2024 | ZH | 3,134 dlg | 9 loại tham vấn · 7 trường phái | Public (GitHub/HF) — CPsyCounR cần ký thỏa thuận | Đề xuất framework tái dựng hội thoại tham vấn từ báo cáo tâm lý (case report). Phase 1: LLM đóng vai "supervisor" trích thông tin + lập kế hoạch. Phase 2: LLM đóng vai "counselor" sinh hội thoại theo kế hoạch. Benchmark đánh giá gồm 4 tiêu chí: toàn diện, chuyên môn, chân thực, an toàn (ACL 2024 Findings). | So sánh pipeline semi-real cùng ngôn ngữ với PsyDial. Phương pháp Memo2Demo minh họa xu hướng xây dataset từ case report. |
| 5 | **3 · Human role-play** (người được huấn luyện) | **KokoroChat** ★ | 2025 | JA | 6,589 dlg · 600K utterances | Tham vấn tâm lý tổng quát | Public (GitHub/HF, CC BY-NC-ND) | Dataset hội thoại tham vấn JA lớn nhất tính đến 06/2025, thu thập bằng role-play giữa 480 counselor được huấn luyện 10 giờ. Counselor dùng keyboard, client dùng LINE — mô phỏng tham vấn online thật. Mỗi dialogue kèm client feedback chi tiết đánh giá chất lượng tham vấn. Fine-tune LLM trên dataset cải thiện cả sinh response lẫn tự động đánh giá (ACL 2025 Main). | **Thay thế EmplifAI.** Đại diện bậc 3 chất lượng cao; so với bậc 4 trả lời "người đóng vai vs LLM đóng vai". Có sẵn client feedback → đối chiếu với Dim B. |
| 6 | 3 · Human role-play (crowdsource) | **ESConv** | 2021 | EN | 1,300 dlg · 31K utterances | Hill's Helping Skills (Exploration–Comforting–Action) | Public (GitHub/HF) | Định nghĩa task Emotional Support Conversation. Thu thập bằng crowdworker (seeker + supporter) được huấn luyện qua tutorial. Mỗi supporter turn annotate 1/8 strategy labels. Seeker tự báo cáo emotion type, intensity trước/sau và feedback 1–5 sao trong quá trình hội thoại. Đánh giá baseline cho thấy strategy-aware model vượt trội (ACL 2021). | **Đưa lại vào đánh giá.** Có self-report cảm xúc trước/sau → anchor validate estimator Dim C. Bậc 3 EN duy nhất. |
| 7 | **4 · LLM role-play** | **CACTUS** | 2024 | EN | 31,577 dlg · ~1M utterances · avg 16.6 turns | CBT (Cognitive Behavioral Therapy) | Public (GitHub) | Dataset multi-turn mô phỏng phiên CBT thật bằng LLM. Client có persona đa dạng + thái độ khác nhau (tích cực/trung tính/tiêu cực). Counselor áp dụng kỹ thuật CBT có kế hoạch. Đề xuất COUNSELINGEVAL framework đánh giá kỹ năng counselor + thay đổi cảm xúc client theo tiêu chí tâm lý học (EMNLP 2024 Findings). | Anchor synthetic hạng 1 hiện tại của pilot. Có CBT plan rõ ràng → kiểm chứng strength profile (F7: metric phản ánh theory grounding). |
| 8 | 4 · LLM role-play | **SimPsyDial** | 2024 | ZH | 1,000 dlg · avg 13 turns | Hill's (2009) + Tích hợp CC/PD/CBT | Public (GitHub) | Hội thoại tham vấn ZH sinh bằng GPT-4 role-play. Tích hợp nhiều trường phái (Client-Centered, Psychodynamic, CBT) qua framework Helping Skills. Mỗi dialogue có nhãn chiến lược và giai đoạn trị liệu. | Đã có pilot S1/S2/S3 đầy đủ. Dùng làm reference khi mở rộng thiết kế ngôn ngữ. |
| 9 | 4 · LLM-generated | **SoulChat** | 2023 | ZH | ~2.3M samples | Empathy-centered (lắng nghe, an ủi, tin tưởng) | Public | Dataset quy mô rất lớn, LLM sinh ra để cải thiện khả năng empathy, lắng nghe và an ủi của chatbot. Tập trung vào emotional support hơn là tham vấn lâm sàng có cấu trúc. Fine-tune SoulChat model trên dataset này (EMNLP 2023 Findings). | Đại diện "emotional support thuần" — case bị rubric trị liệu phạt (F7: SoulChat yếu Clinical/Assessment). Minh họa ranh giới empathy ≠ counseling. |
| 10 | 4 · LLM role-play | **KMI** | 2025 | KO | 1,000 dlg | Motivational Interviewing (MI) | Public (NAACL 2025) | Dataset hội thoại MI tiếng Hàn sinh bằng GPT-4 + MI forecasting. Mô phỏng quy trình MI với client personas và giai đoạn thay đổi hành vi. | **Cặp matched với AnnoMI** (cùng MI). Đã có pilot: phát hiện translation artifact (F4) và strength profile "đúng mực nhưng kém kết nối" (F7). |
| 11 | 4 · LLM-expanded | **SMILE (SmileChat)** ★ | 2023 (EMNLP 2024) | ZH | 55,165 dlg · avg 10.4 turns | Tham vấn tâm lý (kế thừa PsyQA) | Public (GitHub/HF) | Đề xuất kỹ thuật SMILE: dùng ChatGPT mở rộng cặp QA đơn lượt (từ PsyQA) thành hội thoại nhiều lượt. Phân tích tính khả thi qua language transformation analysis + đánh giá đa dạng (lexical, semantic, topical). Train chatbot MeChat; đánh giá bằng cả automatic và human evaluation so với dữ liệu tham vấn thật. | **Ablation sạch nhất toàn bài:** cùng nội dung nguồn với PsyQA (Bảng 2), chỉ khác bước "LLM hóa" → đo trực tiếp ảnh hưởng của LLM expansion lên chất lượng. |
| — | *(2 · Semi-real, multi-session)* | ***MusPsy*** *(case study)* | 2025 | ZH | Multi-session / client | Tham vấn tâm lý theo tiến trình | Cần xác minh repo (HIT-SCIR) | Đề xuất dataset multi-session đầu tiên cho tham vấn tâm lý tự động. Xây từ profile client thật (case report công khai), mô hình hóa therapeutic arc qua nhiều session liên tiếp. Phát triển MusPsy-Model để theo dõi tiến triển client và điều chỉnh hướng tham vấn theo thời gian. Đánh giá bằng GPT-4o + human trên 4 metric + 3 chiều WAI. | **Section mở rộng riêng** (10–15 case). Kiểm chứng framework mở rộng sang multi-session. Đối chiếu alliance xuyên session với finding "alliance không tăng theo session" của bài Alliance. |

### Tổng kết phổ provenance (Multi-turn)

| Bậc | Số dataset | Đại diện |
|---|---|---|
| 1 · Real counseling | 2 | AnnoMI (EN), Psy-Insight (EN+ZH) |
| 2 · Semi-real | 2 (+1 multi-session) | PsyDial (ZH), CPsyCoun (ZH), MusPsy (ZH, case study) |
| 3 · Human role-play | 2 | KokoroChat (JA), ESConv (EN) |
| 4 · LLM role-play/generated | 5 | CACTUS (EN), SimPsyDial (ZH), SoulChat (ZH), KMI (KO), SMILE (ZH) |

### Cặp đối chứng chính (Matched Pairs)

| Cặp | Biến kiểm soát | Câu hỏi trả lời |
|---|---|---|
| **AnnoMI ↔ KMI** | Cùng MI, khác provenance (real vs LLM) | Phương thức thu thập ảnh hưởng thế nào khi cùng framework? |
| **KokoroChat ↔ CACTUS / SimPsyDial** | Cùng role-play, khác actor (người vs LLM) | Người đóng vai vs LLM đóng vai tạo chất lượng khác nhau thế nào? |
| **PsyDial ↔ CPsyCoun** | Cùng bậc 2, cùng ZH, khác pipeline tái dựng | Pipeline semi-real nào cho chất lượng cao hơn? |
| **PsyQA (Bảng 2) ↔ SMILE** | Cùng nội dung nguồn, khác cấu trúc (ST→MT) | LLM expansion ảnh hưởng thế nào đến chất lượng? |
| **ESConv ↔ CACTUS** | Cùng EN, khác provenance (crowd vs LLM) | Crowdsource vs LLM synthetic trong cùng ngôn ngữ? |

---

## Bảng 2 — Single-turn Datasets (đánh giá trên 7 metrics MentalChat16K)

| # | Bậc Provenance | Dataset | Năm | Ngôn ngữ | Quy mô | Nguồn gốc cụ thể | Availability | Nội dung chính của bài báo | Vai trò trong thiết kế audit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **1 · Real** (web crawl) | **PsyQA** | 2021 | ZH | 22K Q / 56K A | Crawl từ nền tảng tham vấn online 壹心理 (Yixinli) | Public | Dataset QA tiếng Trung quy mô lớn thu thập từ nền tảng tham vấn tâm lý trực tuyến. Mỗi câu hỏi do người dùng thật đặt, mỗi câu trả lời do supporter/counselor viết. Annotate chiến lược hỗ trợ theo Hill's Helping Skills. Phân tích đặc trưng ngôn ngữ và kỹ thuật hỗ trợ trong dữ liệu. | **Anchor real ZH.** Nguồn gốc của SMILE (Bảng 1) → nối hai bảng, tạo cặp ablation ST↔MT. |
| 2 | 1 · Real (therapist response) | **CounselChat** ★ | 2020 | EN | 940 Q / 2,775 QA pairs | 433 therapist có giấy phép trả lời trên CounselChat.com | Public (GitHub/HF, MIT) | Tập dữ liệu scrape từ CounselChat.com — nền tảng nơi therapist có giấy phép hành nghề trả lời câu hỏi tâm lý để xây dựng uy tín. Mỗi QA pair có số upvote và lượt view, cho phép đánh giá chất lượng response theo cộng đồng. Bao phủ nhiều chủ đề: lo âu, trầm cảm, trauma, self-esteem, relationships. | **Anchor real EN** — nhánh single-turn hiện thiếu đối trọng EN-real. Có upvote → proxy chất lượng từ cộng đồng. Cùng phân bố topic với MentalChat16K Synthetic. |
| 3 | **2 · Semi-real** (audio → QA) | **Psych8K (ChatPsychiatrist)** ★ | 2023 | EN | 8,187 QA pairs từ 260 bản ghi âm | Transcript tham vấn thật → chuyển đổi thành QA | Public (GitHub) | Xây dataset từ 260 bản ghi âm tham vấn tâm lý thật, chuyển đổi thành cặp QA. Đào tạo ChatPsychiatrist — LLM chuyên biệt cho QA counseling tiếng Anh đầu tiên. Là baseline chính mà MentalChat16K so sánh (gấp đôi quy mô Psych8K). | Bậc 2 single-turn; chính là baseline MentalChat16K so sánh → context cho cặp Interview↔Synthetic. |
| 4 | 2 · Semi-real (transcript → QA) | **MentalChat16K — Interview** ★ | 2025 | EN | 9,775 QA pairs từ 378 sessions / 514 caregivers | Transcript clinical trial thật, paraphrase local bằng Mistral-7B | Public (HF) | Một nửa dataset MentalChat16K. Nguồn từ clinical trial can thiệp problem-solving therapy cho caregivers bệnh nhân hospice/palliative. Audio → human transcription → paraphrase cục bộ bằng Mistral-7B (không upload cloud vì privacy). Lọc QA < 40 từ + kiểm tra thủ công xóa PII. | Một nửa cặp đối chứng Interview↔Synthetic: **cùng paper, cùng format, cùng ngôn ngữ, khác provenance.** |
| 5 | **4 · LLM-generated** | **MentalChat16K — Synthetic** ★ | 2025 | EN | 6,338 QA pairs · 33 topics | GPT-3.5 Turbo sinh theo framework Airoboros, phân bố topic CounselChat | Public (HF) | Nửa còn lại của MentalChat16K. GPT-3.5 Turbo sinh patient queries theo 33 chủ đề (phân bố theo CounselChat), rồi sinh counselor responses. 100 mẫu human review. Paper gốc phát hiện: GPT-4 judge thiên vị phần synthetic; Gemini Pro ưu tiên interview data → bằng chứng cho dual-judge. 7 metrics validate bởi GPT-4 + Gemini Pro + human experts (KDD 2025). | Nửa kia cặp: matched pair tinh khiết nhất cho single-turn. Paper gốc cũng là nguồn 7 metrics → khai báo caveat khi đánh giá. |

### Tổng kết phổ provenance (Single-turn)

| Bậc | Số dataset | Đại diện |
|---|---|---|
| 1 · Real | 2 | PsyQA (ZH), CounselChat (EN) |
| 2 · Semi-real | 2 | Psych8K (EN), MentalChat16K Interview (EN) |
| 3 · Human role-play | 0 | *(Ô trống — observation đáng ghi: không ai thuê người đóng vai viết QA đơn lượt)* |
| 4 · LLM-generated | 1 | MentalChat16K Synthetic (EN) |

### Cặp đối chứng chính (Matched Pairs — Single-turn)

| Cặp | Biến kiểm soát | Câu hỏi trả lời |
|---|---|---|
| **MentalChat16K Interview ↔ MentalChat16K Synthetic** | Cùng paper, cùng format, cùng ngôn ngữ | Human-origin vs LLM-generated ảnh hưởng thế nào khi mọi thứ khác giống nhau? |
| **CounselChat ↔ MentalChat16K Synthetic** | Cùng phân bố topic (CounselChat là nguồn topic) | Real therapist vs LLM sinh: chênh lệch lớn nhất ở metric nào? |
| **PsyQA ↔ CounselChat** | Cùng bậc 1, khác ngôn ngữ (ZH vs EN) | Ngôn ngữ ảnh hưởng thế nào ở cùng bậc real? (áp dụng S1/S3 cho PsyQA) |

---

## Ghi chú

- ★ = dataset mới đề xuất bổ sung (chưa có trong slide gốc)
- Bậc 3 single-turn trống: đây là observation tự nhiên đáng ghi trong paper — cấu trúc QA đơn lượt hầu như chỉ được xây bằng crawl thật hoặc LLM sinh, không ai thuê người đóng vai viết Q&A
- **MusPsy** được đặt ngoài bảng chính, ở section case study riêng vì: (1) không có đối thủ multi-session để so sánh, (2) đơn vị phân tích khác (case → sessions → turns), (3) availability cần xác minh
- Tổng: **11 multi-turn + 5 single-turn = 16 datasets** (+ 1 case study MusPsy)
