## **HƯỚNG DẪN THỰC HIỆN BÀI TẬP LỚN CHO SINH VIÊN HỌC PHẦN CSC4007** 

**CSC4007 – Xử lý ngôn ngữ tự nhiên** 

Chủ đề: Khai thác thông tin kinh tế, tài chính và kinh tế vĩ mô từ văn bản 

ThS. Lê Thị Thùy Trang 

28/10/2026 

# **1 Giới thiệu bài tập lớn** 

## **1.1 Bối cảnh** 

Sinh viên chọn một nhiệm vụ NLP trong miền dữliệu kinh tế– tài chính, thiết kếquy trình dữliệu và mô hình, xây dựng tập đánh giá có căn cứ, thực hiện thí nghiệm đối chứng và triển khai sản phẩm minh họa. Không yêu cầu mọi nhóm fine-tune mô hình lớn, xuất ONNX hoặc sửdụng GPU/LLM trảphí. 

Sáu đề tài được xây dựng quanh cùng miền ứng dụng nhưng khác bản chất nhiệm vụ: **phân loại văn bản, trích xuất thông tin, tìm kiếm ngữnghĩa, phát hiện bất định kinh tế, tóm tắt có kiểm chứng và hỏi đáp tài liệu tài chính bằng RAG** . Sựthống nhất vềmiền dữliệu giúp sinh viên liên hệkết quảgiữa các nhóm; sự khác nhau vềnhiệm vụgiúp thểhiện đầy đủcác năng lực của NLP. 

Một sản phẩm đạt yêu cầu không chỉtrảlời được câu hỏi “demo có chạy không?”, mà phải chứng minh được: **dữliệu đúng bài toán →tập gold kiểm chứng được →baseline →hai cấu hình đối chứng →chỉsốtrên test độc lập →phân tích lỗi →demo có thểchạy lại** . 

## **1.2 Nguyên tắc thiết kếvà thực hiện** 

- Có nhiệm vụ NLP xác định rõ **đầu vào, đầu ra, nhãn/đáp án và metric** ; không biến dựán thành dựbáo GDP/CPI bằng kinh tếlượng. 

- Nguồn dữliệu phải đúng bài toán, có phiên bản, quyền sửdụng và cách truy xuất; **không mặc nhiên coi nhãn có sẵn của một nhiệm vụ là gold cho nhiệm vụ khác** . 

- Có tệp **data_card.md riêng** , mô tả đúng dữ liệu thực sửdụng, nguồn, tiền xửlý, phân chia dữliệu, chất lượng nhãn, bias và rủi ro. 

- Có **bộ kiểm thửgold và giao thức đánh giá** ; ghi rõ ai gắn nhãn, ai rà soát và cách xửlý bất đồng. 

- Có **E0 (baseline), E1, E2** – ba cấu hình có khác biệt và giảthuyết rõ ràng, có log, dựđoán và kết quảđịnh lượng đểtái lập. 

- Có phân tích ít nhất **10 lỗi cụthể** , demo chạy được hoặc bản ghi demo kèm hướng dẫn thực thi, báo cáo kỹ thuật và minh bạch việc sửdụng AI. 

- Không chấp nhận dựán **chỉlà giao diện gọi API/LLM** , hoặc chỉbáo cáo một con sốmà thiếu bộđánh giá và bằng chứng chạy thực tế. 

**Điều kiện quan trọng nhất:** Thiếu Data Card hoặc thiếu bằng chứng thực nghiệm thì **chưa đủhồsơ nghiệm thu** ; không thay thếbằng nội dung mô tảtrong báo cáo hay video demo. Việc xửlý bổsung và điểm sốtuân theo quy định chính thức của học phần/trường. 
# **2 Mục tiêu học tập** 

Sau khi hoàn thành bài tập lớn, sinh viên có thể: 

1. **Phân tích** một bài toán NLP thực tế: đối tượng sửdụng, dữliệu, đầu vào, đầu ra, nhãn và chỉsốđánh giá. 

2. **Thiết kế** lược đồdữliệu, quy trình lấy mẫu, làm sạch, ghi nguồn, kiểm tra chất lượng và chống rò rỉdữ liệu. 

3. **Xây dựng** Data Card và bộgold có khảnăng truy xuất, rà soát và tái tạo theo đúng đặc thù nhiệm vụ. 

4. **Triển khai** baseline và ít nhất hai cấu hình đối chứng/cải tiến; nêu được giảthuyết và giới hạn của so sánh. 

5. **Đánh giá** kết quảbằng metric phù hợp, tập test độc lập và bằng chứng dựđoán theo từng mẫu. 

6. **Phân tích** lỗi ngôn ngữ, lỗi dữliệu, lỗi trích xuất/chứng cứvà đềxuất được hướng sửa có thểkiểm chứng. 

7. **Xây dựng** demo minh họa chức năng NLP; trình bày, bảo vệvà giải trình mô hình, prompt, công cụAI đã sửdụng. 

# **3 Quy định chung** 

## **3.2 Mức tối thiểu đểđược nghiệm thu** 

Một nhóm cần có đồng thời: 

