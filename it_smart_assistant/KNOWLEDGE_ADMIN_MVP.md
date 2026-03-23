# Knowledge Admin MVP

## 1. Muc tieu

`Knowledge Admin MVP` la khu vuc quan tri toi thieu de admin co the:

- upload tai lieu PDF moi vao kho tri thuc
- them FAQ moi cho chatbot
- them template bieu mau moi
- rebuild kho tri thuc ma khong can sua tay code

MVP nay uu tien:

- dung duoc ngay
- de mo rong sau nay
- it rui ro, khong can migration database

Phien ban hien tai dung `filesystem-backed storage`, tuc la du lieu duoc luu trong thu muc cua du an.

---

## 2. Tinh nang da co

### 2.1. Documents

Admin co the:

- upload file PDF moi
- chon `category` cho tai lieu
- tu dong luu file vao `knowledge_raw/<category>`
- tu dong chay lai ingest de cap nhat `knowledge_processed`

### 2.2. FAQs

Admin co the:

- tao FAQ moi
- xoa FAQ
- FAQ moi duoc dua vao retrieval ngay sau khi tao

### 2.3. Forms

Admin co the:

- tao form template moi
- xoa form template
- form template moi duoc dua vao retrieval ngay sau khi tao

Luu y: hien tai `Forms` moi o muc quan ly knowledge va template. No chua duoc noi sau vao workflow `generate_form`.

### 2.4. Rebuild Knowledge

Admin co the bam nut `Rebuild Knowledge` de:

- chay lai pipeline ingest tu `knowledge_raw`
- cap nhat `knowledge_processed`
- clear cache retrieval

---

## 3. Vi tri hien thi tren giao dien

Menu `Knowledge Admin` duoc them vao thanh trai dashboard.

No chi hien voi user co role `admin`.

File lien quan:

- [sidebar.tsx](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/components/layout/sidebar.tsx)
- [knowledge-admin/page.tsx](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/[locale]/(dashboard)/knowledge-admin/page.tsx)

Route frontend:

- `/knowledge-admin`

---

## 4. Cau truc luu tru du lieu

### 4.1. Tai lieu PDF goc

```text
it_smart_assistant/
  knowledge_raw/
    hoc_phi/
    so_tay_sinh_vien/
    ...
```

File moi upload se duoc dua vao day.

### 4.2. Du lieu da xu ly

```text
it_smart_assistant/
  knowledge_processed/
    knowledge_manifest.csv
    documents/
    chunks/
    tables/
```

Trong do:

- `documents/`: metadata va full text tai lieu
- `chunks/`: chunk van ban de retrieval
- `tables/`: du lieu bang co cau truc, dac biet huu ich cho hoc phi

### 4.3. Du lieu admin

```text
it_smart_assistant/
  knowledge_admin/
    faqs/
    forms/
```

Trong do:

- `faqs/`: moi FAQ la 1 file JSON
- `forms/`: moi form template la 1 file JSON

---

## 5. Kien truc backend

### 5.1. API admin

Route backend:

- [knowledge_admin.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/api/routes/v1/knowledge_admin.py)

Da co cac API:

- `GET /api/v1/knowledge-admin/documents`
- `POST /api/v1/knowledge-admin/documents/upload`
- `POST /api/v1/knowledge-admin/documents/rebuild`
- `GET /api/v1/knowledge-admin/faqs`
- `POST /api/v1/knowledge-admin/faqs`
- `DELETE /api/v1/knowledge-admin/faqs/{faq_id}`
- `GET /api/v1/knowledge-admin/forms`
- `POST /api/v1/knowledge-admin/forms`
- `DELETE /api/v1/knowledge-admin/forms/{form_id}`

Tat ca cac route nay deu yeu cau role `admin`.

### 5.2. Storage layer

File quan ly luu tru:

- [admin_store.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/admin_store.py)

No phu trach:

- luu file PDF upload
- luu FAQ JSON
- luu Form JSON
- goi rebuild knowledge
- clear cache retrieval

### 5.3. Retrieval layer

File retrieval:

- [service.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/service.py)

Hien tai retrieval doc tu 4 nguon:

- `backend/app/knowledge/documents/*.json`
- `knowledge_processed/chunks/*.json`
- `knowledge_processed/tables/*.json`
- `knowledge_admin/faqs/*.json`
- `knowledge_admin/forms/*.json`

Loai source hien co:

- `document`
- `chunk`
- `table_row`
- `faq`
- `form_template`

---

## 6. Kien truc frontend

### 6.1. Trang admin

Trang chinh:

- [knowledge-admin/page.tsx](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/[locale]/(dashboard)/knowledge-admin/page.tsx)

Trang nay gom 3 khu:

- `Documents`
- `FAQs`
- `Forms`

