# Kế hoạch phát triển

## Phạm vi đã chốt
Một người sử dụng trên Windows, RAM 32 GB, trống 3 TB, GPU NVIDIA (cần xác nhận model khi tối ưu GPU). Mục tiêu 5–6 video/ngày. Facebook và TikTok ưu tiên; toàn bộ giao diện tiếng Việt. Không có API nền tảng được cấp. Custom Link và CSV Shopee dùng thủ công.

## Thứ tự và điều kiện nghiệm thu
1. Nền tảng: Next.js + TypeScript, FastAPI, SQLite, lưu tệp local. Dữ liệu giữ sau khởi động lại, lỗi hiển thị rõ. API chỉ nghe loopback.
2. Nguồn: thêm URL từng nền tảng, tìm kiếm, chống trùng, CSV nguồn. Không biến URL công khai thành quyền tải video.
3. Video và quyền: upload, kiểm tra FFprobe, SHA-256, hồ sơ quyền theo kênh và thời hạn. Thiếu quyền chặn xuất.
4. Biên tập: cắt, crop 9:16, chữ, phụ đề SRT; không sửa tệp gốc; lưu bản nháp. Xuất MP4 và gói ZIP kèm caption, link, manifest. Xác minh quyền trước và sau render.
5. Đối soát: ánh xạ cột CSV, xem trước, nhập idempotent theo mã chuyển đổi; tách chờ duyệt/đã duyệt/đã thanh toán/hủy; giữ lịch sử thay đổi. Số tiền VND dùng số nguyên.
6. Hoàn thiện bản đầu: kiểm thử luồng thật, chống đường dẫn nguy hiểm và URL nội bộ, sao lưu/khôi phục, hướng dẫn Windows, kiểm tra giao diện bàn phím và lỗi.
7. Bản tiếp: chiến dịch, lịch đăng tay, ghi nhận URL và số liệu bài đăng; phụ đề tự động local, AI caption có duyệt, giới hạn chi phí.
8. Mở rộng: connector chính thức theo quyền, watchlist, PostgreSQL và hàng đợi riêng khi có nhu cầu; nhiều người dùng và phân quyền trước khi mở mạng.

## Nguyên tắc
Không tự đăng, không lấy cookie hoặc vượt hạn chế nền tảng. Không coi link sản phẩm là link Affiliate. Không dùng số liệu giả làm số liệu thật. API AI mặc định tắt, chưa giả định đồng ý gửi media bên ngoài. Không cần GPU cho luồng FFmpeg CPU cơ bản.

## Trạng thái
Các bước triển khai và giới hạn thực tế được ghi trong README; đây là kế hoạch, không phải tuyên bố mọi tiêu chí đã đạt.

## Phân rã chi tiết và phụ thuộc

