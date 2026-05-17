"""Generate the full RUMAH KARIR documentation as a .docx file.

Run:
    python docs/generate_docs.py

Output is written to ``docs/RUMAH_KARIR_Dokumentasi.docx``.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor


OUTPUT = Path(__file__).resolve().parent / "RUMAH_KARIR_Dokumentasi.docx"


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str) -> None:
    p = doc.add_paragraph(text)
    for run in p.runs:
        run.font.size = Pt(11)


def add_bullet(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="List Bullet")


def add_code(doc: Document, code: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(code)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x11, 0x11, 0x11)


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
    for r, row in enumerate(rows, start=1):
        for i, cell in enumerate(row):
            table.rows[r].cells[i].text = cell


def build() -> None:
    doc = Document()

    # Title page
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run("RUMAH KARIR")
    tr.bold = True
    tr.font.size = Pt(36)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub.add_run("Dokumentasi Sistem & Alur Kerja")
    sr.font.size = Pt(16)

    doc.add_paragraph()
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.CENTER
    intro.add_run(
        "Platform pencarian kerja berbasis Flask + SQLite dengan "
        "pencocokan CV otomatis, autentikasi OTP via SMTP, dashboard admin, "
        "dan pendaftaran perusahaan dengan persetujuan."
    )
    doc.add_page_break()

    # 1. Overview
    add_heading(doc, "1. Ringkasan Proyek", level=1)
    add_para(
        doc,
        "RUMAH KARIR adalah aplikasi web untuk pencarian lowongan kerja yang "
        "menggabungkan halaman publik (browsing lowongan + statistik), "
        "akun pengguna dengan unggah CV PDF dan pencocokan otomatis, "
        "akun perusahaan dengan persetujuan admin, serta dashboard admin "
        "lengkap (CRUD perusahaan, lowongan, user, mitra, dan mode "
        "maintenance). Tema visual menggunakan palet abu-abu, hitam, dan "
        "putih sesuai permintaan, dan seluruh halaman responsif untuk "
        "desktop, tablet, dan mobile (dengan hamburger menu).",
    )
    add_bullet(doc, "Bahasa: Python (Flask), HTML, CSS, JS, dan sedikit React via CDN.")
    add_bullet(doc, "Database: SQLite (modul stdlib sqlite3).")
    add_bullet(doc, "Email/OTP: SMTP (Gmail) via stdlib smtplib.")
    add_bullet(doc, "Parsing CV: pypdf untuk ekstraksi teks dari PDF.")
    add_bullet(doc, "Dokumentasi: python-docx (file ini).")

    doc.add_page_break()

    # 2. Folder structure
    add_heading(doc, "2. Struktur Folder", level=1)
    add_para(doc, "Struktur folder utama proyek:")
    add_code(
        doc,
        """cari-kerjaan/
