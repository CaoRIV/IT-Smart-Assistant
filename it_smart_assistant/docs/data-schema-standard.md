# Data Schema Standard

Tai lieu nay dinh nghia schema chuan cho du lieu dau vao va du lieu da chuan hoa cua `IT - Smart - UTC`.

Muc tieu:
- thong nhat cach chuan bi PDF, DOCX, Excel, FAQ, interaction log
- giup pipeline ingest, knowledge retrieval, analytics, va admin CMS dung cung mot hop dong du lieu
- dam bao truy xuat co nguon, co hieu luc, va co the filter theo nghiep vu

## 1. Nguyen tac chung

Moi nguon du lieu khi dua vao he thong phai co 4 lop:

1. `raw_source`
   - file goc hoac record goc
2. `source_metadata`
   - metadata van ban va nghiep vu
3. `normalized_records`
   - text chunks, table rows, faq entries, procedure templates
4. `published_records`
   - ban da review va duoc chatbot su dung

Quy tac bat buoc:
- moi tai lieu phai co `status`
- moi ban ghi phai co `source_id`
- moi record retrieval phai truy nguoc duoc ve tai lieu goc
- du lieu het hieu luc khong duoc dua vao runtime knowledge mac dinh
- interaction log phai an danh truoc khi dua vao he thong

## 2. Enum chuan

### 2.1. `status`
```json
["draft", "needs_review", "published", "archived", "expired", "replaced"]
```

### 2.2. `source_type`
```json
["pdf", "docx", "excel", "faq", "interaction_log", "form_template", "procedure_template"]
```

### 2.3. `trust_level`
```json
["official", "internal", "reviewed_faq", "reviewed_interaction", "experimental"]
```

### 2.4. `language`
```json
["vi", "en", "mixed"]
```

### 2.5. `source_kind` cho retrieval
```json
["document_chunk", "table_row", "faq_entry", "procedure_template", "form_template", "interaction_pattern"]
```

## 3. Common Source Metadata

Tat ca nguon du lieu deu phai map duoc ve schema metadata chung nay.

```json
{
  "source_id": "string",
  "source_type": "pdf",
  "title": "Quy che dao tao dai hoc 2025",
  "category": "hoc_vu",
  "subcategory": "quy_che",
  "source_office": "Phong Dao tao",
  "issued_date": "2025-01-10",
  "effective_date": "2025-02-01",
  "expiry_date": null,
  "version": "v2",
  "status": "published",
  "trust_level": "official",
  "language": "vi",
  "source_url": "https://...",
  "file_name": "quy_che_dao_tao_2025_v2.pdf",
  "storage_path": "knowledge_raw/hoc-vu/quy_che_dao_tao_2025_v2.pdf",
  "checksum_sha256": "string",
  "notes": "Ban dang ap dung"
}
```

### Truong bat buoc
- `source_id`
- `source_type`
- `title`
- `category`
- `source_office`
- `status`
- `trust_level`
- `language`

## 4. PDF / DOCX Input Schema

PDF va DOCX sau extract phai dua ve 1 schema trung gian chung.

```json
{
  "source_id": "pdf_001",
  "source_type": "pdf",
  "metadata": { "...": "Common Source Metadata" },
  "extraction": {
    "is_scanned": false,
    "ocr_used": false,
    "page_count": 24,
    "extractor": "pymupdf",
    "extracted_at": "2026-03-20T10:00:00Z",
    "quality_score": 0.94
  },
  "sections": [
    {
      "section_id": "pdf_001_sec_001",
      "heading": "Dieu 1. Pham vi ap dung",
      "level": 1,
      "page_from": 1,
      "page_to": 2,
      "text": "..."
    }
  ],
  "tables": [
    {
      "table_id": "pdf_001_tbl_001",
      "title": "Muc thu hoc phi hoc ky I",
      "page_from": 5,
      "page_to": 5,
      "headers": ["he_dao_tao", "khoi_nganh", "hoc_phi_tin_chi"],
      "rows": [
        ["dai_hoc", "V", "512062"]
      ]
    }
  ]
}
```

### Rule chunking
- chunk theo `heading`, `dieu`, `muc`, `khoan`, `quy trinh`
- khong chunk mu theo so ky tu neu tai lieu co heading
- moi chunk phai co `page_from`, `page_to`

## 5. Excel Input Schema

Excel khong duoc coi la text document. Moi sheet phai duoc chuan hoa thanh dataset co cau truc.