1. Nguồn dữliệu và quyền sửdụng đã được xác định; tệp **data_manifest.csv** (hoặc định dạng tương đương) và tài liệu schema. 

2. **data_card.md** hoàn chỉnh, phản ánh đúng tập con dùng trong nghiên cứu. 

3. Báo cáo kiểm tra dữliệu, **gold/evaluation set** kèm guideline/protocol và manifest phân chia dev/test. 

4. **E0, E1, E2** , mã nguồn/cấu hình, log thí nghiệm và ít nhất một tệp dựđoán cho mỗi cấu hình. 

5. Bảng kết quảđược tính bằng script trên **cùng tập test đã khóa** ; metric riêng đúng nhiệm vụ. 

6. **error_analysis.md** phân tích ít nhất 10 trường hợp cụthểvà giải thích nguyên nhân. 

7. Demo và README.md mô tảcách chạy; báo cáo PDF; nhật ký và tuyên bốsửdụng AI. 

8. Đường dẫn repository hoặc gói ZIP, không công khai lại dữliệu hoặc khóa truy cập trái phép. 

## **3.3 Nguồn dữliệu tham khảo** 

|Nguồn|Đặc điểm|Nhiệm vụphù hợp|Lưu ý khi dùng|
|---|---|---|---|
|ViFinQA|Câu hỏi và báo cáo tài<br>chính OCR theo tài liệu<br>nguồn|Document QA/RAG|Bản công khai chưa có gold<br>answer/evidence và split<br>đánh giá; cần tự xác minh|
**Ghi chú:** Các dataset trên chỉlà dataset gợi ý; sinh viên có thểtựdo tìm kiếm và lựa chọn dataset phù hợp với đềtài. 

## **3.4 Điều chỉnh khối lượng theo quy mô nhóm** 

Với nhóm **02 sinh viên** , giảng viên có thểcung cấp sẵn tới khoảng **25% gold/starter annotations đã hậu kiểm** , hoặc giảm corpus mởrộng đểtiết kiệm công gắn nhãn; **không giảm** yêu cầu tập test độc lập, E0–E2, Data Card, bằng chứng thực nghiệm và phân tích lỗi. Các điều chỉnh khối lượng phải được ghi trong phiếu duyệt đềtài. 

## **3.5 Nguyên tắc chấm công bằng** 

- Các ngưỡng khối lượng khác nhau vì gắn nhãn một câu hỏi RAG hay bản tóm tắt thường tốn công hơn kiểm tra một nhãn classification. 

- Đềtài có nhãn sẵn cần tăng chất lượng phân tích lỗi, so sánh biểu diễn/mô hình và robustness; đềtài tựtạo gold được ghi nhận công annotation khi có guideline và hậu kiểm. 

- Không so điểm sốtrực tiếp giữa những metric khác bản chất, chẳng hạn F1 của NER và nDCG của retrieval. 

- Không cộng điểm chỉvì dùng mô hình lớn, GPU mạnh hoặc API trảphí; một cải tiến không vượt baseline vẫn được chấp nhận nếu thí nghiệm nghiêm túc và phân tích nguyên nhân đúng. 

# **4 Danh sách và hướng dẫn thực hiện sáu đềtài** 

Bảng dưới đây tóm tắt sáu hướng, sau đó là hướng dẫn chi tiết theo **cùng cấu trúc như mẫu kỳtrước** : mục tiêu, dữliệu, kỹthuật tối thiểu, yêu cầu nâng cao, thực nghiệm–đánh giá và sản phẩm nộp. 

|Mã|Đềtài|Khối lượng cơ bản (tham<br>chiếu)|Mức độ|
|---|---|---|---|
|ĐT06|RAG báo cáo tài chính có<br>trích dẫn|10–20 báo cáo; ≥50 QA<br>gold, test ≥40 câu|Nâng cao|

## **4.6 Đề tài 6. Hỏi đáp báo cáo tài chính có trích dẫn bằng RAG** 

### **4.6.1 Mục tiêu** 

Trảlời câu hỏi vềbáo cáo tài chính, tìm đúng doanh nghiệp/năm/đoạn hoặc bảng nguồn, có kiểm tra đơn vịsố học và từchối khi thiếu bằng chứng. 

**Đầu vào/đầu ra mong đợi:** câu hỏi + corpus báo cáo →câu trảlời, sốliệu/đơn vị, doanh nghiệp, năm và trích dẫn tới trang/đoạn/bảng. 

### **4.6.2 Dataset, chuẩn dữliệu và định mức** 

**Nguồn dữliệu:** ViFinQA. Giới hạn một corpus khảthi, khuyến nghị **10–20 báo cáo** của **02–04 doanh nghiệp** qua một sốnăm, ưu tiên bản OCR/bảng dễkiểm tra. 

**Khối lượng tối thiểu:** nhóm kiểm chứng **tối thiểu 50 câu hỏi** trên corpus thực dùng; chia **10 dev + 40 test** , trong test có **ít nhất 08 câu không đủbằng chứng** , **ít nhất 10 câu liên quan sốliệu/đơn vị** ; có evidence/page/report/year và phép tính hoặc công thức nếu cần; **≥20% hậu kiểm chéo** . Khi không đủ50 câu hợp lệ, phải báo giảng viên trước giai đoạn thực nghiệm. 
**Yêu cầu triển khai dữliệu:** Nhóm cung cấp data_manifest.csv với ID ổn định, phiên bản/nguồn, data_card.md, data_quality_report.md, giao thức chia dev/test và bộnhãn hoặc đáp án gold đã được rà soát theo yêu cầu nhiệm vụ. Tập test được khóa trước khi chọn cấu hình cuối. 

