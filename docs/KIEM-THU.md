# Kết quả kiểm chứng bản đầu

Môi trường: Linux, Python 3.12, Node.js 24, FFmpeg CPU, Chromium. Chưa chạy Windows thật và chưa có CSV Shopee thật.

- `npm run build`: biên dịch và kiểm tra TypeScript thành công.
- `python -m unittest backend.test_workflow -v`: 6 bài kiểm thử tích hợp, dùng dữ liệu/video tạm.
- Kiểm thử API: nhập URL, nguồn trùng, URL nội bộ bị từ chối, nguồn yêu cầu chéo bị chặn, nhập nguồn hàng loạt có lỗi/trùng, video thật/hỏng/trùng.
- Quyền: thiếu hồ sơ bị chặn, sai kênh bị chặn, hết hạn bị chặn tải gói cũ. Kết xuất dọc 720×1280 có chữ/phụ đề tiếng Việt và hồ sơ checksum.
- CSV: dòng lỗi riêng, nhập hai lần không cộng trùng, trạng thái bị hủy cập nhật đúng.
- Sao lưu: tạo khi đang chạy, kiểm checksum, khôi phục vào thư mục khác, kiểm dữ liệu và đường dẫn video.
- Kiểm thử Chromium tự động: mở sáu mục, thêm nguồn qua biểu mẫu, nhập và đối soát lại CSV, upload video, xác nhận quyền, điền dự án, lưu nháp, render thật, tải ZIP, tạo sao lưu. Không ghi nhận lỗi JavaScript.
- Bố cục 1440px và 390px: không tràn ngang toàn trang; bảng rộng có vùng cuộn riêng.

## Cần kiểm chứng bằng dữ liệu/máy của chủ ứng dụng

- Cài đặt và khởi động trên Windows; FFmpeg có đủ bộ lọc/font.
- Định dạng CSV tài khoản Shopee thực tế, mã duy nhất từng dòng, trạng thái và đơn vị tiền.
- Thời gian render video dài thực tế và khả năng sử dụng NVIDIA.
- Kiểm tra sản phẩm, tracking Affiliate, quyền và chất lượng trên bài đăng thực tế. Các điều này không được chứng minh chỉ bởi bộ kiểm thử nội bộ.
- Toàn bộ 22 AT của SRS là mục tiêu V3; chưa tuyên bố tất cả đạt trong bản đầu.
