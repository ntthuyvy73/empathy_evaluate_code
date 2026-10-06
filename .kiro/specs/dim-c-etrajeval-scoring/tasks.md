# Implementation Plan: dim-c-etrajeval-scoring

## Overview

Kế hoạch này hiện thực một **lớp adapter mỏng** (Python) bao quanh mã ETrajEval đã được **vendor nguyên vẹn** tại `vendor/etrajeval/`, theo đúng ràng buộc cốt lõi của Requirement 1 (KHÔNG sửa logic lõi `dyn_score.py` / `model.py` / `run.py`). Mọi tùy biến nằm ở `src/dim_c_etraj/` + cấu hình + mở rộng tệp prompt + tích hợp kết quả vào layout Chiều C.

Ngôn ngữ triển khai: **Python**; kiểm thử thuộc tính dùng **Hypothesis** (tối thiểu 100 vòng/lặp). 13 correctness property của thiết kế mỗi cái được hiện thực bằng đúng một property test, gắn nhãn theo định dạng `Feature: dim-c-etrajeval-scoring, Property {n}: {text}`.

Lưu ý quan trọng về trạng thái vendored đã xác minh tại chỗ:
- Mã đã có sẵn ở `vendor/etrajeval/ETrajEval/{dyn_score.py, model.py, run.py, chat_env.py, dataloader.py, config.yaml}` và `vendor/etrajeval/ETrajEval/prompt/{sys_prompt.json, dynamic_params.json}`.
- **KHÔNG có tệp `LICENSE` riêng**; điều khoản Apache-2.0 nằm trong `vendor/etrajeval/SECURITY.md`. Tác vụ attribution phải tham chiếu `SECURITY.md` và bổ sung `NOTICE`/`ATTRIBUTION.md`.
- Tồn tại **nested `.git`** tại `vendor/etrajeval/.git` → cần gỡ sớm để không thành submodule, rồi mới lập checksum baseline.
- Hợp đồng scoring đã xác minh: `run.py` xây `prompt_map = {p['id']: p for p in prompts_data}` và chỉ chấm các id khớp; pha scoring chỉ đọc `id, param_set_key, initial_mu, psychological_theory` từ mỗi mục `prompts.json` (các trường sinh-hội-thoại như `character_settings`/`initial_dialogue`/`aggravating_events` KHÔNG cần cho scoring). `chat_logs` dùng `{id, conversations:[{role,content}]}` với id khớp `prompts.json`.
- Đã xác minh: `DynamicEmotionalScorer` index prompt theo `self.language`, không có hard guard `en`/`zh` → `ja`/`ko` chạy được chỉ bằng thêm khóa prompt + đặt `language`, KHÔNG sửa core.

## Tasks