### **4.6.3 Yêu cầu kỹ thuật tối thiểu** 

**Baseline E0:** BM25 + trích đoạn nguồn (không buộc sinh văn bản). 

**Các cấu hình E0–E2:** BM25 retrieval; dense/hybrid retrieval; pipeline trảlời có chứng cứ và/hoặc reranking trên corpus cốđịnh. Không bắt buộc mô hình sinh trảlời đắt tiền. 

**Demo:** hỏi – đáp, hiển thịnguồn, doanh nghiệp, năm, trang/đoạn và cơ chếkhông đủdữliệu. 

### **4.6.4 Yêu cầu nâng cao** 

câu hỏi đa bước qua nhiều bảng/báo cáo, cross-report QA, kiểm tra bảng tính, rút gọn chi phí truy hồi. 

Các ý tưởng nâng cao là phần tựchọn sau khi hoàn thành và kiểm chứng toàn bộyêu cầu cơ bản, không bắt buộc triển khai đồng thời. 

### **4.6.5 Thí nghiệm và đánh giá** 

**Metric và phân tích: retrieval Recall@k/MRR@k** , **answer numeric/normalized match** , **citation correctness** , tỷlệtừchối đúng khi thiếu chứng cứ; báo cáo lỗi theo OCR, sai năm, sai đơn vị, sai phép tính. 

Nhóm lập bảng E0/E1/E2 với version dữliệu, split, cấu hình/seed hoặc prompt version, kết quảdev/test và đường dẫn tới predictions. Mọi cấu hình phải được đo bằng cùng protocol; báo cáo ít nhất 10 mẫu lỗi có ID và chứng cứ. 

### **4.6.6 Sản phẩm nộp riêng của đềtài** 

**Minh chứng đặc thù:** danh mục báo cáo, audit OCR, qa_gold.jsonl, trích dẫn đã duyệt, retrieval_ predictions.csv và answer_predictions.csv. 

Ngoài các tệp này, nộp đầy đủhồsơ chung theo Mục 10. **Mức độ: nâng cao** , khuyến nghịnhóm đã có kinh nghiệm retrieval/LLM. 

# **5 Chuẩn hóa dữ liệu bắt buộc cho tất cảđềtài** 

## **5.1 Ba tầng dữ liệu và bộhồsơ** 

Dữliệu dựán phải được tách thành ba tầng có thểđối chiếu: 

1. **Nguồn gốc (raw/references):** URL/ID nguồn, phiên bản, ngày truy xuất, tác giả/đơn vịcung cấp, quyền sửdụng và giới hạn tái phân phối. Toàn văn chỉđược lưu hoặc công bốkhi được phép. 

2. **Dữliệu xửlý (processed):** bản làm sạch, chuẩn Unicode, bổsung ID, loại trùng, chuẩn trường dữliệu, lịch sửvà script biến đổi có thểchạy lại. 

3. **Dữliệu đánh giá (gold):** nhãn hoặc đáp án/bằng chứng đã rà soát, hướng dẫn gắn nhãn, log bất đồng, danh sách ID chia dev và **test độc lập** . 

Nhóm cần tạo data_schema.md giải thích tên trường, kiểu dữliệu, tập giá trịhợp lệvà quy ước nhãn. Giảng viên có thểcung cấp starter pack gồm 05–10 ví dụđúng định dạng cho mỗi đềtài và các template; nhóm vẫn phải xây dựng/kiểm chứng gold theo định mức. 

## **5.2 Lược đồchuẩn và quy tắc điền dữliệu** 

data_manifest.csv khuyến nghịdùng các cột: 

> item_id,document_id,source_name,source_url,source_version,retrieved_at,published_at,language,original_c _⌋ �→_ ategory,task_label,license_status,split,notes 
- published_at chỉdùng cho ngày phát hành **thực** từnguồn; retrieved_at là ngày nhóm tải. Nếu nguồn thiếu thì giữ null/unknown, **không suy ra từID hoặc ngày crawl** . 

- original_category là nhãn chuyên mục gốc, task_label là nhãn nhiệm vụdo nhóm sửdụng; **không được đánh đồng** hai trường. 

- Dữliệu IE: lưu vịtrí span hoặc khoảng ký tự, tên chỉtiêu, giá trị, đơn vị, thời kỳvà câu bằng chứng. 

- Dữliệu retrieval: lưu query_id, document_id, relevance, reviewer_id; không coi tài liệu chưa chấm là non-relevant. 

- Dữliệu summarization: giữbài gốc, bản tham chiếu và phiếu kiểm tra sốliệu; dữliệu RAG: thêm report_id, company_id, fiscal_year, trang/bảng, đáp án và evidence. 