### 6.2. Next.js proxy routes

Frontend khong goi truc tiep backend tu browser, ma di qua Next API route.

Da them:

- [documents/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/documents/route.ts)
- [documents/rebuild/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/documents/rebuild/route.ts)
- [documents/upload/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/documents/upload/route.ts)
- [faqs/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/faqs/route.ts)
- [faqs/[id]/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/faqs/[id]/route.ts)
- [forms/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/forms/route.ts)
- [forms/[id]/route.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/api/knowledge-admin/forms/[id]/route.ts)

---

## 7. Bai toan bang bieu da duoc xu ly nhu the nao

Tai lieu hoc phi thuong co rat nhieu bang.

Neu chi chunk text thong thuong thi chatbot se:

- doc duoc chu
- nhung khong hieu cau truc hang/cot

Vi vay pipeline ingest da duoc nang cap de sinh them:

- `knowledge_processed/tables/*.json`

File parser:

- [ingest.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/ingest.py)

Muc tieu:

- tach hang bang hoc phi thanh du lieu co cau truc
- dua tung hang bang vao retrieval duoi dang `table_row`

Vi vay cac truy van kieu:

- `hoc phi khoi nganh V la bao nhieu`
- `hoc phi cao hoc khoi nganh VII`
- `hoc phi chuong trinh tien tien khoi nganh III`

se co ket qua tot hon truoc.

---

## 8. Cach su dung

### 8.1. Upload document

1. Dang nhap bang tai khoan `admin`
2. Mo menu `Knowledge Admin`
3. Vao khu `Documents`
4. Nhap `category`
5. Chon file PDF
6. Bam `Upload`

Ket qua:

- file duoc luu vao `knowledge_raw/<category>`
- pipeline ingest duoc chay lai
- retrieval duoc clear cache

### 8.2. Them FAQ

1. Mo khu `FAQs`
2. Nhap:
   - `title`
   - `category`
   - `question`
   - `answer`
   - `source_url` neu co
   - `keywords`
3. Bam `Them FAQ`

### 8.3. Them Form

1. Mo khu `Forms`
2. Nhap:
   - `title`
   - `category`
   - `description`
   - `source_url`
   - `keywords`
   - `fields`
3. Moi dong `fields` theo format:

```text
name|label|type|required|placeholder
```

Vi du:

```text
full_name|Ho va ten|text|true|Nhap ho va ten
student_id|Ma sinh vien|text|true|Nhap ma sinh vien
reason|Ly do|textarea|false|Nhap ly do
```

---

## 9. Cac file quan trong

### Backend

- [knowledge_admin.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/api/routes/v1/knowledge_admin.py)
- [admin_store.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/admin_store.py)
- [ingest.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/ingest.py)
- [service.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/service.py)
- [knowledge_admin.py](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/schemas/knowledge_admin.py)

### Frontend

- [knowledge-admin/page.tsx](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/app/[locale]/(dashboard)/knowledge-admin/page.tsx)
- [sidebar.tsx](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/components/layout/sidebar.tsx)
- [knowledge-admin.ts](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/frontend/src/types/knowledge-admin.ts)

---

## 10. Gioi han hien tai

Day la MVP, nen hien tai con mot so gioi han:

- chua dung database cho admin knowledge
- chua co update/edit, moi chi co create/delete
- chua co preview chunk/table trong giao dien
- chua co publish/unpublish workflow
- `Forms` chua noi sau vao `generate_form`
- parser bang hoc phi da tot hon, nhung van co the con OCR noise o mot so tieu de

---

## 11. Huong nang cap tiep theo

Huong nang cap hop ly nhat:

1. them edit/update cho FAQ va Form
2. them xoa/sua metadata cho Document
3. them preview processed chunk/table tren UI
4. them publish/unpublish
5. chuyen knowledge admin tu filesystem sang database
6. noi `Forms` admin vao workflow `generate_form`
7. them semantic search / hybrid retrieval

---

## 12. Cach kiem tra nhanh

### Kiem tra frontend

```powershell
cd D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant\frontend
npm run type-check
```

### Kiem tra backend

```powershell
cd D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant\backend
uv run python -m compileall app cli tests
```

### Kiem tra runtime nhe

```powershell
cd D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant\backend
uv run python -c "from app.knowledge.admin_store import list_documents; print(len(list_documents()))"
```

---

## 13. Ghi chu quan trong

Neu admin upload tai lieu moi ma chatbot chua tra loi theo noi dung moi ngay, hay kiem tra:

- upload da thanh cong chua
- category dat dung chua
- `Rebuild Knowledge` da chay chua
- backend da restart neu can

Trong MVP hien tai, phan lon truong hop se khong can sua code, chi can:

- upload document
- them FAQ / Form
- rebuild knowledge

