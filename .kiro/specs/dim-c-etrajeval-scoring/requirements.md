# Requirements Document

## Introduction

Tính năng này thay thế phương pháp đánh giá **Chiều C (Dimension C)** hiện tại trong codebase nghiên cứu `mind-eval` — vốn dựa trên từ điển (lexicon-based) theo phương pháp UED (Utterance Emotion Dynamics, dùng từ điển NRC-VAD) — bằng phương pháp đánh giá quỹ đạo cảm xúc **lấy thân chủ làm trung tâm (client-centered)** dựa trên mô hình, theo bài báo *"Detecting Emotional Dynamic Trajectories: An Evaluation Framework for Emotional Support in Language Models"* (ETrajEval, arXiv 2511.09003).

Lý do thay thế: bằng chứng trong `data/cactus/results/dim_c/cactus_pilot_summary.txt` cho thấy độ phủ từ điển (lexicon coverage) chỉ khoảng ~69% (client) / ~75% (counselor) ngay cả trên dữ liệu tiếng Anh (cactus). Với các tập dữ liệu ngôn ngữ bản địa (Trung, Nhật, Hàn), độ phủ từ điển còn thấp hơn nhiều, khiến các chỉ số Chiều C (emo_mean, rise_rate, recovery_rate, peak_dist, displacement_length) trở nên thiếu tin cậy.