Đối với nhãn thủcông, nhóm nộp annotation_guideline.md, gold_labels.csv/jsonl và log hậu kiểm với tối thiểu ID mẫu, nhãn/đáp án, mã người gắn nhãn, trạng thái rà soát, phiên bản guideline và ghi chú bất đồng. **Ít nhất 20% gold do nhóm tựtạo phải được người thứhai hậu kiểm** , trừkhi đặc tảcho phép mức kiểm tra cao hơn. 

## **5.3 Checklist kiểm tra chất lượng dữliệu** 

Trước mọi thí nghiệm chính, chạy script hoặc notebook kiểm tra và lưu reports/data_quality_report.md: 

- **Schema:** sốdòng thực đọc được, cột bắt buộc, kiểu dữliệu, nhãn ngoài danh mục, bản mã Unicode, ID trùng/rỗng, đường dẫn nguồn. 

- **Nội dung:** text trống, HTML, độdài bất thường, bản tin đăng lại và gần trùng, lỗi OCR, văn bản sai ngôn ngữhoặc không liên quan nhiệm vụ. 

- **Sốliệu kinh tế:** dấu âm, dấu phẩy/chấm thập phân, ký hiệu %, đơn vịtiền/tỷlệ, tên doanh nghiệp/cơ quan, năm/quý/tháng; không được biến 3,2% thành 32%. 

- **Gold:** phân bốnhãn, ví dụranh giới giữa các nhãn, nhãn unknown, các bất đồng và cách phân xử, tính đầy đủcủa evidence/reference. 

- **Rò rỉ:** cùng bài gốc, bản tin được sửa, cùng sựkiện, các chunk của cùng tài liệu; không đểbản sao hoặc biến thểgần giống xuất hiện sai quy tắc giữa train và test. 

- **Pháp lý/đạo đức:** kiểm tra quyền dùng, không đưa API key/PII/dữliệu có bản quyền không được phép lên repo công khai; dữliệu do LLM hỗtrợtạo nhãn phải được người kiểm chứng. 

Báo cáo có bảng kiểm đếm **trước/sau làm sạch** , danh sách ID mẫu bịloại/chỉnh và lý do, không chỉmô tả “đã làm sạch dữliệu”. 

## **5.4 Tách train/dev/test và quản lý tập gold** 

- **Classification/IE:** tỷlệ70/15/15 là gợi ý khi sốmẫu đủlớn; với gold nhỏcó thểdành **25–30% làm test** . Phải tách theo bài/sựkiện/nguồn khi cần, không rải chunk cùng bài sang nhiều split. 

- **Retrieval:** tách **theo truy vấn** , không đưa các câu hỏi paraphrase gần như trùng nhau vào cảdev và test. Ghi rõ candidate pooling, nhãn relevance và giới hạn các tài liệu chưa được chấm. 

- **Summarization:** dành tập dev đểthiết kếprompt/lựa chọn mô hình và tập test khóa lại đểchấm cuối; không đưa reference summary của test vào prompt. 

- **Financial RAG:** tách dev/test theo câu hỏi và công bốrõ cùng báo cáo có thểxuất hiện ởcảhai; nếu khẳng định tổng quát sang doanh nghiệp/năm mới thì phải có thửnghiệm tách riêng theo doanh nghiệp/năm. 

- **Có thời gian:** nếu có published_at thật, có thểbáo cáo thêm đánh giá theo thời gian. Không dùng ngày truy xuất thay ngày công bố. 
**Quy tắc bất biến:** chọn tham số, chọn prompt, chọn mô hình bằng **dev** . Chỉdùng **test** đểcông bốkết quả cuối. Nếu đã nhìn test đểtuning, phải khai báo và thiết kếlại tập test độc lập nếu muốn kết luận khách quan. 

## **5.5 Cổng duyệt dữliệu D1** 

Trước khi bước vào thực nghiệm E1/E2, nhóm nộp gói **D1 – Data Readiness** gồm (i) nguồn/version/license; (ii) schema/manifest; (iii) thống kê dữliệu thực; (iv) split và giải pháp chống leakage; (v) guideline và log rà soát nhãn nếu có; (vi) gold và evaluation protocol; (vii) data-quality report. **Chưa có bộgold đáng tin cậy thì chưa được nghiệm thu kết quảmô hình** , kểcảkhi có demo. 

# **6 Yêu cầu thực nghiệm và đánh giá cho tất cảđềtài** 

## **6.1 Ba cấu hình E0–E2 là bắt buộc** 

|Mã|Vai trò|Bằng chứng tối thiểu|
|---|---|---|
|**E0**|Baseline đơn giản, có thểtái lập<br>(TF-IDF/BM25/regex/Lead-k…)|Script, config, prediction, metric|
|**E1**|Phương án 1 với giảthuyết kiểm<br>chứng (embedding, model, prompt…)|Mô tảyếu tốthay đổi, prediction,<br>metric|
|**E2**|Đối chứng/cải tiến thứ2 (fusion,<br>reranking, kiểm soát factuality…)|Lý do kỳvọng khác E1, prediction,<br>metric|