```json
{
  "source_id": "xlsx_001",
  "source_type": "excel",
  "metadata": { "...": "Common Source Metadata" },
  "workbook": {
    "sheet_count": 3,
    "parsed_at": "2026-03-20T10:00:00Z"
  },
  "sheets": [
    {
      "sheet_id": "xlsx_001_sheet_01",
      "sheet_name": "HocPhi",
      "schema_type": "tuition_table",
      "headers": [
        "education_level",
        "program_type",
        "major_group",
        "fee_per_credit",
        "academic_year",
        "semester",
        "notes"
      ],
      "rows": [
        {
          "education_level": "dai_hoc",
          "program_type": "chinh_quy",
          "major_group": "V",
          "fee_per_credit": 512062,
          "academic_year": "2025-2026",
          "semester": "HK1",
          "notes": ""
        }
      ]
    }
  ]
}
```

### Rule cho Excel
- moi sheet phai co `schema_type`
- neu la bang lookup, phai map thanh object rows, khong de dang cell text roi
- merged cells phai duoc xu ly truoc khi index

## 6. FAQ Schema

FAQ phai la record rieng, khong tron vao raw text chunk.

```json
{
  "faq_id": "faq_001",
  "question": "Sinh vien co the xin bao luu hoc tap trong truong hop nao?",
  "answer": "Sinh vien co the xin bao luu khi co ly do hop le va nop ho so dung thoi han theo quy dinh.",
  "category": "hoc_vu",
  "subcategory": "bao_luu",
  "keywords": ["bao luu", "tam ngung hoc", "thu tuc bao luu"],
  "status": "published",
  "trust_level": "reviewed_faq",
  "language": "vi",
  "source_id": "pdf_001",
  "source_url": "https://...",
  "last_reviewed_at": "2026-03-20T10:00:00Z",
  "reviewed_by": "admin@utc.edu.vn"
}
```

### Rule cho FAQ
- `question` phai la cau hoi that
- `answer` ngan gon, 1 y chinh
- neu tra loi dua tren van ban chinh thuc, phai co `source_id` hoac `source_url`

## 7. Interaction Log Schema

Interaction log chi duoc dua vao he thong sau khi da an danh.

```json
{
  "interaction_id": "int_001",
  "source_type": "interaction_log",
  "channel": "student_support",
  "occurred_at": "2026-03-18T09:30:00Z",
  "user_question_raw": "Em xin hoi thu tuc bao luu la nhu the nao?",
  "user_question_clean": "Thu tuc bao luu hoc tap nhu the nao?",
  "resolved_answer_clean": "Can nop don bao luu va tai lieu chung minh ly do theo huong dan cua phong dao tao.",
  "intent": "procedure_workflow",
  "category": "hoc_vu",
  "subcategory": "bao_luu",
  "quality_label": "resolved",
  "contains_private_data": false,
  "review_status": "published",
  "reviewed_by": "admin@utc.edu.vn",
  "notes": "Da loai bo ten va ma sinh vien"
}
```

### Rule cho interaction log
- khong luu:
  - ho ten
  - ma sinh vien
  - email
  - so dien thoai
  - thong tin suc khoe / tai chinh ca nhan
- chi giu:
  - mau cau hoi
  - mau cau tra loi
  - intent
  - category

## 8. Procedure Template Schema

Dung cho `procedure workflow`.

```json
{
  "procedure_id": "bao_luu_hoc_tap",
  "title": "Thu tuc bao luu hoc tap",
  "category": "hoc_vu",
  "keywords": ["bao luu", "tam ngung hoc", "nghi hoc tam thoi"],
  "eligibility": [
    "Sinh vien co nhu cau tam ngung hoc theo quy dinh"
  ],
  "required_documents": [
    "Don xin bao luu hoc tap",
    "Tai lieu chung minh ly do neu co"
  ],
  "steps": [
    "Kiem tra dieu kien va thoi han nop ho so",
    "Dien don",
    "Nop ho so cho phong dao tao",
    "Theo doi ket qua phe duyet"
  ],
  "contact_office": "Phong Dao tao",
  "related_form_id": "form_001",
  "source_ids": ["pdf_001", "faq_014"],
  "status": "published",
  "trust_level": "official"
}
```

## 9. Form Template Schema

Dung cho `form orchestration` va `print/export`.