- [ ] 1. Khởi tạo cấu trúc adapter và vendoring hygiene
  - [ ] 1.1 Tạo cấu trúc gói adapter và tệp cấu hình mind-eval
    - Tạo gói `src/dim_c_etraj/` với `__init__.py` và các module rỗng/skeleton: `converter.py`, `translated_en_ingest.py`, `prompt_extension.py`, `preflight.py`, `config_gen.py`, `runner.py`, `orchestrator.py`, `metrics.py`, `results_writer.py`, `validation.py`, `cli.py`
    - Tạo `config/dim_c_etraj.yaml` với các khóa cấu hình phía mind-eval: `reward_model_path`, `reward_model_device`, `k_samples`, `softmax_temperature`, `compute_ecp` (mặc định false), đường dẫn vendored `run.py`/`config.yaml`, và thư mục đầu vào/đầu ra
    - Tạo thư mục test `tests/dim_c_etraj/` và cấu hình Hypothesis (profile tối thiểu 100 vòng lặp)
    - _Requirements: 8.1, 8.2_

  - [ ] 1.2 Vendoring hygiene + attribution + ghim phụ thuộc
    - Gỡ thư mục nested `.git` tại `vendor/etrajeval/.git` để vendored core không bị coi là submodule
    - Ghi provenance: tạo `vendor/etrajeval/PROVENANCE.md` ghi URL kho gốc (https://github.com/RuoChoXio/ETrajEval) và commit hash đã tải về
    - Tạo `vendor/etrajeval/ATTRIBUTION.md` và `NOTICE` ghi nhận ETrajEval theo Apache-2.0, **trỏ tới `vendor/etrajeval/SECURITY.md`** (nơi chứa điều khoản Apache-2.0) thay vì một tệp `LICENSE` không tồn tại
    - Ghim phụ thuộc: sinh `requirements-etraj.lock` từ `vendor/etrajeval/requirements.txt` (pin phiên bản chính xác) để chạy pha scoring tái lập được
    - _Requirements: 1.1, 1.5, 8.3, 8.4_

  - [ ]* 1.3 Viết test core-integrity checksum baseline
    - Ghi baseline checksum (SHA-256) cho `vendor/etrajeval/ETrajEval/{dyn_score.py, model.py, run.py}` **SAU khi** đã gỡ nested `.git` (task 1.2)
    - Test `tests/dim_c_etraj/test_core_integrity.py` so checksum hiện tại với baseline; fail nếu lệch (chặn mọi sửa đổi lõi)
    - Kiểm tra tồn tại `ATTRIBUTION.md`/`NOTICE` trỏ `SECURITY.md` Apache-2.0 và tồn tại `requirements-etraj.lock`
    - _Requirements: 1.2, 1.4, 1.5, 8.3, 8.4_

- [ ] 2. DataConverter, role-reorder và PromptsBuilder (converter.py)
  - [ ] 2.1 Định nghĩa data models của converter
    - Trong `converter.py` định nghĩa dataclass `ConversionConfig` (default `param_set_key="slow_40_turns"`, `initial_mu=-2.0`, override fields, `theory_field="extra.topic_group"`, `theory_default="N/A"`), `SkipRecord{interaction_id, reason}`, `ConversionResult{chat_logs, prompts, skipped, errors}`
    - _Requirements: 3.1, 4.1, 4.2_

  - [ ] 2.2 Hiện thực role-reorder (Phương án A) và convert_file
    - Hiện thực `DataConverter._reorder_roles`: nếu `interaction[0].role == "counselor"` thì loại đúng lượt counselor mở đầu để client thành phần tử `[0]`; nếu bắt đầu bằng client thì giữ nguyên; ánh xạ `client→"client"`, `counselor→"counselor"`
    - Hiện thực `convert_file` + `_split_by_language` (dùng `metadata.language`) sinh `chat_logs_<lang>.json` dạng `{id, conversations:[{role,content}], source_meta}`, bảo toàn `interaction_id → id`
    - Xử lý biên: `empty_interaction`, `missing_field`, `no_client_turn` → ghi `skipped`; lỗi khác → ghi `errors`; cô lập lỗi theo từng hội thoại (thành công một phần)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7, 3.8, 3.9, 5.5_

  - [ ]* 2.3 Property test Property 2 (thân chủ luôn ở vị trí [0])
    - **Property 2: Thân chủ luôn là subject ở vị trí [0] (drop leading counselor)**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 2: Với mọi canonical interaction có ít nhất một lượt client, sau khi chuyển đổi, conversations[0] PHẢI là một lượt của client; và nếu interaction nguồn bắt đầu bằng counselor thì đúng một lượt counselor mở đầu bị loại bỏ, còn thứ tự tương đối của các lượt còn lại được bảo toàn.`
    - Hypothesis ≥ 100 vòng; generator bao phủ bắt đầu bằng client/counselor, số lượt lẻ, lượt liên tiếp cùng vai trò
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 2.4 Property test Property 1 (bảo toàn lược đồ và định danh)
    - **Property 1: Chuyển đổi bảo toàn lược đồ và định danh**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 1: Với mọi canonical interaction hợp lệ (có ít nhất một lượt client), bản ghi chat_logs sinh ra PHẢI tuân thủ lược đồ {id, conversations:[{role, content}], ...}, trong đó id == interaction_id và mọi role thuộc tập vai trò ETrajEval mong đợi.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 3.1, 3.4, 3.9**

  - [ ]* 2.5 Property test Property 3 (cô lập lỗi theo lô — thành công một phần)
    - **Property 3: Cô lập lỗi theo lô — thành công một phần**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 3: Với mọi lô bản ghi trộn lẫn (hợp lệ và không hợp lệ), mọi bản ghi hợp lệ vẫn được chuyển đổi thành công và xuất hiện trong đầu ra, không phụ thuộc vào sự hiện diện của bất kỳ bản ghi không hợp lệ nào.`
    - Hypothesis ≥ 100 vòng; generator trộn bản ghi hợp lệ/không hợp lệ theo thứ tự bất kỳ
    - **Validates: Requirements 3.8**

  - [ ]* 2.6 Property test Property 4 (bản ghi không hợp lệ bị bỏ qua/ghi lỗi kèm id + lý do)
    - **Property 4: Bản ghi không hợp lệ bị bỏ qua/ghi lỗi kèm định danh và lý do**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 4: Với mọi bản ghi thiếu trường bắt buộc (thiếu/rỗng interaction, hoặc không có lượt client), bản ghi đó PHẢI bị loại khỏi đầu ra VÀ phải xuất hiện trong danh sách skipped/errors kèm interaction_id và một lý do khác rỗng.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 3.6, 3.7**

  - [ ] 2.7 Hiện thực PromptsBuilder sinh prompts.json
    - Trong `converter.py` hiện thực `PromptsBuilder`: mỗi `id` → `{param_set_key, initial_mu, psychological_theory}` (chỉ bốn trường scoring cần thiết)
    - `param_set_key` = override nếu có, ngược lại `"slow_40_turns"`; `initial_mu` = override nếu có, ngược lại `-2.0`; `psychological_theory` suy từ `extra.topic_group`, thiếu → `"N/A"`
    - _Requirements: 3.5, 4.1, 4.2, 4.3, 5.6_

- [ ] 3. ConfigGenerator và RunManifest (config_gen.py)
  - [ ] 3.1 Hiện thực ConfigGenerator sinh config.yaml ETrajEval
    - `write_etraj_config(sc: ScoringConfig, out_path)` luôn đặt `execution_phases.run_generation=false`, `run_scoring=true`; ánh xạ `reward_model_path`, `reward_model_device`, `k_samples` (mặc định 8), `softmax_temperature` (mặc định 10), `language`, `track`, `input_chat_log_file`, `prompt_file`, `compute_ecp`
    - Định nghĩa dataclass `ScoringConfig` theo thiết kế
    - _Requirements: 2.1, 2.2, 2.4, 8.1, 8.2_

  - [ ] 3.2 Hiện thực RunManifest ghi tham số hiệu lực
    - `RunManifest.record(effective_params, per_conv_params)` ghi `reward_model_path`, `device`, `k_samples`, `softmax_temperature`, `language`, `track`, `compute_ecp`, `dependency_lock`, và `per_conversation_params` (param_set_key/initial_mu theo id)
    - _Requirements: 4.4, 8.5_

  - [ ]* 3.3 Property test Property 9 (sinh cấu hình & manifest đúng đắn)
    - **Property 9: Sinh cấu hình & manifest đúng đắn**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 9: Với mọi ScoringConfig, tệp config.yaml sinh ra PHẢI luôn đặt execution_phases.run_generation=false và run_scoring=true; các giá trị reward_model_path, k_samples, softmax_temperature, device cấu hình được phải xuất hiện đúng (áp mặc định k_samples=8, softmax_temperature=10 khi thiếu); và RunManifest phải ghi lại đúng các tham số hiệu lực này.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 2.1, 2.4, 8.1, 8.2, 8.5**

  - [ ]* 3.4 Property test Property 5 (phân giải tham số quỹ đạo + ghi nhận tái lập)
    - **Property 5: Phân giải tham số quỹ đạo nhất quán và ghi nhận tái lập được** (PromptsBuilder ↔ RunManifest)
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 5: Với mọi tập id được chuyển đổi, mỗi mục prompts.json PHẢI có đủ param_set_key, initial_mu, psychological_theory; khi không có override thì param_set_key == "slow_40_turns" và initial_mu bằng đúng giá trị mặc định; khi có override thì mọi mục dùng giá trị override; và giá trị ghi trong RunManifest trùng khớp với giá trị phát ra trong prompts.json.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [ ] 4. Checkpoint — Đảm bảo các test hiện có đều pass
  - Đảm bảo tất cả test pass, hỏi người dùng nếu có vướng mắc.

- [ ] 5. TranslatedEnIngest — Track A cho ja/ko (translated_en_ingest.py)
  - [ ] 5.1 Hiện thực TranslatedEnIngest (ingest bản dịch en CÓ SẴN, KHÔNG dịch)
    - `ingest(translated_path, prov: TranslatedEnProvenance) -> ConversionResult`: đọc bản dịch tiếng Anh CÓ SẴN, KHÔNG thực hiện bước dịch; áp cùng role-reorder + PromptsBuilder của `converter.py`
    - Gắn thẻ track `translated-en`, pipeline ngôn ngữ `en`; đính `TranslatedEnProvenance{source_language ∈ {ja,ko}, translation_source, translation_ref, note}`
    - Báo lỗi rõ ràng nếu tệp bản dịch thiếu/không tồn tại (không tự dịch thay thế)
    - _Requirements: 6.4, 6.5_

  - [ ]* 5.2 Property test Property 13 (Track A ingest — không dịch, có provenance)
    - **Property 13: Track A ingest bản dịch CÓ SẴN — không dịch, có provenance**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 13: Với mọi bản dịch tiếng Anh đầu vào của một hội thoại ja/ko, TranslatedEnIngest PHẢI bảo toàn nguyên trạng nội dung văn bản tiếng Anh (không thực hiện bước dịch nào), gắn thẻ kết quả là translated-en và đính kèm provenance khác rỗng với source_language ∈ {ja, ko} và một tham chiếu nguồn bản dịch khác rỗng.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 6.4, 6.5**

- [ ] 6. PromptExtension — Track B native ja/ko (prompt_extension.py)
  - [ ] 6.1 Hiện thực PromptExtension (mở rộng BẢN SAO sys_prompt.json, không sửa core)
    - Tạo/ghi vào một **bản sao mở rộng** của `sys_prompt.json` (không chỉnh tệp gốc trong vùng core logic): thêm khóa `ja`/`ko` cho `main_template`, `positive_eval`, `negative_eval`, `first_turn_context`, và bổ sung nhãn `ja`/`ko` cho từng phần tử `emotional_descriptors` (giữ nguyên `threshold` dạng số: `-2.5,-1.5,-0.5,0.5,1.5,2.5,999999`)
    - Đây chỉ là mở rộng tệp prompt (extension), không sửa logic Core (nhất quán R1.3)
    - _Requirements: 6.6, 6.7_

  - [ ]* 6.2 Viết unit test cho PromptExtension
    - Kiểm tra bản mở rộng chứa đầy đủ khóa `ja`/`ko` ở mọi trường bắt buộc và `emotional_descriptors` có nhãn `ja`/`ko`; `threshold` không đổi và vẫn là số
    - Kiểm tra tệp core gốc không bị thay đổi (so với core-integrity)
    - _Requirements: 6.6, 6.7_

- [ ] 7. LanguagePreflight (preflight.py)
  - [ ] 7.1 Hiện thực LanguagePreflight (en/zh + ja/ko, fail-fast)
    - Trước khi chấm, với mỗi ngôn ngữ yêu cầu ∈ `{en, zh, ja, ko}`, kiểm tra mọi khóa prompt bắt buộc tồn tại đầy đủ (`en`/`zh` cho bản địa và pipeline Track A; `ja`/`ko` cho Track B)
    - Nếu thiếu bất kỳ khóa nào → dừng và phát lỗi nêu rõ ngôn ngữ + (các) khóa còn thiếu trước khi chấm
    - _Requirements: 6.2, 6.3, 6.8, 6.9_

  - [ ]* 7.2 Property test Property 10 (preflight ngôn ngữ chuẩn xác, báo lỗi mô tả)
    - **Property 10: Preflight ngôn ngữ chuẩn xác cho en/zh VÀ ja/ko, báo lỗi mô tả**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 10: Với mọi ngôn ngữ được yêu cầu thuộc {en, zh, ja, ko}, LanguagePreflight PHẢI vượt qua khi và chỉ khi mọi khóa prompt bắt buộc tồn tại đầy đủ; ngược lại, nếu thiếu bất kỳ khóa nào thì preflight PHẢI dừng (fail-fast) và phát lỗi nêu rõ tên ngôn ngữ và (các) khóa còn thiếu, trước khi chấm điểm.`
    - Hypothesis ≥ 100 vòng; generator bỏ khóa ngẫu nhiên cho cả `en`/`zh` và `ja`/`ko`
    - **Validates: Requirements 6.2, 6.3, 6.8, 6.9**

- [ ] 8. MetricsAdapter (metrics.py)
  - [ ] 8.1 Hiện thực ánh xạ BEL/ETV và turn_scores
    - Đọc `answer_dialogues_<track>.json`; ánh xạ `BEL = avg_sentiment`, `ETV = weighted_trajectory_score` không biến đổi; bảo toàn nguyên vẹn chuỗi `turn_scores`
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 8.2 Property test Property 7 (ánh xạ chỉ số trung thực với đầu ra Core)
    - **Property 7: Ánh xạ chỉ số trung thực với đầu ra Core**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 7: Với mọi bản ghi trong answer_dialogues_<lang>.json, MetricsAdapter PHẢI ánh xạ BEL == avg_sentiment và ETV == weighted_trajectory_score mà không biến đổi giá trị, và bảo toàn nguyên vẹn chuỗi turn_scores.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 5.2, 5.3**

  - [ ] 8.3 Hiện thực ECP (tùy chọn, mặc định TẮT) với Cy − Cx
    - Khi `compute_ecp=true`: `Cx = mean(s[:-1])`, `Cy = mean(s[1:])`, phơi bày `Cy_minus_Cx = Cy - Cx`; khi `len(s) < 2` → ECP = `null` + lý do; thuần adapter, không chạm core
    - _Requirements: 5.4_

  - [ ]* 8.4 Property test Property 6 (toán ECP đúng định nghĩa centroid)
    - **Property 6: Toán ECP đúng định nghĩa centroid (khi bật)**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 6: Với mọi chuỗi điểm lượt s có độ dài ≥ 2, khi ECP được bật, ECP PHẢI thỏa Cx = mean(s[:-1]) và Cy = mean(s[1:]), Cy_minus_Cx == Cy - Cx; khi mọi phần tử bằng hằng số c thì Cx == Cy == c (và Cy_minus_Cx == 0), và Cx, Cy luôn nằm trong [min(s), max(s)].`
    - Hypothesis ≥ 100 vòng; generator gồm chuỗi độ dài 0/1/≥2 và chuỗi hằng số
    - **Validates: Requirements 5.4**

  - [ ] 8.5 Hiện thực tổng hợp (aggregate) theo dataset/language/theory
    - Tổng hợp chỉ số per dataset, per language (`metadata.language`), per `psychological_theory` khi có; giữ thẻ `track` cho mỗi bản ghi
    - _Requirements: 5.5, 5.6_

  - [ ]* 8.6 Property test Property 8 (tổng hợp phân hoạch đúng, trung bình nhóm)
    - **Property 8: Tổng hợp phân hoạch đúng và trung bình nhóm bằng trung bình thành viên**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 8: Với mọi tập kết quả per-conversation, việc tổng hợp theo (dataset, language) và theo psychological_theory PHẢI phân hoạch sao cho mỗi kết quả thuộc đúng nhóm khóa của nó, và giá trị trung bình mỗi chỉ số của một nhóm bằng trung bình của chính các thành viên trong nhóm.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 5.5, 5.6**

- [ ] 9. Checkpoint — Đảm bảo các test hiện có đều pass
  - Đảm bảo tất cả test pass, hỏi người dùng nếu có vướng mắc.

- [ ] 10. ScoringRunner (runner.py)
  - [ ] 10.1 Hiện thực ScoringRunner gọi vendored run.py (run_scoring)
    - Gọi `vendor/etrajeval` `run.py` ở chế độ `run_scoring` bằng `config.yaml` đã sinh; KHÔNG chứa logic chấm điểm; hỗ trợ chế độ `dry_run` (xác thực cấu hình + đường dẫn, không nạp model) để agent kiểm thử mà không cần GPU
    - Ghi rõ trong docstring: lần chạy GPU thật do **NGƯỜI DÙNG tự thực thi thủ công** (xem runbook task 16.1)
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ]* 10.2 Viết unit test cho ScoringRunner (mock/dry-run)
    - Mock tiến trình `run.py`; xác minh ScoringRunner truyền đúng `config.yaml`, đặt chế độ `run_scoring`, và `dry_run` không nạp model/GPU
    - _Requirements: 2.1, 2.4_