Ba cấu hình phải dùng **cùng test và cách tính metric** ; báo cáo dev đểgiải thích quyết định chọn phương án trước khi đánh giá test. E2 không được chỉlà đổi tên file hay chạy lại cùng tham số. Với thí nghiệm ngẫu nhiên, khuyến khích nhiều seed và thống kê dao động nếu điều kiện cho phép. 

## **6.2 Nhật ký thí nghiệm và bảng so sánh** 

Mỗi cấu hình phải có run_id, phương pháp, dataset/split version, config path, seed hoặc prompt version, model/version, thời điểm chạy, metric dev/test, prediction artifact và ghi chú. **W&B hoặc MLflow là tùy chọn; experiments.csv hoặc runs.jsonl là bắt buộc** . 

|Run|Phương pháp|Cấu hình thay đổi|Dev metric|Test metric|Diễn giải|
|---|---|---|---|---|---|
|E0|Baseline|Đặt mốc|…|…|…|
|E1|Biến thể1|Giảthuyết A|…|…|…|
|E2|Biến thể2|Giảthuyết B|…|…|…|



Các giá trịphải được tạo bằng script đánh giá và lưu trên tệp. Không được chỉchụp màn hình bảng kết quả hoặc tựgõ kết quảvào báo cáo. Kèm test_predictions.csv/jsonl theo từng run với ID, gold/reference có quyền dùng, dựđoán và thông tin cần thiết đểtính lại metric. 

## **6.3 Phân tích lỗi** 

Phân tích **ít nhất 10 mẫu lỗi khác nhau** . Mỗi trường hợp phải nêu: ID, đầu vào/bằng chứng nguồn được phép trình bày, gold/reference, dựđoán của E0/E1/E2, loại lỗi, giảthuyết nguyên nhân và hướng xửlý. Các nhóm phân loại xét nhầm lớp; IE xét lỗi span/đơn vị/thời gian; retrieval xét tài liệu đúng ngoài top-k; bất định xét ranh giới với tin tiêu cực; tóm tắt xét sai sốliệu/hallucination; RAG xét sai nguồn/năm/bảng và từchối khi không đủchứng cứ. 

**Kết quảthấp hơn baseline vẫn có thểcó giá trịhọc thuật** nếu protocol đúng và nhóm chỉra được nguyên nhân cụthể, giới hạn dữliệu và thí nghiệm tiếp theo. Không được chọn thủcông mẫu “đẹp” đểthay bảng test. 
## **6.4 LLM, Prompt Engineering và RAG** 

Nếu dùng LLM, phải lưu **prompt template, ví dụfew-shot (nếu có), model/version, tham sốsuy luận, ngày chạy và mẫu output** trong phạm vi quyền sửdụng. Các biến thểprompt E1/E2 phải khác biệt rõ vềchiến lược, không đơn thuần thay câu chữ. Mỗi nhóm dùng RAG phải **đánh giá riêng retrieval và answer** , có nguồn/đoạn chứng cứ, nêu chính sách từchối thiếu bằng chứng. **Multi-hop reasoning là nâng cao** , yêu cầu nhãn từng bước/bằng chứng khi nhóm tựchọn, không phải yêu cầu mặc định cho tất cảđềtài. 

## **6.5 Demo và khảnăng tái lập** 

Demo phải nhận đầu vào đúng nhiệm vụvà trình bày kết quảkèm nguồn khi có truy hồi dữliệu. Có thểdùng CLI, notebook có cấu trúc, Streamlit hoặc Gradio. Nếu môi trường chấm không chạy được, nộp video kèm **lệnh cài đặt và chạy lại** , phiên bản phụthuộc, dữliệu mẫu hợp lệvà một ca kiểm tra đầu vào/đầu ra. ONNX, tối ưu suy luận và W&B năm runs là **tùy chọn** , không được yêu cầu thay phần bằng chứng NLP cốt lõi. 

# **7 Quy định Data Card và trách nhiệm dữliệu** 

File **data_card.md là bắt buộc** và phải phản ánh corpus **thực tế** (không sao chép nguyên dataset card từ Internet). Tối thiểu có 14 mục: 

1. **Dataset Summary & Intended Use:** bài toán và phạm vi sửdụng. 

2. **Dataset Sources & Versions:** link, tác giả, ngày truy xuất, revision. 

3. **License & Access:** quyền, giới hạn tái phân phối, điều kiện truy cập. 

4. **Data Structure:** các trường, kiểu và ví dụđã ẩn thông tin nhạy cảm. 

5. **Composition & Distributions:** sốmẫu, chủđề/nhãn/nguồn và thiếu dữliệu. 

6. **Collection & Sampling:** cách chọn bài, truy vấn, snapshot, nguồn lọc. 

7. **Preprocessing:** script biến đổi, loại trùng và bảo toàn sốliệu. 

8. **Annotation Process:** người gắn nhãn, hướng dẫn, cách xửlý unclear. 

9. **Quality Checks:** lỗi, audit, tỷlệkiểm tra chéo, bất đồng nhãn. 

10. **Splits & Leakage Prevention:** danh sách ID, quy tắc train/dev/test. 

11. **Gold & Evaluation Protocol:** nguồn gốc đáp án, tiêu chí chấm, phần chưa gắn nhãn. 

12. **Biases, Ethics & Risks:** thiên lệch nguồn/ngôn ngữ/thời gian và PII. 

