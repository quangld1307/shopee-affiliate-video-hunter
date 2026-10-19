# Mầm — Xưởng nội dung

Ứng dụng web chạy trên máy cá nhân cho quy trình nguồn → video có quyền → biên tập → xuất gói → đăng thủ công → đối soát hoa hồng. Dành cho một người, khoảng 5–6 video/ngày. Giao diện tiếng Việt, ưu tiên Facebook và TikTok.

## Chức năng bản đầu

- Tổng quan dùng dữ liệu thật, không chèn số liệu minh họa.
- Lưu nguồn URL thủ công hoặc nhập CSV; chống URL trùng và báo lỗi từng dòng. Không tự tải video nền tảng.
- Nhập video tối đa 1 GB, kiểm tra FFprobe, SHA-256 chống tệp trùng, giữ tệp gốc và xem video.
- Hồ sơ quyền: chủ sở hữu, bằng chứng dạng văn bản, ngày hết hạn, kênh, quyền thương mại/biên tập/nhạc. Do người dùng xác nhận, không phải xác minh pháp lý tự động.
- Biên tập: chọn điểm cắt theo giây, crop giữa 9:16, chữ, phụ đề SRT nhập tay theo thời gian đoạn đã cắt. Khung xem phát nguồn; kết xuất mới áp dụng thay đổi.
- Lưu bản nháp; xác nhận sản phẩm, link và nội dung; xuất MP4 720×1280, ảnh bìa, caption có công bố Affiliate, hồ sơ quyền và checksum trong ZIP. Kiểm tra quyền trước/sau kết xuất và trước tải gói.
- Nhập CSV UTF-8 tối đa 10 MB; ánh xạ mã chuyển đổi/hoa hồng/trạng thái; xem trước 10 dòng; chống cộng trùng, cập nhật trạng thái và ghi lịch sử.
- Theo dõi tác vụ, một render mỗi lần; tác vụ bị ngắt được đánh dấu thất bại sau khởi động lại để xuất lại từ bản nháp.
- Tạo bản sao lưu, công cụ kiểm tra checksum/khôi phục vào thư mục mới.

## Cài trên Windows

Yêu cầu Node.js 24 LTS, Python 3.12, FFmpeg và FFprobe trong PATH (bản FFmpeg có libx264, drawtext và subtitles/libass). Cài từ nguồn chính thức hoặc qua Windows Package Manager:

```powershell
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install Gyan.FFmpeg
```

Mở cửa sổ dòng lệnh mới sau cài đặt. Từ thư mục repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\cai-dat.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\khoi-dong.ps1
```

Lệnh Bypass chỉ áp dụng tiến trình PowerShell chạy script; không đổi chính sách hệ thống. Có thể đọc và chạy từng lệnh trong script nếu máy có chính sách quản trị riêng. Mở trình duyệt tại địa chỉ script hiển thị. Ctrl+C để dừng. Cổng giao diện 3000, dịch vụ 8000, đều chỉ lắng nghe 127.0.0.1. Không mở ra mạng: bản này chưa có đăng nhập/phân quyền nhiều người.

GPU không bắt buộc; bản đầu dùng FFmpeg CPU 2 luồng. Chưa bật NVIDIA vì model card chưa được xác nhận và cần thử khả năng bộ mã hóa trên máy Windows thật.

## Phát triển trên Linux / môi trường đám mây

```bash
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-lock.txt
cd frontend
npm ci
npm run build
cd ..
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Cửa sổ khác, trong frontend:
npm run dev
```

Không cần tạo worktree; dùng checkout hiện tại trong môi trường cô lập.

## Kiểm thử

```bash
.venv/bin/python -m unittest backend.test_workflow -v
```

Bộ kiểm thử tạo video bằng FFmpeg trong thư mục tạm; kiểm tra chống trùng nguồn/tệp, URL không hợp lệ, chặn nguồn yêu cầu chéo, quyền thiếu/sai kênh/hết hạn, xuất video 9:16 thực có chữ và phụ đề tiếng Việt, manifest, đối soát CSV lặp/trạng thái đảo và sao lưu/khôi phục. Không chạm dữ liệu người dùng. Trên Windows thay `.venv/bin/python` bằng `.venv\Scripts\python.exe`.

## Dữ liệu và sao lưu

Dữ liệu trong `data/`, bản sao lưu tạo từ giao diện trong `backups/`; đều bị loại khỏi Git. Giữ bản sao trên ổ khác. Không xóa các tệp video hoặc ZIP trực tiếp khi ứng dụng đang chạy. Bằng chứng hiện là văn bản; lưu tài liệu gốc riêng và ghi tham chiếu đầy đủ.

Công cụ dòng lệnh, khi ứng dụng đã dừng:

```powershell
.venv\Scripts\python.exe scripts/sao_luu.py backup D:\sao-luu\mam.zip
.venv\Scripts\python.exe scripts/sao_luu.py verify D:\sao-luu\mam.zip
.venv\Scripts\python.exe scripts/sao_luu.py restore D:\sao-luu\mam.zip --data D:\thu-khoi-phuc
```

Kiểm tra thư mục mới, sau đó đặt biến `MAM_DATA_DIR` trỏ vào thư mục khôi phục trước khi chạy ứng dụng. Không ghi đè thư mục đang có dữ liệu. Khôi phục tự cập nhật đường dẫn tệp trong cơ sở dữ liệu. Bản sao lưu chứa video và bằng chứng nhạy cảm; giữ ở nơi riêng, chưa có mã hóa tự động.

## CSV hoa hồng

Dùng mã duy nhất của từng dòng chuyển đổi/hoa hồng, không chỉ mã đơn nếu đơn có nhiều dòng. Số tiền VND nguyên không có dấu phân cách. Chấp nhận trạng thái tiếng Việt như mẫu và `pending`, `approved`, `paid`, `rejected`, `reversed`. Mẫu trong `samples/` chỉ để học định dạng, không phải báo cáo Shopee chuẩn. Cần kiểm tra một CSV thật của tài khoản trước khi vận hành; chưa có tệp báo cáo thật được cung cấp. Không suy ra doanh thu theo kênh khi không có dữ liệu tracking.

## Chưa triển khai

Tự tìm kiếm/quét/tải từ nền tảng; tạo Affiliate link tự động; tự đăng; AI/ASR/voice; watchlist theo lịch; timeline kéo thả nhiều lớp; crop tùy vị trí; chiến dịch; xuất báo cáo nâng cao; đính kèm bằng chứng dạng tệp; phân quyền nhiều người; mã hóa backup; queue tự tiếp tục sau crash; đầy đủ 22 màn hình V3. Các chức năng API cần quyền chính thức. Không có khóa API nào cần nhập để chạy bản đầu.

Link được kiểm tra cấu trúc và chủ tên miền Shopee, còn đúng sản phẩm/tracking là xác nhận thủ công của bạn; HTTP 200 không chứng minh tracking Affiliate hoạt động. Những giới hạn này được giữ rõ trên giao diện và trong kế hoạch.

Xem `docs/KE-HOACH.md` để biết thứ tự hoàn thiện V3. Hiện việc build, render và kiểm thử được xác minh trên Linux; script và bộ mã hóa phải kiểm tra tiếp trên máy Windows thật trước khi coi là bản phát hành cho Windows.