- [ ] 11. TrackOrchestrator (orchestrator.py)
  - [ ] 11.1 Hiện thực TrackOrchestrator điều phối hai track + gắn thẻ
    - `en`→`{en}`, `zh`→`{zh}`, `ja`→`{translated-en, native-ja}`, `ko`→`{translated-en, native-ko}`; với `ja`/`ko` đảm bảo tạo + persist CẢ HAI track
    - Mỗi kết quả gắn đúng một thẻ `track ∈ {en, zh, translated-en, native-ja, native-ko}`; báo lỗi nếu thiếu một track
    - Ghi tài liệu lựa chọn Reward_Model (mặc định Skywork-Reward-V2-Llama-3.1-8B) + ghi rõ rủi ro cross-lingual chưa kiểm chứng của Track B
    - _Requirements: 6.10, 6.11, 6.12_

  - [ ]* 11.2 Property test Property 12 (điều phối track đúng theo ngôn ngữ và gắn thẻ)
    - **Property 12: Điều phối track đúng theo ngôn ngữ và gắn thẻ hợp lệ**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 12: Với mọi ngôn ngữ tập dữ liệu thuộc {en, zh, ja, ko}, tập track TrackOrchestrator tạo ra PHẢI đúng: en→{en}, zh→{zh}, ja→{translated-en, native-ja}, ko→{translated-en, native-ko}; mỗi kết quả per-conversation mang đúng một thẻ track hợp lệ và nhất quán với pipeline; với ja/ko CẢ HAI track đều có mặt.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 6.10, 6.11**