├── app.py                       # Entrypoint Flask
├── config.py                    # Konfigurasi (env)
├── seed.py                      # Seeder data perusahaan + lowongan
├── requirements.txt
├── .env.example
├── README.md
├── docs/
│   ├── generate_docs.py         # Script ini
│   └── RUMAH_KARIR_Dokumentasi.docx
├── instance/
│   └── rumahkarir.db            # SQLite database (auto-generated)
├── backend/
│   ├── __init__.py
│   ├── database.py              # Helper sqlite3 (connection + helpers)
│   ├── auth.py                  # Session, decorator login_required, hashing
│   ├── mailer.py                # SMTP OTP delivery
│   ├── cv_parser.py             # PDF parsing + matching skill/age/experience
│   ├── middleware.py            # Maintenance mode middleware
│   └── routes/
│       ├── pages.py             # HTML routes (login, register, dashboard ...)
│       ├── api_auth.py          # /api/auth/*
│       ├── api_jobs.py          # /api/jobs/*, /api/companies/*, /api/stats
│       ├── api_cv.py            # /api/cv/upload
│       ├── api_partners.py      # /api/partners, /api/experiences
│       ├── api_company.py       # /api/company/* (untuk akun perusahaan)
│       └── api_admin.py         # /api/admin/* (untuk admin)
├── static/
│   ├── css/{main,dashboard}.css
│   ├── js/main.js
│   ├── img/indonesia-map.svg
│   └── uploads/{cv,photos,partners}/
└── templates/
    ├── base.html
    ├── index.html / jobs.html / job_detail.html
    ├── login.html / register.html / verify_otp.html
    ├── cv_upload.html / share_experience.html / maintenance.html
    ├── admin/ ... (sidebar dashboard pages)
    └── company/ (dashboard + post_job)""",
    )

    doc.add_page_break()

    # 3. Library used
    add_heading(doc, "3. Library / Dependencies", level=1)
    add_table(
        doc,
        ["Library", "Versi", "Fungsi"],
        [
            ["Flask", "3.0.3", "Web framework + routing + templating (Jinja2)."],
            ["Werkzeug", "3.0.3", "Password hashing + secure_filename + WSGI utilities."],
            ["python-dotenv", "1.0.1", "Load .env saat development."],
            ["pypdf", "4.3.1", "Membaca teks dari file PDF (CV)."],
            ["python-docx", "1.1.2", "Generate dokumentasi .docx (file ini)."],
            ["Pillow", "10.4.0", "Pendukung pemrosesan image upload (opsional)."],
            ["smtplib (stdlib)", "—", "Kirim email OTP via SMTP (Gmail)."],
            ["sqlite3 (stdlib)", "—", "Database engine."],
            ["React 18 (CDN) + Babel", "—", "Sedikit komponen (search engine pada homepage)."],
        ],
    )

    # 4. Database schema
    doc.add_page_break()
    add_heading(doc, "4. Database Schema (SQLite)", level=1)
    add_para(
        doc,
        "Skema didefinisikan di backend/database.py dan dibuat otomatis "
        "saat aplikasi pertama kali dijalankan (init_db).",
    )

    for title, sql in (
        (
            "users",
            "CREATE TABLE users (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  role TEXT NOT NULL CHECK(role IN ('user','company','admin')),\n"
            "  email TEXT NOT NULL UNIQUE,\n"
            "  password_hash TEXT NOT NULL,\n"
            "  full_name TEXT, username TEXT, birth_date TEXT, photo_path TEXT,\n"
            "  is_verified INTEGER NOT NULL DEFAULT 0,\n"
            "  is_approved INTEGER NOT NULL DEFAULT 1,\n"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "companies",
            "CREATE TABLE companies (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,\n"
            "  name TEXT NOT NULL, slug TEXT UNIQUE,\n"
            "  industry TEXT, website TEXT, address TEXT,\n"
            "  province TEXT, city TEXT, country TEXT DEFAULT 'Indonesia',\n"
            "  description TEXT, logo_path TEXT, employees TEXT,\n"
            "  founded_year INTEGER,\n"
            "  is_approved INTEGER NOT NULL DEFAULT 1,\n"
            "  search_count INTEGER NOT NULL DEFAULT 0,\n"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "jobs",
            "CREATE TABLE jobs (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,\n"
            "  title TEXT NOT NULL, description TEXT, requirements TEXT,\n"
            "  skills TEXT, employment_type TEXT,\n"
            "  country TEXT, province TEXT, city TEXT,\n"
            "  salary_min INTEGER, salary_max INTEGER,\n"
            "  min_experience INTEGER DEFAULT 0,\n"
            "  min_age INTEGER, max_age INTEGER,\n"
            "  is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "otps",
            "CREATE TABLE otps (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  email TEXT NOT NULL, code TEXT NOT NULL,\n"
            "  purpose TEXT NOT NULL DEFAULT 'register',\n"
            "  expires_at INTEGER NOT NULL,\n"
            "  used INTEGER NOT NULL DEFAULT 0,\n"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "partners",
            "CREATE TABLE partners (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  name TEXT, image_path TEXT NOT NULL, link TEXT,\n"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "experiences",
            "CREATE TABLE experiences (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,\n"
            "  rating INTEGER NOT NULL DEFAULT 5, title TEXT, body TEXT NOT NULL,\n"
            "  is_visible INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "cv_uploads",
            "CREATE TABLE cv_uploads (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,\n"
            "  file_path TEXT NOT NULL,\n"
            "  parsed_skills TEXT, parsed_age INTEGER, parsed_experience_years INTEGER,\n"
            "  raw_text TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
        (
            "settings",
            "CREATE TABLE settings (\n"
            "  key TEXT PRIMARY KEY, value TEXT NOT NULL\n"
            ");",
        ),
        (
            "company_search_log",
            "CREATE TABLE company_search_log (\n"
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,\n"
            "  created_at TEXT DEFAULT CURRENT_TIMESTAMP\n"
            ");",
        ),
    ):
        add_heading(doc, f"4.{title}", level=2)
        add_code(doc, sql)

    # 5. Query Examples
    doc.add_page_break()
    add_heading(doc, "5. Contoh Query yang Dipakai Aplikasi", level=1)
    add_heading(doc, "5.1 Pencarian lowongan", level=2)
    add_code(
        doc,
        "SELECT j.id, j.title, j.skills, j.city, j.country, c.name AS company_name\n"
        "FROM jobs j JOIN companies c ON c.id = j.company_id\n"
        "WHERE j.is_active=1 AND c.is_approved=1\n"
        "  AND (j.title LIKE ? OR j.skills LIKE ? OR c.name LIKE ?)\n"
        "  AND j.country LIKE ? AND j.province LIKE ? AND j.city LIKE ?\n"
        "ORDER BY j.created_at DESC LIMIT ? OFFSET ?;",
    )
    add_heading(doc, "5.2 Top 10 perusahaan dengan lowongan terbanyak", level=2)
    add_code(
        doc,
        "SELECT c.id, c.name, COUNT(j.id) AS open_jobs\n"
        "FROM companies c LEFT JOIN jobs j ON j.company_id=c.id AND j.is_active=1\n"
        "WHERE c.is_approved=1\n"
        "GROUP BY c.id ORDER BY open_jobs DESC LIMIT 10;",
    )
    add_heading(doc, "5.3 Toggle maintenance", level=2)
    add_code(
        doc,
        "INSERT INTO settings(key,value) VALUES('maintenance_mode', ?)\n"
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value;",
    )
    add_heading(doc, "5.4 Verifikasi OTP", level=2)
    add_code(
        doc,
        "SELECT id, expires_at, used FROM otps\n"
        "WHERE email=? AND code=? AND purpose='register'\n"
        "ORDER BY id DESC LIMIT 1;\n"
        "-- jika valid, UPDATE otps SET used=1 WHERE id=?;",
    )
    add_heading(doc, "5.5 Approval perusahaan", level=2)
    add_code(
        doc,
        "UPDATE users SET is_approved=1, is_verified=1 WHERE id=?;\n"
        "UPDATE companies SET is_approved=1 WHERE owner_user_id=?;",
    )

    # 6. System flow
    doc.add_page_break()
    add_heading(doc, "6. Alur Kerja Sistem", level=1)

    add_heading(doc, "6.1 Pendaftaran user biasa", level=2)
    for s in (
        "1. User membuka /register dan memilih tab 'Sebagai Pengguna'.",
        "2. Mengisi nama lengkap, tanggal lahir, foto profil, email, password.",
        "3. Server menyimpan user (is_verified=0), generate OTP 6 digit, simpan ke tabel otps, dan kirim email via SMTP.",
        "4. User membuka /verify-otp, memasukkan kode. OTP diverifikasi, is_verified=1.",
        "5. User redirect ke /login dan masuk ke aplikasi.",
    ):
        add_bullet(doc, s)

    add_heading(doc, "6.2 Pendaftaran perusahaan", level=2)
    for s in (
        "1. Perusahaan membuka /register dan memilih tab 'Sebagai Perusahaan'.",
        "2. Mengisi data perusahaan (nama, industri, kota, alamat, dsb).",
        "3. Server membuat user(role='company', is_approved=0) + companies(is_approved=0).",
        "4. Kirim OTP via SMTP untuk verifikasi email.",
        "5. Admin membuka /admin/approvals untuk menyetujui (POST /api/admin/users/<id>/approve).",
        "6. Setelah disetujui, perusahaan dapat login dan masuk ke /company untuk memasang lowongan.",
    ):
        add_bullet(doc, s)

    add_heading(doc, "6.3 Upload CV & matching", level=2)
    for s in (
        "1. User login dan membuka /cv.",
        "2. Upload PDF -> POST /api/cv/upload (server menyimpan file ke static/uploads/cv).",
        "3. pypdf mengekstrak text. cv_parser._detect_skills, _detect_age, _detect_experience_years memprosesnya.",
        "4. Server menarik seluruh jobs aktif, lalu match_jobs_for_cv menghitung skor "
        "(skill 80%, experience 10%, age 10%).",
        "5. Jika best score < 50 -> sistem mengirim daftar skill suggestion paling sering kurang.",
    ):
        add_bullet(doc, s)

    add_heading(doc, "6.4 Mode maintenance", level=2)
    for s in (
        "1. Admin men-toggle di /admin/maintenance -> POST /api/admin/maintenance { enabled: true }.",
        "2. Middleware @app.before_request membaca settings.maintenance_mode.",
        "3. Jika '1' dan user bukan admin, request dijawab dengan halaman maintenance.html (atau JSON 503 untuk /api/*).",
        "4. Endpoint login/logout tetap dibuka agar admin bisa masuk.",
    ):
        add_bullet(doc, s)

    add_heading(doc, "6.5 Toggle 'Lihat Selengkapnya'", level=2)
    for s in (
        "1. /api/jobs mengembalikan flag _locked:true bila user belum login.",
        "2. /api/jobs/<id> juga mengembalikan versi terpotong + _locked bila belum login.",
        "3. Frontend menampilkan banner 'Login untuk melihat selengkapnya' dan mengaburkan body detail.",
    ):
        add_bullet(doc, s)

    # 7. API list
    doc.add_page_break()
    add_heading(doc, "7. Daftar Endpoint REST API", level=1)
    add_para(doc, "Semua endpoint mengembalikan JSON dan menggunakan format RESTful.")
    add_table(
        doc,
        ["Method", "Path", "Auth", "Keterangan"],
        [
            ["POST", "/api/auth/register", "-", "Daftar user atau perusahaan (multipart)."],
            ["POST", "/api/auth/verify-otp", "-", "Verifikasi OTP yang dikirim ke email."],
            ["POST", "/api/auth/resend-otp", "-", "Kirim ulang kode OTP."],
            ["POST", "/api/auth/login", "-", "Login user / perusahaan / admin."],
            ["POST", "/api/auth/logout", "-", "Logout sesi."],
            ["GET",  "/api/auth/me", "-", "Detail user saat ini."],
            ["GET",  "/api/jobs", "-", "Cari lowongan (q, country, province, city, page)."],
            ["GET",  "/api/jobs/<id>", "-", "Detail lowongan; konten penuh hanya untuk login user."],
            ["GET",  "/api/companies/top-searched", "-", "Top perusahaan paling dicari."],
            ["GET",  "/api/companies/top-openings", "-", "Top 10 perusahaan dengan lowongan terbanyak."],
            ["GET",  "/api/companies/<id>", "-", "Detail perusahaan + daftar lowongan."],
            ["GET",  "/api/stats", "-", "Statistik komunitas (users, companies, jobs)."],
            ["GET",  "/api/locations/provinces", "-", "Daftar provinsi unik."],
            ["POST", "/api/cv/upload", "user", "Upload PDF + matching otomatis."],
            ["GET",  "/api/partners", "-", "Daftar mitra kerja sama."],
            ["GET",  "/api/experiences", "-", "Daftar pengalaman pengguna."],
            ["POST", "/api/experiences", "user", "Bagikan pengalaman."],
            ["GET",  "/api/company/me", "company", "Profil perusahaan login."],
            ["GET",  "/api/company/jobs", "company", "Lowongan milik perusahaan login."],
            ["POST", "/api/company/jobs", "company", "Tambah lowongan baru."],
            ["DELETE","/api/company/jobs/<id>", "company", "Hapus lowongan milik perusahaan."],
            ["GET",  "/api/admin/stats", "admin", "Statistik admin lengkap."],
            ["GET",  "/api/admin/users", "admin", "Daftar user (?q=)."],
            ["PUT",  "/api/admin/users/<id>", "admin", "Update data user."],
            ["DELETE","/api/admin/users/<id>", "admin", "Hapus user."],
            ["POST", "/api/admin/users/<id>/approve", "admin", "Approve user perusahaan."],
            ["GET",  "/api/admin/pending-companies", "admin", "Daftar perusahaan menunggu approval."],
            ["GET",  "/api/admin/companies", "admin", "Daftar perusahaan (?q=)."],
            ["POST", "/api/admin/companies", "admin", "Tambah perusahaan."],
            ["PUT",  "/api/admin/companies/<id>", "admin", "Update perusahaan."],
            ["DELETE","/api/admin/companies/<id>", "admin", "Hapus perusahaan."],
            ["GET",  "/api/admin/jobs", "admin", "Daftar lowongan (?q=)."],
            ["POST", "/api/admin/jobs", "admin", "Tambah lowongan."],
            ["DELETE","/api/admin/jobs/<id>", "admin", "Hapus lowongan."],
            ["POST", "/api/admin/partners", "admin", "Tambah mitra (upload gambar)."],
            ["DELETE","/api/admin/partners/<id>", "admin", "Hapus mitra."],
            ["GET",  "/api/admin/experiences", "admin", "Moderasi pengalaman user."],
            ["DELETE","/api/admin/experiences/<id>", "admin", "Hapus pengalaman."],
            ["GET",  "/api/admin/maintenance", "admin", "Status mode maintenance."],
            ["POST", "/api/admin/maintenance", "admin", "Toggle mode maintenance."],
        ],
    )

    # 8. CV parsing detail
    doc.add_page_break()
    add_heading(doc, "8. Algoritma CV Parsing & Matching", level=1)
    add_para(
        doc,
        "Modul backend/cv_parser.py menggunakan pendekatan deterministic, "
        "berbasis dictionary skill + regex untuk umur dan pengalaman. "
        "Pendekatan ini sengaja dipilih agar offline-friendly, ringan, dan "
        "tidak butuh model ML.",
    )

    add_heading(doc, "8.1 Ekstraksi teks", level=2)
    add_para(
        doc,
        "Menggunakan pypdf.PdfReader untuk membaca semua halaman PDF "
        "dan menggabungkan hasil extract_text(). Bila file hasil scan "
        "(tanpa teks), sistem mengembalikan error: 'CV tidak terbaca'.",
    )

    add_heading(doc, "8.2 Deteksi skill", level=2)
    add_para(
        doc,
        "Setiap skill canonical (mis: 'python') memiliki alias daftar. "
        "Sistem mencari pola \\\\b<alias>\\\\b di teks (case-insensitive) "
        "dan menyatukan hasilnya menjadi list skill kandidat.",
    )

    add_heading(doc, "8.3 Deteksi umur", level=2)
    add_bullet(doc, "Mencari 'umur', 'usia', 'age', 'berusia' diikuti dua digit.")
    add_bullet(doc, "Mencari tanggal lahir (dd-mm-yyyy / dd Bulan yyyy) dan menghitung umur dari hari ini.")

    add_heading(doc, "8.4 Deteksi pengalaman", level=2)
    add_bullet(doc, "Mencari 'X tahun pengalaman' / 'X years of experience'.")
    add_bullet(doc, "Menjumlahkan rentang tanggal pekerjaan (2020 - 2023 ≈ 3 tahun). Hasil akhir = max.")

    add_heading(doc, "8.5 Scoring", level=2)
    add_para(doc, "Setiap lowongan mendapatkan skor 0–100:")
    add_bullet(doc, "Skill: (matched / total skill job) × 80.")
    add_bullet(doc, "Experience: 10 jika cv.experience >= min_experience else 0.")
    add_bullet(doc, "Age: 10 jika cv.age sesuai min_age..max_age (atau usia tidak terdeteksi) else 0.")
    add_para(doc, "Match terbaik di atas 50 dianggap 'has_good_match'. Jika tidak, sistem mengembalikan saran skill yang paling sering hilang.")

    # 9. SMTP
    doc.add_page_break()
    add_heading(doc, "9. Konfigurasi SMTP (Gmail OTP)", level=1)
    add_para(doc, "Pengaturan ada di .env (lihat .env.example). Variabel yang dibaca:")
    add_table(
        doc,
        ["Variable", "Default", "Keterangan"],
        [
            ["SMTP_HOST", "smtp.gmail.com", "Host SMTP."],
            ["SMTP_PORT", "587", "587 untuk STARTTLS, 465 untuk SSL."],
            ["SMTP_USER", "(kosong)", "Email pengirim."],
            ["SMTP_PASS", "(kosong)", "App Password Gmail (bukan password akun)."],
            ["SMTP_FROM", "RUMAH KARIR <no-reply@...>", "From header email."],
        ],
    )
    add_para(
        doc,
        "Jika SMTP tidak dikonfigurasi, OTP tetap dibuat dan disimpan tetapi "
        "dicatat ke logger Flask (untuk debugging lokal). Cara mengaktifkan: "
        "buat App Password di akun Google (myaccount.google.com -> Security -> "
        "App Passwords) dan paste di SMTP_PASS.",
    )

    # 10. Admin
    doc.add_page_break()
    add_heading(doc, "10. Admin Account & Hak Akses", level=1)
    add_para(doc, "Akun admin di-hardcode dengan kredensial default:")
    add_code(doc, "Email   : admin@admin.com\nPassword: admin123")
    add_para(
        doc,
        "Dapat di-override via env ADMIN_EMAIL / ADMIN_PASSWORD. Admin tidak "
        "disimpan di tabel users; login admin diidentifikasi langsung pada "
        "endpoint /api/auth/login. Sesi admin memiliki role='admin'.",
    )

    add_heading(doc, "10.1 Hak akses", level=2)
    add_bullet(doc, "Admin: akses penuh ke /admin/* dan /api/admin/*.")
    add_bullet(doc, "Perusahaan (role=company, is_approved=1): akses /company/*.")
    add_bullet(doc, "User biasa (role=user, is_verified=1): akses CV upload, share experience, lihat detail lowongan.")
    add_bullet(doc, "Public: lihat lowongan dengan _locked, statistik, partner, pengalaman.")

    # 11. Running
    doc.add_page_break()
    add_heading(doc, "11. Cara Menjalankan", level=1)
    add_code(
        doc,
        "python -m venv .venv\n"
        "source .venv/bin/activate   # Windows: .venv\\Scripts\\activate\n"
        "pip install -r requirements.txt\n"
        "cp .env.example .env        # isi SMTP_USER & SMTP_PASS\n"
        "python seed.py              # opsional, isi 23 perusahaan + 69 lowongan demo\n"
        "python app.py               # http://127.0.0.1:5000\n"
        "python docs/generate_docs.py  # regenerate dokumentasi .docx",
    )

    # 12. Sumber data lowongan (external scrapers / API)
    doc.add_page_break()
    add_heading(doc, "12. Sumber Data Lowongan & Integrasi API Eksternal", level=1)
    add_para(
        doc,
        "Database lowongan diisi dengan kombinasi data hasil scraping job "
        "board publik dan REST API gratis. Semua data diambil dengan rate "
        "limit konservatif dan disimpan sebagai snapshot JSON di "
        "scrapers/data/* sebelum di-import ke SQLite. Importer bersifat "
        "idempotent: perusahaan di-dedup case-insensitive berdasarkan nama "
        "dan lowongan di-dedup berdasarkan (company_id, title).",
    )

    add_heading(doc, "12.1 Ringkasan sumber data", level=2)
    add_table(
        doc,
        ["Sumber", "Tipe", "Auth", "Cakupan", "Script scraper"],
        [
            [
                "Kalibrr.id",
                "HTML SSR (__NEXT_DATA__)",
                "Tidak ada",
                "Indonesia, 21 industri x 2 mode (umum + WFH)",
                "scrapers/kalibrr_scraper.py",
            ],
            [
                "RemoteOK",
                "REST JSON",
                "Tidak ada",
                "Global, semua lowongan remote (full feed)",
                "scrapers/remoteok_scraper.py",
            ],
            [
                "arbeitnow.com",
                "REST JSON (paginated)",
                "Tidak ada",
                "Global (fokus EU + remote), 10 halaman x 100",
                "scrapers/arbeitnow_scraper.py",
            ],
            [
                "Jobicy.com",
                "REST JSON",
                "Tidak ada",
                "Global remote, 15 industri x 100",
                "scrapers/jobicy_scraper.py",
            ],
            [
                "WeWorkRemotely",
                "RSS XML",
                "Tidak ada",
                "Global remote, 8 kategori (programming, design, sales, dsb)",
                "scrapers/weworkremotely_scraper.py",
            ],
            [
                "Adzuna.com",
                "REST JSON",
                "API key (gratis)",
                "Indonesia, sweep 20 kata kunci",
                "scrapers/adzuna_scraper.py",
            ],
        ],
    )

    add_heading(doc, "12.2 Endpoint API yang dipakai", level=2)
    add_table(
        doc,
        ["Sumber", "Endpoint", "Method", "Query params penting"],
        [
            [
                "Kalibrr",
                "https://www.kalibrr.id/job-board/i/<industry>/<page>",
                "GET (HTML)",
                "industry, work_from_home",
            ],
            [
                "RemoteOK",
                "https://remoteok.com/api",
                "GET",
                "(tanpa parameter)",
            ],
            [
                "arbeitnow",
                "https://www.arbeitnow.com/api/job-board-api",
                "GET",
                "?page=N",
            ],
            [
                "Jobicy",
                "https://jobicy.com/api/v2/remote-jobs",
                "GET",
                "?count=100&industry=...&geo=...",
            ],
            [
                "WWR (RSS)",
                "https://weworkremotely.com/categories/<slug>.rss",
                "GET",
                "(tanpa parameter)",
            ],
            [
                "Adzuna",
                "https://api.adzuna.com/v1/api/jobs/id/search/<page>",
                "GET",
                "app_id, app_key, results_per_page, what",
            ],
        ],
    )

    add_heading(doc, "12.3 Field yang diambil", level=2)
    add_para(
        doc,
        "Berikut field yang berhasil di-mapping ke kolom database. Field "
        "yang tidak ada di sumber bernilai NULL.",
    )
    add_table(
        doc,
        ["Kolom DB", "Kalibrr", "RemoteOK", "arbeitnow", "Jobicy", "WWR", "Adzuna"],
        [
            ["title", "name", "position", "title", "jobTitle", "title (split ':')", "title"],
            ["company_name", "company.name", "company", "company_name", "companyName", "title prefix", "company.display_name"],
            ["description", "description (HTML)", "description (HTML)", "description (HTML)", "jobDescription", "description (RSS)", "description (HTML)"],
            ["requirements", "qualifications + Sumber", "tags + Sumber", "Sumber link", "Sumber link", "Sumber link", "Sumber link"],
            ["country", "googleLocation.country", "heuristik dari location", "heuristik", "heuristik dari jobGeo", "region", "Indonesia"],
            ["province", "googleLocation.region (normalized)", "-", "-", "-", "-", "location.area[1] (normalized)"],
            ["city", "googleLocation.city (normalized)", "location", "location", "jobGeo", "region", "location.area[2]"],
            ["salary_min/max", "baseSalary/maximumSalary (IDR only)", "salary_min/max (USD/yr -> IDR/bln)", "-", "salaryMin/Max", "-", "salary_min/max (IDR)"],
            ["employment_type", "tenure (mapped)", "Remote", "job_types[0]", "jobType[0]", "Remote", "contract_time/contract_type"],
            ["skills", "-", "tags (join ',')", "tags (join ',')", "-", "-", "-"],
            ["min_experience", "workExperience bucket (mapped)", "0", "0", "0", "0", "0"],
        ],
    )

    add_heading(doc, "12.4 Contoh response Kalibrr (__NEXT_DATA__)", level=2)
    add_para(
        doc,
        "Kalibrr adalah Next.js SSR. Setiap halaman job-board memuat "
        "<script id=\"__NEXT_DATA__\"> berisi JSON. Path job:",
    )
    add_code(
        doc,
        "props.pageProps.jobs = [\n"
        "  {\n"
        "    id: 267040,\n"
        "    name: \"Sales Canvassing EDC Klungkung\",\n"
        "    slug: \"sales-canvassing-edc-klungkung\",\n"
        "    description: \"<p>Mencari new sales/UMKM ...</p>\",\n"
        "    qualifications: \"<ul><li>Berpengalaman ...</li></ul>\",\n"
        "    tenure: \"Full time\",\n"
        "    workExperience: 200,           // 100|200|300|400 bucket\n"
        "    baseSalary: 5000000,\n"
        "    maximumSalary: 6000000,\n"
        "    salaryCurrency: \"IDR\",\n"
        "    salaryInterval: \"month\",\n"
        "    isWorkFromHome: false,\n"
        "    googleLocation: { addressComponents: {\n"
        "      country: \"Indonesia\", region: \"Bali\", city: \"Klungkung\"\n"
        "    }},\n"
        "    company: {\n"
        "      code: \"buku-warung\",\n"
        "      name: \"Buku Warung\",\n"
        "      industry: \"Financial Services\"\n"
        "    }\n"
        "  },\n"
        "  ...\n"
        "]",
    )

    add_heading(doc, "12.5 Contoh response RemoteOK", level=2)
    add_code(
        doc,
        "GET https://remoteok.com/api\n"
        "[\n"
        "  { /* meta */ },\n"
        "  {\n"
        "    \"id\": \"123456\",\n"
        "    \"slug\": \"forward-deployed-engineer-cohere\",\n"
        "    \"position\": \"Forward Deployed Engineer Agentic Platform\",\n"
        "    \"company\": \"Cohere\",\n"
        "    \"location\": \"\",\n"
        "    \"tags\": [\"engineer\", \"python\", \"llm\"],\n"
        "    \"description\": \"<p>...</p>\",\n"
        "    \"salary_min\": 150000, \"salary_max\": 200000,   // USD per year\n"
        "    \"apply_url\": \"https://remoteok.com/l/123456\"\n"
        "  }, ...\n"
        "]",
    )

    add_heading(doc, "12.6 Contoh response arbeitnow", level=2)
    add_code(
        doc,
        "GET https://www.arbeitnow.com/api/job-board-api?page=1\n"
        "{\n"
        "  \"data\": [\n"
        "    {\n"
        "      \"slug\": \"tech-lead-android-core-product-speechify-12345\",\n"
        "      \"company_name\": \"Speechify\",\n"
        "      \"title\": \"Tech Lead, Android Core Product\",\n"
        "      \"description\": \"<p>...</p>\",\n"
        "      \"remote\": false,\n"
        "      \"location\": \"Munich, Bavaria, Germany\",\n"
        "      \"tags\": [\"android\", \"kotlin\"],\n"
        "      \"job_types\": [\"full-time\"],\n"
        "      \"created_at\": 1715000000,\n"
        "      \"url\": \"https://www.arbeitnow.com/view/...\"\n"
        "    }, ...\n"
        "  ],\n"
        "  \"meta\": { \"current_page\": 1, \"per_page\": 100, \"to\": 100 }\n"
        "}",
    )

    add_heading(doc, "12.7 Contoh response Jobicy", level=2)
    add_code(
        doc,
        "GET https://jobicy.com/api/v2/remote-jobs?count=100&industry=marketing\n"
        "{\n"
        "  \"jobCount\": 100,\n"
        "  \"jobs\": [\n"
        "    {\n"
        "      \"id\": 144044,\n"
        "      \"jobSlug\": \"144044-order-management-associate\",\n"
        "      \"jobTitle\": \"Order Management Associate\",\n"
        "      \"companyName\": \"EOS\",\n"
        "      \"jobIndustry\": [\"Admin & Virtual Assistant\"],\n"
        "      \"jobType\": [\"Full-Time\"],\n"
        "      \"jobGeo\": \"USA\",\n"
        "      \"jobLevel\": \"Midweight\",\n"
        "      \"jobDescription\": \"<p>...</p>\",\n"
        "      \"salaryMin\": 50000, \"salaryMax\": 75000,\n"
        "      \"salaryCurrency\": \"USD\", \"salaryPeriod\": \"yearly\",\n"
        "      \"url\": \"https://jobicy.com/jobs/...\"\n"
        "    }, ...\n"
        "  ]\n"
        "}",
    )

    add_heading(doc, "12.8 Contoh response Adzuna", level=2)
    add_code(
        doc,
        "GET https://api.adzuna.com/v1/api/jobs/id/search/1\n"
        "    ?app_id=YOUR_ID&app_key=YOUR_KEY&results_per_page=50&what=developer\n"
        "{\n"
        "  \"count\": 1234,\n"
        "  \"results\": [\n"
        "    {\n"
        "      \"id\": \"5078123456\",\n"
        "      \"title\": \"Backend Developer\",\n"
        "      \"company\": { \"display_name\": \"PT Tokopedia\" },\n"
        "      \"location\": {\n"
        "        \"display_name\": \"Jakarta Selatan\",\n"
        "        \"area\": [\"Indonesia\", \"DKI Jakarta\", \"Jakarta Selatan\"]\n"
        "      },\n"
        "      \"description\": \"...\",\n"
        "      \"category\": { \"label\": \"IT Jobs\" },\n"
        "      \"contract_type\": \"permanent\", \"contract_time\": \"full_time\",\n"
        "      \"salary_min\": 15000000, \"salary_max\": 25000000,\n"
        "      \"created\": \"2026-05-10T08:00:00Z\",\n"
        "      \"redirect_url\": \"https://www.adzuna.com/redirect/...\"\n"
        "    }, ...\n"
        "  ]\n"
        "}",
    )

    add_heading(doc, "12.9 Alur pipeline scraping & import", level=2)
    for s in (
        "1. Scraper Kalibrr menggunakan Playwright + Chrome CDP (port 29229) karena Kalibrr di-proteksi Cloudflare. Setiap URL kategori di-load, __NEXT_DATA__ di-ekstrak dengan document.querySelector, dan field di-pluck.",
        "2. Scraper RemoteOK / arbeitnow / Jobicy / WWR menggunakan urllib.request standar — lebih ringan, tanpa browser.",
        "3. Scraper Adzuna menggunakan urllib.request + dua env var (ADZUNA_APP_ID, ADZUNA_APP_KEY) dari kredensial gratis Adzuna Developer.",
        "4. Hasil setiap scraper disimpan sebagai snapshot JSON di scrapers/data/<source>_jobs.json.",
        "5. Importer (scrapers/import_kalibrr.py untuk Kalibrr, scrapers/import_external_jobs.py untuk sisanya) membaca JSON, melakukan dedup, dan INSERT ke tabel companies + jobs lewat helper backend.database.execute().",
        "6. Importer bersifat idempotent: aman dijalankan berulang tanpa duplikasi.",
    ):
        add_bullet(doc, s)

    add_heading(doc, "12.10 Cara menjalankan ulang scraping & import", level=2)
    add_code(
        doc,
        "# 1. Pastikan Chrome berjalan di port 29229 (hanya untuk Kalibrr)\n"
        "google-chrome --remote-debugging-port=29229 --user-data-dir=/tmp/cdp &\n\n"
        "# 2. Jalankan semua scraper (paralel boleh)\n"
        "python scrapers/kalibrr_scraper.py --max-jobs 300\n"
        "python scrapers/remoteok_scraper.py\n"
        "python scrapers/arbeitnow_scraper.py 16\n"
        "python scrapers/jobicy_scraper.py\n"
        "python scrapers/weworkremotely_scraper.py\n"
        "# Adzuna butuh API key gratis dari https://developer.adzuna.com/signup\n"
        "ADZUNA_APP_ID=xxx ADZUNA_APP_KEY=yyy python scrapers/adzuna_scraper.py\n\n"
        "# 3. Import ke SQLite (dedup otomatis)\n"
        "python scrapers/import_kalibrr.py\n"
        "python scrapers/import_external_jobs.py",
    )

    add_heading(doc, "12.11 Catatan legal & rate-limit", level=2)
    add_bullet(
        doc,
        "Semua sumber yang dipakai mengizinkan akses publik tanpa scraping ban di "
        "ToS-nya (RemoteOK API publik, arbeitnow API publik, Jobicy 'free public API', "
        "WWR RSS, Adzuna API key gratis). Untuk Kalibrr tidak ada API publik resmi, "
        "namun __NEXT_DATA__ disajikan ke browser apapun yang me-load halaman.",
    )
    add_bullet(
        doc,
        "Rate limit diatur konservatif: 1.5-2 detik per URL untuk Kalibrr "
        "(rate-limited Playwright), 0.4 detik antar request untuk REST API.",
    )
    add_bullet(
        doc,
        "Field 'Sumber: <URL>' selalu ditambahkan ke kolom requirements supaya "
        "kandidat dapat melamar langsung ke halaman job-board asli.",
    )
    add_bullet(
        doc,
        "Daftar LinkedIn, Indeed, Glints, JobStreet, dan Kaggle TIDAK dipakai: "
        "LinkedIn/Indeed/Glints/JobStreet diblok oleh Cloudflare anti-bot dari "
        "cloud IP umum, sedangkan Kaggle bukan job board (platform kompetisi data science).",
    )

    add_para(doc, "Selamat menggunakan RUMAH KARIR!")

    doc.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