```json
{
  "form_id": "form_001",
  "title": "Don xin bao luu hoc tap",
  "category": "hoc_vu",
  "description": "Bieu mau danh cho sinh vien xin bao luu theo hoc ky hoac nam hoc",
  "keywords": ["bao luu", "don bao luu", "tam ngung hoc"],
  "status": "published",
  "fields": [
    {
      "name": "full_name",
      "label": "Ho va ten",
      "type": "text",
      "required": true,
      "placeholder": "Nhap ho va ten"
    }
  ],
  "print_template_type": "administrative_letter",
  "related_procedure_id": "bao_luu_hoc_tap",
  "source_ids": ["pdf_001"]
}
```

## 10. Normalized Retrieval Record Schema

Tat ca nguon du lieu sau ingest phai do ve 1 trong cac record retrieval sau.

### 10.1. `document_chunk`
```json
{
  "entry_id": "chunk_001",
  "source_kind": "document_chunk",
  "source_id": "pdf_001",
  "title": "Quy che dao tao 2025",
  "category": "hoc_vu",
  "section_title": "Dieu 5. Bao luu hoc tap",
  "content": "Sinh vien duoc xem xet bao luu khi...",
  "page_from": 8,
  "page_to": 9,
  "keywords": ["bao luu", "hoc vu"],
  "status": "published",
  "trust_level": "official"
}
```

### 10.2. `table_row`
```json
{
  "entry_id": "table_row_001",
  "source_kind": "table_row",
  "source_id": "xlsx_001",
  "title": "Hoc phi nam hoc 2025-2026",
  "category": "hoc_phi",
  "table_title": "Bang hoc phi HK1",
  "row_data": {
    "education_level": "dai_hoc",
    "program_type": "chinh_quy",
    "major_group": "V",
    "fee_per_credit": 512062
  },
  "search_text": "hoc phi dai hoc chinh quy khoi nganh V 512062",
  "status": "published",
  "trust_level": "official"
}
```

### 10.3. `faq_entry`
```json
{
  "entry_id": "faq_entry_001",
  "source_kind": "faq_entry",
  "source_id": "faq_001",
  "title": "FAQ Bao luu hoc tap",
  "category": "hoc_vu",
  "content": "Sinh vien co the xin bao luu khi...",
  "question": "Sinh vien co the xin bao luu hoc tap trong truong hop nao?",
  "status": "published",
  "trust_level": "reviewed_faq"
}
```

### 10.4. `interaction_pattern`
```json
{
  "entry_id": "interaction_001",
  "source_kind": "interaction_pattern",
  "source_id": "int_001",
  "title": "Mau hoi dap ve bao luu",
  "category": "hoc_vu",
  "intent": "procedure_workflow",
  "content": "Thu tuc bao luu hoc tap nhu the nao? Can nop don va tai lieu chung minh ly do...",
  "status": "published",
  "trust_level": "reviewed_interaction"
}
```

## 11. Validation Rules bat buoc

### Cho moi source
- `source_id` duy nhat
- `status` hop le
- `title` khong rong
- `category` khong rong

### Cho document chunk
- `content` toi thieu 50 ky tu, tru chunk dac biet
- phai co `page_from` neu source la PDF

### Cho table row
- `row_data` phai la object
- phai co `search_text`

### Cho FAQ
- `question` va `answer` khong rong

### Cho interaction
- `contains_private_data` phai la `false` moi duoc publish

## 12. Mapping category de xuat

```json
[
  "hoc_vu",
  "hoc_phi",
  "hoc_bong",
  "cong_tac_sinh_vien",
  "bieu_mau",
  "thuc_tap",
  "quy_che",
  "dao_tao",
  "hanh_chinh"
]
```

## 13. Thu muc de xuat

```text
knowledge_raw/
  pdf/
  docx/
  excel/
  faq/
  interactions/

knowledge_staging/
  extracted/
  normalized/
  validation_reports/

knowledge_processed/
  chunks/
  tables/
  faqs/
  interactions/
```

## 14. Thu tu ingest de xuat

1. raw file / raw record
2. gan `Common Source Metadata`
3. extract
4. normalize
5. validate
6. preview
7. publish
8. embed / index

## 15. Uu tien trien khai

Neu lam theo thu tu thuc dung:

1. `PDF/DOCX + Common Source Metadata`
2. `Excel table schema`
3. `FAQ schema`
4. `Procedure Template schema`
5. `Interaction Log schema`

## 16. Muc tieu su dung schema nay

Schema nay duoc dung cho:
- pipeline ingest
- knowledge admin CMS
- retrieval
- procedure workflow
- form orchestration
- analytics

Khong dung schema nay, he thong van chay duoc o muc MVP.
Dung schema nay, he thong moi co the mo rong on dinh o muc production-lite.