- [ ] 12. ResultsWriter (results_writer.py)
  - [ ] 12.1 Hiện thực ResultsWriter ghi layout dim_c
    - Ghi `*_etraj.json` per-conversation (id, language, track, theory, turn_scores, BEL, ETV, ECP?, param_set_key, initial_mu, provenance nếu track `translated-en`) vào `data/<dataset>/results/dim_c/`
    - Ghi `*_etraj_summary.txt` theo **phong cách** `cactus_pilot_summary.txt` (tiêu đề `=== ... SUMMARY ===`, dòng chỉ số kèm `(n=...)`), tách theo track cho `ja`/`ko`
    - _Requirements: 5.7_

  - [ ]* 12.2 Viết unit test cho ResultsWriter
    - Xác minh tệp ghi đúng vị trí `data/<dataset>/results/dim_c/`, đúng phong cách summary, và có tách track cho `ja`/`ko`
    - _Requirements: 5.7_

- [ ] 13. ValidationHarness (validation.py)
  - [ ] 13.1 Hiện thực hàm tính độ đồng thuận/so sánh
    - Hàm agreement (vd accuracy ∈ [0,1], correlation ∈ [-1,1]) dùng cho: điểm mô hình vs nhãn tham chiếu, và so sánh Track A vs Track B
    - _Requirements: 7.1, 7.3, 7.5_

  - [ ]* 13.2 Property test Property 11 (hàm tính độ đồng thuận đúng đắn)
    - **Property 11: Hàm tính độ đồng thuận đúng đắn**
    - Nhãn: `Feature: dim-c-etrajeval-scoring, Property 11: Với mọi cặp chuỗi cùng độ dài (điểm mô hình vs nhãn tham chiếu, hoặc Track A vs Track B), thước đo đồng thuận PHẢI nằm trong miền hợp lệ (accuracy ∈ [0,1]; tương quan ∈ [-1,1]) và đạt giá trị đồng thuận hoàn hảo khi hai chuỗi trùng khớp hoàn toàn.`
    - Hypothesis ≥ 100 vòng
    - **Validates: Requirements 7.1, 7.3**

  - [ ] 13.3 Hiện thực báo cáo xác thực và ghi *_etraj_validation.txt
    - `en`/`zh`: sanity check so nhãn tham chiếu theo từng ngôn ngữ; `ja`/`ko`: báo cáo CẢ HAI track so nhãn + so Track A vs Track B; ghi rủi ro (translation fidelity Track A, cross-lingual chưa kiểm chứng Track B); so coverage/stability với UED cũ; ghi `*_etraj_validation.txt` vào layout dim_c
    - _Requirements: 7.2, 7.4, 7.6, 7.7_

  - [ ]* 13.4 Viết unit test cho báo cáo xác thực
    - Xác minh báo cáo `ja`/`ko` có mục rủi ro cho cả hai track, có so sánh coverage/stability với UED, và ghi đúng `*_etraj_validation.txt`
    - _Requirements: 7.2, 7.4, 7.6, 7.7_