13. **Limitations & Inappropriate Uses:** điều dữliệu không chứng minh được. 

14. **Reproducibility & Access Instructions:** phiên bản, script, seed, cách tải lại hợp lệ. 

Với gold do nhóm tựxây, nộp **annotation_guideline.md** và log kiểm chứng nhãn. Với dữliệu bên ngoài, không giảđịnh mọi trường trong dataset card đều có mặt trong phiên bản thực tếđã tải. **Data Card không phải đoạn giới thiệu vài dòng trong báo cáo.** 

# **8 Rubric đánh giá** 

|Thành phần|Điểm (thang 100)|Bằng chứng chấm|
|---|---|---|
|Xác định bài toán, phạm vi NLP|10|Đầu vào/đầu ra, câu hỏi nghiên<br>cứu, metric phù hợp|
|**Dữliệu, chuẩn hóa, Data Card**|**20**|Nguồn/quyền, schema, audit,|
|**và chất lượng nhãn**||gold, split, guideline|
|Baseline và khảnăng tái lập|10|E0 chạy lại được, kết quảvà mã<br>đánh giá|
|Thành phần|Điểm (thang 100)|Bằng chứng chấm|
|---|---|---|
|Thiết kếthí nghiệm và hai đối<br>chứng|15|E1/E2 có giảthuyết, log và phép<br>so sánh công bằng|
|**Đánh giá, kiểm chứng và phân**<br>**tích lỗi**|**25**|Gold độc lập, metric đúng,<br>predictions và ≥10 lỗi|
|Demo và khảnăng sửdụng|10|Demo đúng nhiệm vụ, trình bày<br>nguồn khi cần|
|Báo cáo, mã nguồn và hướng dẫn<br>chạy|5|Repo/ZIP, PDF, cài đặt, tái lập|
|Minh bạch AI, đạo đức và quyền|5|Nhật ký/tuyên bốAI, bảo vệdữ|
|dữliệu||liệu/khóa API|
|**Tổng cộng**|**100**||



**Chấm riêng theo nhiệm vụ:** phân loại cần Macro-F1 và phân tích nhãn; IE cần span và fact tuple; retrieval cần relevance judgments và ranking metric; bất định cần guideline tách khỏi sentiment; tóm tắt cần đánh giá factuality sốliệu ngoài ROUGE; RAG phải có retrieval, answer, citation và câu hỏi thiếu bằng chứng. **Không áp dụng cùng một ngưỡng điểm mô hình cho mọi đềtài.** 

# **9 Các mốc triển khai gợi ý** 

Các mốc dưới đây thểhiện trình tựvà điều kiện hoàn thành, **không quy định sốtuần thực hiện** . Lịch cụthể do giảng viên công bốtheo kếhoạch học phần. 

|**Mốc**|**Công việc**|**Minh chứng cần nộp**|
|---|---|---|
|M0|Giảng viên kiểm tra quyền, schema và ví dụgold trước<br>khi giao đềtài|Starter pack/bộnguồn đã duyệt|
|M1|Đăng ký, chốt nhiệm vụ, nguồn, câu hỏi nghiên cứu và<br>giao thức đánh giá|Phiếu đăng ký, Data Card nháp|
|M2|Làm sạch, kiểm tra nhãn, khóa test, chuẩn hóa dữliệu và<br>xây baseline|Gói D1 + E0|
|M3|Chạy E1/E2, ghi log và so sánh trên tập dev|experiments.csv, scripts, predictions dev|
|M4|Chọn cấu hình, đánh giá test độc lập và phân tích lỗi|Metrics/predictions test, error analysis|
|M5|Hoàn thiện demo, báo cáo và bảo vệ|Hồsơ nộp hoàn chỉnh|
|Nâng cao|Thửnghiệm robustness, multi-hop hoặc cải thiện khả<br>năng tái lập (nếu phù hợp)|Thí nghiệm/phụlục nâng cao|



**Nguyên tắc:** Có thểđiều chỉnh thứtựhoặc gộp hoạt động theo lịch học phần, nhưng không bỏData Card, gold, kiểm tra chống rò rỉdữliệu hoặc bằng chứng E0–E2. 

# **10 Yêu cầu nộp bài** 

## **10.1 Cấu trúc repository khuyến nghị** 

CSC4007-NLP-Project/ 
├──README.md 
├──requirements.txt 
├──data_card.md 
├──data/ 
│ ├──README.md 
│ ├──data_manifest.csv 
│ ├──splits/ 
│ └──annotations/ 
│ ├──annotation_guideline.md 
│ ├──gold_labels.csv # hoặc JSONL / QA gold 
│ └──review_log.csv 
├──configs/ # E0, E1, E2 và prompt versions 
├──src/ # chuẩn hóa, model, infer, evaluate 
├──evaluation/ 
│ ├──evaluation_protocol.md 
│ ├──experiments.csv 
│ ├──metrics_summary.csv 
│ ├──test_predictions_E0.csv 
│ ├──test_predictions_E1.csv 
│ ├──test_predictions_E2.csv 
│ └──error_analysis.md 
├──reports/ 
│ ├──data_quality_report.md 
│ ├──Bao_cao_BTL.pdf 
│ ├──Nhat_ky_su_dung_AI.md 
│ └──Tuyen_bo_su_dung_AI.md 
└──app/ # mã demo / hướng dẫn / video 