**Ràng buộc cốt lõi (bắt buộc):** Logic chấm điểm/tính chỉ số của ETrajEval phải được **TÁI SỬ DỤNG TỪ MÃ NGUỒN GỐC ĐÃ CÔNG BỐ** trên GitHub (https://github.com/RuoChoXio/ETrajEval, giấy phép Apache-2.0, Python) — **KHÔNG cài đặt lại (re-implement)** — nhằm đảm bảo chất lượng và tính nhất quán của kết quả. Mọi mã tùy chỉnh chỉ được phép là một lớp **adapter mỏng** bao quanh mã ETrajEval gốc, giữ nguyên không sửa đổi phần lõi scorer/metric.

Tính năng chỉ sử dụng **pha chấm điểm (run_scoring)** của ETrajEval trên các hội thoại đã có sẵn của mind-eval (cactus, AnnoMI, và các tập ngôn ngữ bản địa zh/ja/ko); **không** chạy pha sinh hội thoại/mô phỏng (run_generation).

**Ghi chú quyết định — chiến lược đa ngôn ngữ (đã xác nhận):** ETrajEval_Core chỉ hỗ trợ sẵn (native) hai ngôn ngữ `en` và `zh`, vốn đã có mục prompt sẵn và đã được bài báo kiểm chứng trên reward model (~90% với `en`, ~75% với `zh`). Vì vậy:
- **Chấm điểm bản địa (native)** cho `en` và `zh` bằng các mục prompt `en`/`zh` đã có, không sửa đổi phần lõi.
- **Với `ja` và `ko`**, hệ thống chấm điểm theo **HAI track song song** rồi so sánh kết quả với nhau và với nhãn tham chiếu, nhằm đối chiếu quỹ đạo cảm xúc từ nhiều góc nhìn (multi-perspective):
  - **Track A (translated-en):** chấm điểm **bản dịch tiếng Anh (English-translated rendition)** của các hội thoại `ja`/`ko` qua pipeline `en` đã được kiểm chứng. Bản dịch tiếng Anh là **dữ liệu đầu vào CÓ SẴN** (pre-existing), được cung cấp cùng tập dữ liệu — Adapter **KHÔNG** thực hiện bước dịch trong pipeline; hệ thống chỉ tiếp nhận (ingest) tập đã dịch sẵn này và ghi lại nguồn/provenance để tái lập.
  - **Track B (native ja/ko):** bổ sung các mục prompt bản địa `ja`/`ko` vào `sys_prompt.json` (main_template, positive_eval, negative_eval, first_turn_context, và nhãn `ja`/`ko` cho từng mục trong emotional_descriptors — các ngưỡng/thresholds vẫn là số và không đổi) rồi chấm điểm trực tiếp văn bản `ja`/`ko` gốc. Đây chỉ là **mở rộng tệp prompt (extension)**, không sửa đổi phần lõi (nhất quán với Requirement 1).
- Mục đích của việc giữ cả hai track là so sánh kết quả quỹ đạo cảm xúc từ nhiều góc nhìn. Chấm điểm bản địa `ja`/`ko` (Track B) dựa vào khả năng xuyên ngôn ngữ (cross-lingual) của reward model — điều mà bài báo **CHƯA kiểm chứng** — nên Track A (translated-en) đóng vai trò đối chiếu (cross-check). Preflight ngôn ngữ được giữ để xác minh tính đầy đủ của mục prompt `en`/`zh` (trước khi chấm bản địa) và của mục prompt `ja`/`ko` (trước khi chấm bản địa Track B).

## Glossary

- **Mind_Eval**: Codebase nghiên cứu hiện tại tại `mind-eval/`, đánh giá hội thoại hỗ trợ cảm xúc / tư vấn tâm lý theo nhiều chiều.
- **Dim_C (Chiều C)**: Chiều đánh giá động lực học quỹ đạo cảm xúc của thân chủ trong hội thoại.
- **UED_Lexicon (phương pháp cũ)**: Phương pháp đánh giá Chiều C dựa trên từ điển NRC-VAD (Utterance Emotion Dynamics), đang được thay thế.
- **ETrajEval_Core**: Mã nguồn gốc đã công bố của ETrajEval (gồm `dyn_score.py`, `model.py`, `run.py` và các tệp prompt), được tái sử dụng không sửa đổi phần lõi scorer/metric.
- **Adapter**: Lớp mã tùy chỉnh mỏng do dự án này tạo ra, chỉ làm nhiệm vụ chuyển đổi dữ liệu, cấu hình, mở rộng prompt và tổng hợp kết quả; không chứa logic chấm điểm/tính chỉ số.
- **DynamicEmotionalScorer**: Lớp trong `ETrajEval/dyn_score.py` thực hiện `analyze_conversation_and_get_trajectory(...)`, chấm điểm các lượt của thân chủ (subject = người nói đầu tiên trong log).
- **Reward_Model**: Mô hình phần thưởng bao bởi `ETrajEval/model.py` (mặc định Skywork-Reward-V2-Llama-3.1-8B qua `AutoModelForSequenceClassification`, num_labels=1), trả về logits.
- **Chat_Logs**: Tệp đầu vào của ETrajEval dạng JSON, danh sách các phần tử `{id, conversations:[{role, content}], ...}` (ví dụ `chat_logs_{language}.json`).
- **Prompts_File**: Tệp `prompts.json` của ETrajEval, cung cấp theo từng id: `param_set_key`, `initial_mu`, `psychological_theory`.
- **Param_Set_Key**: Khóa cấu hình quỹ đạo trong `dynamic_params.json`, quyết định việc bỏ qua các lượt nhiễu (disturbance turns): `medium_20_turns` bỏ lượt 21; `fast_10_turns` bỏ lượt 11/21/31; `slow_40_turns` không bỏ lượt nào.
- **Initial_Mu**: Tham số mu ban đầu của phân phối Normal(mu, sigma) dùng để lấy mẫu k tiên nghiệm (ước lượng hiệu chỉnh nhân quả, do(S_{t-1})).
- **BEL**: Baseline Emotional Level — điểm cảm xúc trung bình (≈ `average_sentiment_score` do `run.py` xuất ra).
- **ETV**: Emotional Trajectory Value — điểm quỹ đạo có trọng số (≈ `weighted_trajectory_score`, theo `weighted_trajectory_score_corrected` với trọng số = 1 − score_prev).
- **ECP**: Emotional Centroid Position — vị trí trọng tâm cảm xúc; KHÔNG do `run.py` tính, có thể suy ra từ chuỗi điểm lượt: Cx = mean(s[:-1]), Cy = mean(s[1:]).
- **Subject_Speaker**: Người nói được chấm điểm; ETrajEval coi người nói ĐẦU TIÊN trong log là subject (tức thân chủ/client).
- **Supported_Languages**: Ngôn ngữ scorer hỗ trợ sẵn (native) — `en` và `zh` (có mục prompt sẵn và đã được bài báo kiểm chứng trên reward model). Tiếng Nhật (`ja`) và Hàn (`ko`) được chấm điểm theo HAI track song song: (A) qua bản dịch tiếng Anh bằng pipeline `en` (translated-en), và (B) bản địa `ja`/`ko` bằng các mục prompt `ja`/`ko` được bổ sung vào Prompt_Files.
- **Translated_En_Rendition**: Bản dịch tiếng Anh CÓ SẴN (pre-existing) của một hội thoại `ja`/`ko`, được cung cấp như dữ liệu đầu vào và dùng để chấm điểm qua pipeline `en` (Track A). Đây KHÔNG phải do Adapter sinh ra; Adapter không thực hiện bước dịch. Nguồn/provenance của bản dịch được ghi lại để tái lập.
- **Prompt_Files**: `prompt/sys_prompt.json` (khóa: main_template, positive_eval, negative_eval, first_turn_context, emotional_descriptors) và `prompt/dynamic_params.json`. Chứa các mục ngôn ngữ `en` và `zh` có sẵn, cùng các mục `ja`/`ko` được bổ sung (extension) để phục vụ chấm điểm bản địa Track B.
- **Canonical_Interaction**: Định dạng hội thoại chuẩn của mind-eval, ví dụ `data/<dataset>/.../*_canonical.jsonl` với cấu trúc `{interaction_id, interaction:[{role, content}], metadata, extra}`.
- **Dim_C_Results_Layout**: Thư mục kết quả Chiều C của mind-eval: `data/<dataset>/results/dim_c/`.

## Requirements

### Requirement 1: Tái sử dụng mã ETrajEval gốc không sửa đổi (Ràng buộc cốt lõi)

**User Story:** Là một nhà nghiên cứu, tôi muốn tái sử dụng nguyên vẹn mã chấm điểm/tính chỉ số đã công bố của ETrajEval, để đảm bảo chất lượng và tính nhất quán của kết quả mà không phải cài đặt lại thuật toán.

#### Acceptance Criteria

1. THE Mind_Eval SHALL tích hợp (vendor) mã ETrajEval_Core từ kho lưu trữ chính thức (Apache-2.0) vào dự án dưới dạng một thư mục nguồn riêng biệt.
2. THE Mind_Eval SHALL giữ nguyên không sửa đổi nội dung logic của các tệp lõi scorer và metric của ETrajEval_Core, bao gồm `dyn_score.py` (lớp DynamicEmotionalScorer và hàm `weighted_trajectory_score_corrected`) và `model.py` (lớp Reward_Model).
3. WHERE cần hành vi tùy chỉnh, THE Mind_Eval SHALL chỉ bổ sung mã dưới dạng Adapter, tệp cấu hình, hoặc mục mở rộng prompt nằm ngoài các tệp lõi scorer/metric.
4. IF một thay đổi yêu cầu chỉnh sửa nội dung logic của tệp lõi scorer/metric của ETrajEval_Core, THEN THE Mind_Eval SHALL từ chối thay đổi đó và thực hiện thông qua Adapter hoặc cấu hình thay thế.
5. THE Mind_Eval SHALL lưu giữ tệp giấy phép Apache-2.0 gốc và ghi nhận nguồn (attribution) cho ETrajEval trong dự án.

### Requirement 2: Chỉ chạy pha chấm điểm (run_scoring)

**User Story:** Là một nhà nghiên cứu đã có sẵn các hội thoại, tôi muốn chỉ chạy pha chấm điểm của ETrajEval, để chấm điểm trên dữ liệu hiện có mà không phải sinh hội thoại mới.

#### Acceptance Criteria

1. THE Mind_Eval SHALL cấu hình ETrajEval với `run_generation: false` và `run_scoring: true`.
2. THE Mind_Eval SHALL cung cấp đường dẫn tệp Chat_Logs đầu vào qua `scoring.input_chat_log_file`.
3. WHEN pha chấm điểm chạy, THE DynamicEmotionalScorer SHALL chấm điểm chỉ các lượt của Subject_Speaker (người nói đầu tiên trong log) cho mỗi hội thoại.
4. THE Mind_Eval SHALL KHÔNG kích hoạt pha sinh hội thoại / mô phỏng (run_generation) như một mục tiêu của tính năng này.

### Requirement 3: Adapter chuyển đổi dữ liệu mind-eval sang định dạng ETrajEval

**User Story:** Là một nhà nghiên cứu, tôi muốn chuyển đổi các định dạng hội thoại của mind-eval sang định dạng đầu vào của ETrajEval, để có thể chấm điểm dữ liệu hiện có mà không sửa đổi mã lõi.

#### Acceptance Criteria

1. WHEN nhận một tệp hội thoại mind-eval (ví dụ `*_judgments.jsonl` hoặc tệp `*_canonical.jsonl` dưới `data/<dataset>/`), THE Adapter SHALL chuyển đổi tệp đó thành tệp Chat_Logs JSON theo lược đồ ETrajEval `{id, conversations:[{role, content}], ...}`.
2. WHEN xây dựng `conversations` cho mỗi hội thoại, THE Adapter SHALL sắp xếp sao cho lượt của thân chủ (client) là lượt của Subject_Speaker (người nói đầu tiên được chấm điểm).
3. IF lượt nói đầu tiên trong hội thoại nguồn là của counselor, THEN THE Adapter SHALL áp dụng quy tắc ánh xạ vai trò đã xác định để bảo đảm thân chủ được ETrajEval coi là subject.
4. THE Adapter SHALL ánh xạ các vai trò nguồn của mind-eval (ví dụ `client`, `counselor`) sang các vai trò mà ETrajEval mong đợi một cách nhất quán cho mọi hội thoại.
5. WHEN chuyển đổi xong, THE Adapter SHALL sinh tệp Prompts_File (`prompts.json`) tương ứng, cung cấp `param_set_key`, `initial_mu`, và `psychological_theory` cho từng id.
6. IF một hội thoại nguồn thiếu trường bắt buộc (ví dụ thiếu `interaction`/`conversations` hoặc rỗng), THEN THE Adapter SHALL bỏ qua hội thoại đó và ghi lại (log) lý do bỏ qua kèm định danh hội thoại.
7. IF việc chuyển đổi một hội thoại thất bại vì bất kỳ lý do nào khác (ví dụ dữ liệu sai định dạng hoặc lỗi xử lý) dù có đủ trường bắt buộc, THEN THE Adapter SHALL ghi lại (log) thất bại đó kèm định danh hội thoại và lý do.
8. WHERE chỉ tạo được một trong hai tệp đầu ra (Chat_Logs hoặc Prompts_File) cho một phần dữ liệu, THE Adapter SHALL tạo các tệp khả thi và tiếp tục xử lý các hội thoại còn lại (cho phép thành công một phần).
9. THE Adapter SHALL bảo toàn định danh hội thoại nguồn (ví dụ `interaction_id`) trong trường `id` của Chat_Logs để truy vết kết quả.

### Requirement 4: Xác định param_set_key và initial_mu cho hội thoại thực

**User Story:** Là một nhà nghiên cứu, tôi muốn xác định cách xử lý `param_set_key` và `initial_mu` cho các hội thoại thực không có sự kiện nhiễu tổng hợp, để các chỉ số quỹ đạo được tính nhất quán.

#### Acceptance Criteria

1. WHERE một hội thoại thực không có sự kiện nhiễu (disturbance) tổng hợp, THE Adapter SHALL gán `param_set_key` là giá trị không bỏ qua lượt nào (`slow_40_turns`).
2. THE Adapter SHALL gán một giá trị `initial_mu` xác định cho mọi hội thoại, là giá trị mặc định được ghi tài liệu hoặc giá trị do người dùng cấu hình (không dùng giá trị nào khác).
3. WHERE người dùng cấu hình giá trị `param_set_key` hoặc `initial_mu` khác, THE Adapter SHALL sử dụng giá trị do người dùng cấu hình thay cho mặc định.
4. THE Adapter SHALL ghi lại (log/output) giá trị `param_set_key` và `initial_mu` thực tế đã dùng cho mỗi hội thoại để bảo đảm khả năng tái lập.

### Requirement 5: Xuất chỉ số quỹ đạo lấy thân chủ làm trung tâm và tích hợp vào layout kết quả Dim C

**User Story:** Là một nhà nghiên cứu, tôi muốn nhận các chỉ số quỹ đạo cảm xúc của thân chủ và tích hợp chúng trở lại layout kết quả Chiều C của mind-eval, để so sánh và báo cáo theo cùng cấu trúc hiện có.

#### Acceptance Criteria

1. THE Mind_Eval SHALL xuất, cho mỗi hội thoại, chuỗi điểm theo lượt (per-turn scores) của thân chủ với mỗi điểm trong khoảng [0, 1].
2. THE Mind_Eval SHALL xuất chỉ số BEL (≈ `average_sentiment_score`) cho mỗi hội thoại.
3. THE Mind_Eval SHALL xuất chỉ số ETV (≈ `weighted_trajectory_score`) cho mỗi hội thoại.
4. WHERE người dùng bật tùy chọn ECP, THE Adapter SHALL tính ECP từ chuỗi điểm lượt theo Cx = mean(s[:-1]) và Cy = mean(s[1:]).
5. THE Mind_Eval SHALL tổng hợp (aggregate) các chỉ số theo từng tập dữ liệu (per dataset) và theo từng ngôn ngữ (per language).
6. THE Mind_Eval SHALL tổng hợp các chỉ số theo từng `psychological_theory` khi trường này có sẵn trong Prompts_File.
7. THE Mind_Eval SHALL ghi các tệp kết quả vào Dim_C_Results_Layout `data/<dataset>/results/dim_c/`.

### Requirement 6: Chiến lược đa ngôn ngữ — chấm bản địa en/zh; ja/ko theo hai track (translated-en và native)

**User Story:** Là một nhà nghiên cứu làm việc với dữ liệu bản địa, tôi muốn chấm điểm `en`/`zh` theo cách bản địa, và chấm `ja`/`ko` theo hai track song song (bản dịch tiếng Anh đã được kiểm chứng, và bản địa `ja`/`ko` với prompt được bổ sung), để so sánh quỹ đạo cảm xúc từ nhiều góc nhìn.

#### Acceptance Criteria

1. THE Mind_Eval SHALL chấm điểm các tập dữ liệu `en` và `zh` theo cách bản địa (native) bằng các mục prompt `en`/`zh` đã có sẵn của ETrajEval_Core mà không sửa đổi phần lõi.
2. THE Mind_Eval SHALL xác minh tính đầy đủ của các mục prompt `en` và `zh` trong Prompt_Files trước khi chấm điểm `en`/`zh`.
3. IF mục prompt `en` hoặc `zh` thiếu một khóa bắt buộc, THEN THE Mind_Eval SHALL dừng và báo lỗi mô tả rõ ngôn ngữ và khóa prompt còn thiếu trước khi chấm điểm (fail-fast).
4. WHERE tập dữ liệu là `ja` hoặc `ko`, THE Mind_Eval SHALL chấm điểm theo Track A (translated-en) bằng cách chấm điểm Translated_En_Rendition qua pipeline `en`.
5. THE Mind_Eval SHALL tiếp nhận (ingest) Translated_En_Rendition của một tập dữ liệu `ja`/`ko` như một tập dữ liệu đầu vào CÓ SẴN (pre-existing) được cung cấp, KHÔNG thực hiện bất kỳ bước dịch nào trong pipeline, và ghi lại nguồn/provenance của bản dịch để tái lập.
6. WHERE tập dữ liệu là `ja` hoặc `ko`, THE Mind_Eval SHALL chấm điểm theo Track B (native) bằng cách chấm điểm văn bản `ja`/`ko` gốc sử dụng các mục prompt bản địa `ja`/`ko`.
7. THE Mind_Eval SHALL bổ sung các mục prompt bản địa `ja`/`ko` vào `sys_prompt.json` (main_template, positive_eval, negative_eval, first_turn_context, và nhãn `ja`/`ko` cho từng mục emotional_descriptors; các ngưỡng/thresholds vẫn là số và không đổi) chỉ dưới dạng mở rộng tệp prompt (extension), không sửa đổi phần lõi (nhất quán với Requirement 1).
8. THE Mind_Eval SHALL xác minh tính đầy đủ của các mục prompt `ja` và `ko` trong Prompt_Files trước khi chấm điểm bản địa Track B.
9. IF mục prompt `ja` hoặc `ko` thiếu một khóa bắt buộc, THEN THE Mind_Eval SHALL dừng và báo lỗi mô tả rõ ngôn ngữ và khóa prompt còn thiếu trước khi chấm điểm bản địa (fail-fast).
10. WHERE tập dữ liệu là `ja` hoặc `ko`, THE Mind_Eval SHALL tạo và ghi lại kết quả cho CẢ HAI track (Track A translated-en và Track B native) để phục vụ so sánh đa góc nhìn (multi-perspective).
11. THE Mind_Eval SHALL ghi lại, cho mỗi kết quả được chấm, track/pipeline đã tạo ra kết quả đó (bản địa `en`/`zh`, translated-en, hay native `ja`/`ko`) để kết quả có thể diễn giải được.
12. THE Mind_Eval SHALL ghi tài liệu lựa chọn Reward_Model (mặc định Skywork-Reward-V2-Llama-3.1-8B) và ghi rõ rằng chấm điểm bản địa `ja`/`ko` (Track B) dựa vào khả năng xuyên ngôn ngữ (cross-lingual) của reward model mà bài báo CHƯA kiểm chứng, do đó track translated-en (Track A) được dùng làm đối chiếu (cross-check).

### Requirement 7: Xác thực chất lượng so với nhãn người và so với phương pháp từ điển cũ

**User Story:** Là một nhà nghiên cứu, tôi muốn kiểm tra tính hợp lệ của điểm dựa trên mô hình so với nhãn tham chiếu cho `en`/`zh`, đánh giá cả hai track (translated-en và native) cho `ja`/`ko` và so sánh chúng với nhau, đồng thời so sánh độ ổn định/độ phủ với phương pháp UED cũ, để xác nhận phương pháp mới đáng tin cậy.

#### Acceptance Criteria

1. THE Mind_Eval SHALL thực hiện kiểm tra hợp lệ (sanity check) so sánh điểm dựa trên mô hình với nhãn tham chiếu trên một mẫu được gán nhãn, theo từng ngôn ngữ cho `en` và `zh` (tương tự Bảng 3 của bài báo).
2. WHERE tập dữ liệu là `ja` hoặc `ko`, THE Mind_Eval SHALL báo cáo mức độ đồng thuận/chất lượng của CẢ HAI track — Track A (translated-en) và Track B (native `ja`/`ko`) — so với nhãn tham chiếu.
3. WHERE tập dữ liệu là `ja` hoặc `ko`, THE Mind_Eval SHALL so sánh kết quả của hai track (translated-en và native) với nhau để cung cấp góc nhìn đa chiều (multi-perspective).
4. WHERE tập dữ liệu là `ja` hoặc `ko`, THE Mind_Eval SHALL báo cáo độ trung thực (fidelity) của bản dịch của Track A và chất lượng chấm điểm xuyên ngôn ngữ chưa được kiểm chứng của Track B như những rủi ro cần ghi nhận.
5. THE Mind_Eval SHALL báo cáo một thước đo mức độ đồng thuận (agreement) giữa điểm mô hình và nhãn tham chiếu cho mỗi ngôn ngữ và mỗi track được xác thực.
6. THE Mind_Eval SHALL báo cáo so sánh độ ổn định (stability) và độ phủ (coverage) giữa phương pháp ETrajEval dựa trên mô hình và phương pháp UED_Lexicon cũ.
7. THE Mind_Eval SHALL ghi kết quả xác thực vào Dim_C_Results_Layout dưới dạng tệp tóm tắt có thể đọc được.

### Requirement 8: Khả năng tái lập và cấu hình hóa

**User Story:** Là một nhà nghiên cứu, tôi muốn chạy việc chấm điểm thông qua cấu hình với phiên bản phụ thuộc được ghim, để các kết quả có thể tái lập và ghi nhận nguồn đúng quy định.

#### Acceptance Criteria

1. THE Mind_Eval SHALL cho phép cấu hình đường dẫn Reward_Model, `k_samples`, `softmax_temperature`, và thiết bị (device) qua tệp cấu hình.
2. WHERE người dùng không cung cấp `k_samples` hoặc `softmax_temperature`, THE Mind_Eval SHALL sử dụng giá trị mặc định của ETrajEval (`k_samples = 8`, `softmax_temperature = 10`).
3. THE Mind_Eval SHALL ghim (pin) phiên bản các phụ thuộc (dependency) cần thiết để chạy pha chấm điểm.
4. THE Mind_Eval SHALL ghi nhận nguồn ETrajEval kèm giấy phép Apache-2.0 trong tài liệu của tính năng.
5. WHEN một lần chạy chấm điểm hoàn tất, THE Mind_Eval SHALL ghi lại các tham số cấu hình thực tế đã dùng (đường dẫn Reward_Model, k_samples, softmax_temperature, device) cùng với kết quả.

## Phạm vi ngoài (Non-Goals)

1. KHÔNG chạy pha sinh hội thoại / mô phỏng (run_generation) của ETrajEval.
2. KHÔNG cài đặt lại (re-implement) logic chấm điểm/tính chỉ số của ETrajEval; chỉ tái sử dụng mã gốc qua Adapter.
3. KHÔNG sửa đổi nội dung logic của các tệp lõi scorer/metric của ETrajEval_Core.
4. KHÔNG thay đổi cách đánh giá của các chiều khác (không phải Chiều C) trong mind-eval.
5. KHÔNG loại bỏ vĩnh viễn mã UED_Lexicon trong phạm vi tính năng này (chỉ thay thế vai trò đánh giá Chiều C); việc gỡ bỏ là quyết định riêng ngoài phạm vi.