- [ ] 14. CLI wiring (cli.py)
  - [ ] 14.1 Hiện thực cli.py nối toàn bộ pipeline
    - Nối: canonical → DataConverter/TranslatedEnIngest → PromptsBuilder → PromptExtension → LanguagePreflight → ConfigGenerator/RunManifest → TrackOrchestrator → ScoringRunner → MetricsAdapter → ResultsWriter → ValidationHarness; đọc `config/dim_c_etraj.yaml`; hỗ trợ `--dry-run`
    - _Requirements: 8.1, 8.5_

  - [ ]* 14.2 Viết unit test CLI (dry-run)
    - Xác minh CLI dây nối đúng thứ tự thành phần ở chế độ `--dry-run` (không cần GPU/model)
    - _Requirements: 8.1, 8.5_

- [ ] 15. Integration smoke test (CPU-mockable)
  - [ ]* 15.1 Viết integration smoke test trên mẫu 1–2 hội thoại
    - Chạy vendored `run.py` `run_scoring` trên mẫu rất nhỏ (1–2 hội thoại) với reward model nhỏ/giả lập; xác nhận đường ống canonical → convert → chat_logs/prompts → run_scoring → answer → ResultsWriter → dim_c
    - Bao gồm smoke xác nhận Core đọc đúng mục prompt `ja`/`ko` sau PromptExtension khi đặt `language: ja|ko` (kiểm chứng cơ chế index-theo-`self.language`)
    - _Requirements: 2.1, 2.3, 5.1, 6.1, 6.6, 6.7_