Có thể đổi tên hoặc dùng định dạng khác khi nhóm nộp bảng ánh xạ vị trí minh chứng; **không được bỏ bất kỳ nội dung bắt buộc nào** . 

## **10.2 Bảng kiểm trước khi nộp** 

- Dữ liệu đúng đềtài, có nguồn/version/license, không công khai bản quyền trái phép. 

- data_card.md phản ánh dữ liệu **đã sử dụng** , đủ 14 nội dung. 

- Có data_quality_report.md, manifest, schema và split chống leakage. 

- Có bộ gold/evidence/reference và guideline/hậu kiểm theo nhiệm vụ. 

- Có E0/E1/E2 với mã, cấu hình, log và prediction riêng. 

- Có metric test được tính bằng script, bảng tổng hợp và phân tích ≥10 lỗi. 

- Có demo và README đểngười khác chạy lại hoặc kiểm tra. 

- Có báo cáo, nhật ký và tuyên bốsửdụng AI; không lộAPI key/PII. 

## **10.3 Tình huống chưa đủ điều kiện nghiệm thu** 

Nếu thiếu data_card.md, không có gold/test độc lập, chỉcung cấp mô tảthí nghiệm mà **không có mã/log/predictions** , hoặc không có baseline/đối chứng, bài **chưa đủđiều kiện nghiệm thu** . Nhóm phải bổsung theo thông báo giảng viên và quy định học phần; không tựsuy đoán điểm trừhoặc lịch bổsung. 

# **11 Những lỗi thường gặp cần tránh** 

1. Lấy nhãn category của tin tức làm nhãn sentiment, bất định hoặc chuyên đềCPI/GDP mà **chưa gắn nhãn lại** . 

2. Ghi nguồn dataset nhưng không nêu version/snapshot, không kiểm tra sốmẫu và điều kiện quyền sửdụng. 

3. Đưa bài trùng, bản tin cùng sựkiện hoặc chunk cùng tài liệu vào nhiều split gây leakage. 

4. Dùng test đểchọn prompt/hyperparameter nhưng vẫn trình bày như đánh giá độc lập. 

5. Dùng nhãn LLM tựtạo làm gold mà không kiểm chứng; không lưu quy tắc xửlý bất đồng. 

6. Chỉ có demo gọi API mà thiếu baseline, đối chứng và prediction có thể tái lập. 
7. Báo cáo Accuracy của classification khi lệch nhãn; dùng ROUGE cho tóm tắt mà bỏkiểm tra dữkiện; báo cáo Recall@k khi relevance chưa được xác nhận. 

8. Kết luận GDELT tone là chỉsốEPU chính thức hoặc dựbáo kinh tếmà không có chứng cứkiểm định. 

9. Đánh giá RAG chỉbằng câu trảlời cuối, không đo retrieval/citation; không xửlý câu hỏi thiếu chứng cứ. 

10. Có Data Card mang tính hình thức, copy dataset card của nguồn nhưng không mô tảtập con thực dùng. 

11. Chỉ có bảng số trong PDF, không có file script, config, log và dự đoán tương ứng. 

12. Nộp dữ liệu đầy đủtrái phép, API key, PII hoặc báo cáo có nội dung không thể kiểm chứng. 

# **12 Câu hỏi thảo luận và bảo vệcuối kỳ** 

Mỗi thành viên cần có khảnăng trảlời câu hỏi liên quan đến phần việc mình thực hiện và hiểu toàn bộpipeline: 

1. Vì sao dataset này phù hợp với **đúng nhiệm vụ** của nhóm? Nhãn gốc và nhãn nhóm tựxây khác nhau thế nào? 

2. Dataset có các vấn đềbias, chất lượng, bản quyền và giới hạn nguồn/thời gian gì? 

3. Bạn đã kiểm tra mẫu trùng và ngăn data leakage theo **bài báo, sựkiện, công ty/năm hoặc truy vấn** ra sao? 

4. E0 là gì? Tại sao E1 và E2 là phép so sánh có ý nghĩa? 

5. Kết quảdev và test có khác nhau không? Vì sao không được chọn prompt bằng test? 

6. Bạn có thểtính lại một metric từfile predictions bằng script nào? 

7. Gold được xây dựng/kiểm tra thếnào? Nếu hai người gắn nhãn bất đồng thì xửlý ra sao? 

8. Lỗi khó nhất của hệthống thuộc dữliệu, ngôn ngữ, phương pháp hay bằng chứng nguồn? 

9. Nếu hệthống dùng LLM, đâu là vai trò của prompt, model/version, chi phí và giới hạn của nó? 

10. Nếu dùng RAG, retrieval đúng nhưng câu trảlời sai thì nhóm đã phát hiện bằng chỉsốnào? 

11. Nếu được thêm hai tuần, nhóm sẽcải thiện dữliệu, gold, baseline hay mô hình trước? Cơ sởlựa chọn? 