| Nhóm | Bản đầu đang có | Bước tiếp theo | Điều kiện làm sau |
|---|---|---|---|
| Nguồn và khám phá | Nhập URL, CSV, tìm trong nguồn đã lưu, báo lỗi/trùng | Chuẩn hóa URL theo từng nền tảng, bộ lọc và thẻ, nhật ký nhập | Tìm kiếm tự động, metadata, watchlist chỉ sau kiểm tra quyền API/quota |
| Sản phẩm | Tên sản phẩm/biến thể và xác nhận thủ công trong dự án | Danh mục sản phẩm riêng, mã shop/SKU, nhiều video–nhiều sản phẩm, lịch sử giá/hoa hồng nhập tay | Đồng bộ snapshot tự động cần nguồn chính thức |
| Quyền sử dụng | Hồ sơ văn bản, chủ thể, quyền theo kênh, ngày hết hạn, chặn xuất/tải | Tải bằng chứng tệp, duyệt từng phiên bản, thao tác thu hồi riêng, cảnh báo các bài đã đăng, hồ sơ khiếu nại | Không cho AI tự phê duyệt bằng chứng |
| Kho video | Upload, probe, checksum chính xác, xem nguồn, giữ gốc | Thẻ/bộ sưu tập, trạng thái cách ly, thumbnail lưới, nhận diện gần trùng có duyệt | Tải từ đối tác qua URL chỉ khi có quyền, không tự tải nguồn công khai |
| Biên tập | Cắt theo thời gian, crop giữa 9:16, chữ, SRT, bản nháp | Xem trước đã xử lý, đổi vị trí crop, chọn kiểu phụ đề, điều chỉnh vị trí chữ; sau đó mới timeline kéo thả/nhiều lớp | Voice/nhạc bổ sung cần quyền dùng thương mại |
| Gói nội dung | MP4, ảnh bìa, caption/công bố, link, hồ sơ và checksum, ZIP | Hồ sơ phiên bản khóa, lời đăng riêng từng kênh, xuất hàng loạt, kiểm tra link và sản phẩm sâu hơn | Không coi thao tác tải gói là đã đăng bài |
| Affiliate | Dán link từ Custom Link; kiểm tên miền; người dùng xác nhận đúng sản phẩm | Kho link riêng gắn sản phẩm/kênh/chiến dịch; thời điểm xác nhận; danh sách cần kiểm tra lại | Tạo link tự động/subID chỉ bật khi được cấp |
| Đối soát | Ánh xạ CSV, xem trước, số nguyên VND, chống cộng trùng, lịch sử thay đổi, bốn nhóm trạng thái | Ánh xạ báo cáo thật, hỗ trợ cách ghi tiền Việt Nam, khóa ghép dòng đơn/nguồn, lịch sử trên giao diện, báo cáo xuất | Doanh thu theo bài/kênh cần bằng chứng attribution |
| Vận hành | Một kết xuất/lần, trạng thái/lỗi, khởi động lại đánh dấu lỗi, sao lưu và khôi phục | Kiểm dung lượng dự phòng, retention có xem trước, hàng đợi bền vững, hủy/retry, nhật ký giao diện | Dịch vụ queue riêng khi khối lượng tăng |
| Chiến dịch và phân tích | Tổng quan đếm dữ liệu thật | Board/lịch đăng tay, URL bài đăng, số liệu tự nhập; funnel và đối soát theo chiến dịch | So sánh hiệu quả/đề xuất tối ưu cần đủ dữ liệu thực |
| AI | Tắt mặc định | ASR local tiếng Việt; caption/gợi ý có duyệt; chính sách model và ngân sách | API từ xa chỉ sau cấu hình provider, hạn mức và đồng ý gửi media |
| Người dùng | Một chủ máy, loopback, chặn origin/host không hợp lệ | Củng cố đăng nhập khi cần chia sẻ | RBAC, nhiều workspace và PostgreSQL trước khi triển khai mạng |

## Các mốc sử dụng thực tế

### Mốc A — Xác nhận bản đầu trên máy Windows
1. Cài Node/Python/FFmpeg và chạy script cài đặt.
2. Chạy giao diện, thêm 10 URL, nhập một CSV có dòng lỗi và dòng trùng.
3. Nhập 3 video tự sở hữu; thử 1 tệp trùng và 1 tệp hỏng.
4. Xác nhận quyền, cắt video, thêm chữ/phụ đề, dán link Affiliate thật đã tạo thủ công.
5. Kiểm tra 1 gói MP4/ảnh/caption/link/manifest; đăng thủ công lên kênh thử nghiệm.
6. Nhập CSV hoa hồng thật (có thể ẩn dữ liệu cá nhân); chốt ý nghĩa mã chuyển đổi và trạng thái. Nhập lần hai phải không tăng tổng.
7. Sao lưu và khôi phục sang thư mục riêng; mở lại video, quyền, bản nháp và số liệu.
8. Ghi kết quả CPU/RAM/thời gian render; sau đó mới cân nhắc NVIDIA.

### Mốc B — Dùng đều 5–6 video/ngày
Hoàn thiện danh mục sản phẩm/link, xem trước sau xử lý, chỉnh crop/chữ dễ dùng hơn, kiểm dung lượng, phục hồi job, lịch đăng và ghi nhận bài. Không bắt đầu dashboard doanh thu sâu khi CSV thật chưa được xác minh.

### Mốc C — Giảm thao tác bằng AI
Thử ASR local trên 10 video tiếng Việt có quyền. Đo độ chính xác và tốc độ; cho sửa phụ đề. Sau đó thêm caption/hook, kiểm claim và ngân sách API. Kết quả AI luôn là đề xuất.

### Mốc D — Hoàn thiện mục tiêu V3
Thực hiện lần lượt 22 AT trong tài liệu nguồn. Với connector chưa được cấp quyền, nghiệm thu luồng thủ công/tham khảo và ghi tính năng điều kiện chưa bật; không mô phỏng thành tích hợp thật. Kiểm tra bảo mật, hiệu năng 10.000 metadata, RPO/RTO và hướng dẫn nâng cấp trước phát hành ổn định.

## Ranh giới hoàn thành
Bản đầu có thể kiểm thử xuyên luồng, nhưng chưa tương đương toàn bộ SRS V3. Chỉ gọi bản Windows ổn định sau mốc A; chỉ gọi hoàn thiện V3 sau mốc D. Không thể xác nhận quyền API, dữ liệu CSV thật hoặc tốc độ trên PC chỉ từ môi trường Linux đám mây.