- [ ] 16. Runbook cho bước chạy GPU thủ công (NGƯỜI DÙNG TỰ CHẠY)
  - [ ] 16.1 Viết runbook tái lập cho lần chấm điểm GPU thật
    - Tạo `docs/dim_c_etraj_runbook.md` ghi rõ các bước **người dùng tự thực thi thủ công**: tải Reward_Model (Skywork-Reward-V2-Llama-3.1-8B), cấu hình `device`/`k_samples`/`softmax_temperature`, và lệnh chạy CLI để chấm điểm thật (GPU-heavy)
    - Nêu rõ agent CHỈ hiện thực adapter + test dry-run/CPU-mockable; lần chạy GPU/model-download/scoring thật KHÔNG do agent tự chạy
    - _Requirements: 8.1, 8.4, 8.5_

- [ ] 17. Checkpoint cuối — Đảm bảo tất cả test pass
  - Đảm bảo tất cả test pass, hỏi người dùng nếu có vướng mắc.

## Notes

- Các sub-task đánh dấu `*` là tùy chọn (test) và có thể bỏ qua khi cần MVP nhanh; agent KHÔNG tự hiện thực các sub-task `*`.
- Mỗi correctness property (1–13) được hiện thực bằng đúng một property test bằng Hypothesis, tối thiểu 100 vòng lặp, gắn nhãn `Feature: dim-c-etrajeval-scoring, Property {n}: {text}`.
- Property test được đặt sát thành phần liên quan để bắt lỗi sớm.
- Ràng buộc cốt lõi R1: KHÔNG sửa logic core (`dyn_score.py`/`model.py`/`run.py`); mọi đa ngôn ngữ chỉ qua mở rộng prompt + cấu hình.
- Các bước GPU-heavy / tải model / chấm điểm thật là việc **người dùng tự chạy thủ công** (task 16.1); agent chỉ hiện thực adapter + test dry-run/CPU-mockable.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "6.1"] },
    { "id": 2, "tasks": ["1.3", "2.2", "3.1", "7.1"] },
    { "id": 3, "tasks": ["2.3", "2.4", "2.5", "2.6", "2.7", "3.2", "6.2", "7.2", "8.1"] },
    { "id": 4, "tasks": ["3.3", "3.4", "5.1", "8.2", "8.3", "10.1", "12.1", "13.1"] },
    { "id": 5, "tasks": ["5.2", "8.4", "8.5", "10.2", "11.1", "12.2", "13.2", "13.3"] },
    { "id": 6, "tasks": ["8.6", "11.2", "13.4", "14.1"] },
    { "id": 7, "tasks": ["14.2", "15.1"] },
    { "id": 8, "tasks": ["16.1"] }
  ]
}
```