12. Demo hiện tại có thểdùng ngoài phạm vi bài tập lớn chưa? Trong điều kiện nào cần từchối hoặc đưa cảnh báo? 

# **13 Tài liệu và công cụtham khảo** 

- Dataset tin tiếng Việt: VietOnlineNews và UVN-1. 

- Dữliệu tin kinh tếtheo thời gian: GDELT Data Portal, GDELT DOC 2.0 API. 

- QA báo cáo tài chính: ViFinQA; sentiment tiếng Anh (thay thếcó duyệt): Financial PhraseBank. 

- Tài liệu Data Card: Hugging Face Dataset Cards. 

- Các thư viện tham khảo (chọn theo nhiệm vụ): scikit-learn, pandas, datasets, transformers, sentence-transformers, faiss-cpu, rank-bm25, evaluate, rouge-score, streamlit hoặc gradio. Không bắt buộc cài mọi thư viện. 

- Tài liệu tổchức nội bộkếthừa: **hướng dẫn BTL CSC4005–CSC4007 kỳtrước** (mẫu cấu trúc, Data Card, rubric và bảo vệ); **bản đềxuất CSC4007 v2.0 ngày 28/10/2026** (định mức và chuẩn đánh giá). Phần W&B/ONNX dành cho CSC4005 kỳtrước không còn là điều kiện bắt buộc của CSC4007 độc lập. 

# **14 Kết luận** 

Bài tập lớn CSC4007 được tổchức theo một chuỗi thực hành NLP **có trách nhiệm, có kiểm chứng và có thể tái lập** : 

**Bài toán →Nguồn dữliệu →Chuẩn hóa & Data Card →Gold & split →Baseline E0 →Đối chứng E1/E2 →Đánh giá độc lập →Phân tích lỗi →Demo & báo cáo.** 
**Bằng chứng tốt quan trọng hơn một con sốđẹp.** Sản phẩm cần cho thấy không chỉmô hình dựđoán được gì, mà còn cho thấy nhóm biết dữliệu đến từđâu, vì sao có thểtin vào phép đo, mô hình sai ởđâu, và khi nào hệthống không nên đưa ra kết luận. 

# **A Mẫu phiếu đăng ký đềtài** 

- Mã nhóm / họtên và nhiệm vụtừng thành viên: 

- Mã và tên đềtài: 

- Câu hỏi nghiên cứu / trường hợp sửdụng: 

- Đầu vào, đầu ra, nhãn hoặc cấu trúc đáp án: 

- Nguồn dữliệu, URL, phiên bản và quyền dùng: 

- Quy mô corpus / gold / dev / test dựkiến: 

- Baseline E0: 

- Biến thể E1 và giảthuyết: 

- Biến thể E2 và giảthuyết: 

- Metric chính/phụvà cách kiểm chứng: 

- Rủi ro leakage và phương án phòng tránh: 

- Khối lượng tự gắn nhãn, người hậu kiểm: 

- Kịch bản demo và dữliệu mẫu: 

- Phần nâng cao (nếu đăng ký): 

# **B Mẫu log thí nghiệm và phiếu phân tích lỗi** 

Mẫu dòng experiments.csv: 

run_id,method,dataset_version,split_version,config_path,seed_or_prompt_version,dev_metric,test_metric,p _⌋ �→_ rediction_file,notes 

E0,...,...,...,...,...,...,...,...,... E1,...,...,...,...,...,...,...,...,... E2,...,...,...,...,...,...,...,...,... 

Mỗi mục trong error_analysis.md cần có: 

- item_id và loại lỗi: 

- Đầu vào / nguồn / chứng cứhợp lệ: 

- Gold hoặc đáp án tham chiếu: 

- Prediction E0 / E1 / E2: 

- Nguyên nhân khảdĩ (nhãn, OCR, số, model, retrieval, prompt...): 

- Ảnh hưởng của lỗi đến người dùng: 

- Đềxuất thay đổi và phép thửkếtiếp: 

# **C Checklist cổng D1 và nghiệm thu cuối** 

16 

CSC4007 – Xửlý ngôn ngữtự nhiên 

ThS. Lê Thị Thùy Trang 

|Cổng|Dữliệu / minh chứng|Đạt khi|
|---|---|---|
|**D1 – Data readiness**|Nguồn + license, manifest/schema,<br>quality report, split, guideline, gold,<br>evaluation protocol|Có khảnăng tính metric đúng nhiệm<br>vụvà test không rò rỉ|
|**E – Experiment readiness**|E0/E1/E2, configs, log, predictions,<br>metric script, bảng đối chứng|Có thểtái lập các con sốbáo cáo|
|**F – Final acceptance**|Data Card, gold/protocol, E0–E2,<br>error analysis ≥10, demo, PDF, AI<br>logs, README|Đầy đủhồsơ và không có vi phạm<br>quyền/gian lận dữliệu|



**Ghi chú về tính áp dụng:** Định mức sốmẫu, thời lượng và kế hoạch nghiệm thu trong tài liệu dựa trên bản đề xuất CSC4007 v2.0. Nếu nhà trường hoặc giảng viên công bốquy định chính thức khác, áp dụng quy định chính thức và ghi rõ điều chỉnh trong thông báo giao bài. 
