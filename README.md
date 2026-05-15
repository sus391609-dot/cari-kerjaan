# RUMAH KARIR

Platform pencarian kerja berbasis **Flask + SQLite + HTML/CSS/JS + sedikit React**. Tema visual: abu-abu, hitam, dan putih. Responsif untuk desktop, tablet, dan mobile.

## Fitur Utama

- **Halaman utama** dengan search engine (kata kunci, negara, provinsi, kota), top 10 perusahaan dengan lowongan terbanyak, perusahaan paling banyak dicari, peta Indonesia interaktif, statistik komunitas, daftar mitra "Kerja Sama dengan Kami", dan pengalaman pengguna.
- **Detail lowongan** dengan toggle "Lihat Selengkapnya" — detail penuh hanya tersedia setelah login.
- **Autentikasi**: register sebagai user (nama, tanggal lahir, foto profil, email, password) atau perusahaan (data perusahaan lengkap). OTP 6 digit dikirim ke Gmail via SMTP. Login terpisah untuk admin (`admin@admin.com` / `admin123`).
- **Upload CV PDF**: sistem mem-parsing skill, umur, dan pengalaman dari CV lalu mencocokkan dengan lowongan yang sedang dibuka. Jika tidak ada yang cocok, sistem memberi saran skill yang perlu ditingkatkan.
- **Dashboard admin** dengan sidebar: CRUD perusahaan dan lowongan (tombol Search + New), Manage User (edit username/tanggal lahir/password, hapus), Approval pendaftaran perusahaan, Mode Maintenance (semua halaman terkunci kecuali admin), unggah gambar mitra "Kerja Sama", dan moderasi pengalaman user.
- **Dashboard perusahaan**: setelah disetujui admin, perusahaan dapat memasang lowongan baru dari halaman `/company`.
- **Bagikan pengalaman**: user terdaftar dapat menulis pengalaman yang akan tampil di halaman utama.
- **REST API**: seluruh interaksi data lewat endpoint `/api/...` (JSON).

## Stack

- Python 3.10+, Flask 3
- SQLite (modul stdlib `sqlite3`)
- pypdf (parsing CV PDF)
- python-docx (dokumentasi)
- SMTP (stdlib `smtplib`) untuk OTP
- React 18 via CDN + Babel standalone (hanya komponen search engine)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # isi SMTP_USER & SMTP_PASS (App Password Gmail)
python seed.py                    # mengisi 23 perusahaan + 69 lowongan demo
python app.py                     # http://127.0.0.1:5000
```

Akses dashboard admin: <http://127.0.0.1:5000/login> menggunakan kredensial default `admin@admin.com` / `admin123`.

### Konfigurasi SMTP (Gmail)

1. Aktifkan 2FA di akun Google Anda.
2. Buat **App Password** di <https://myaccount.google.com/apppasswords>.
3. Set `SMTP_USER` (alamat Gmail Anda) dan `SMTP_PASS` (App Password 16 karakter) di `.env`.

Tanpa konfigurasi SMTP, OTP tetap dibuat dan dicatat ke log aplikasi (mode dev).

## Dokumentasi

Dokumentasi lengkap (alur sistem, schema DB, query, daftar endpoint, struktur folder, library) tersedia dalam format `.docx`:

- `docs/RUMAH_KARIR_Dokumentasi.docx`

Untuk regenerasi:

```bash
python docs/generate_docs.py
```

## Struktur

```
app.py
config.py
seed.py
backend/
  database.py    # SQLite helpers
  auth.py        # Session, login_required, password hashing
  mailer.py      # SMTP / OTP
  cv_parser.py   # PDF parsing + matching algorithm
  middleware.py  # Maintenance mode
  routes/        # Blueprints: pages.py + api_*.py (RESTful)
static/          # css, js, img, uploads/
templates/       # Jinja templates: pages + admin/ + company/
docs/            # generate_docs.py + RUMAH_KARIR_Dokumentasi.docx
```

## Catatan

- Data perusahaan/lowongan pada seed dibuat manual menyerupai listing populer di [glints.com/id](https://glints.com/id) (Tokopedia, Gojek, Traveloka, Shopee, Bank Mandiri, Telkomsel, Ruangguru, dll). Tidak ada scraping live.
- Maintenance mode mengunci seluruh endpoint kecuali `/login`, `/logout`, dan endpoint admin auth.
- Pendaftaran perusahaan akan membuat baris `users(role='company', is_approved=0)` dan `companies(is_approved=0)`. Admin menyetujui melalui halaman **Approval Perusahaan**.
