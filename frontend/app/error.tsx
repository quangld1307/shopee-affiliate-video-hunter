'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <main><section className="panel"><h1>Chưa tải được nội dung</h1><p>Dữ liệu đã lưu vẫn được giữ lại. Bạn có thể thử mở lại trang.</p><button onClick={reset}>Thử lại</button></section></main>}
