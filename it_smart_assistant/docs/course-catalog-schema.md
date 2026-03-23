# Course Catalog Schema

Tai lieu nay dinh nghia schema chuan rieng cho nhom file Excel `course catalog`.

Muc tieu:
- truy van chinh xac cac file chuong trinh dao tao co nhieu sheet, nhieu hang, nhieu cot
- khong phu thuoc vao chunk text thong thuong
- cho phep mo rong sang cac file Excel hoc vu khac co cau truc tuong tu

Tai lieu nay bo sung cho:
- [data-schema-standard.md](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/docs/data-schema-standard.md)
- [knowledge-database-design.md](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/docs/knowledge-database-design.md)

## 1. Khi nao dung schema nay

Dung schema `course_catalog` khi file Excel co mot hoac nhieu sheet mo ta:
- danh sach hoc phan
- hoc ky / lo trinh dao tao
- tong so tin chi
- mon hoc tien quyet
- ngon ngu giang day
- so tiet LT / TH / THoc / BTL / TN

Khong dung schema nay cho:
- bang hoc phi
- lich hoc / lich thi
- danh ba phong ban
- checklist ho so

## 2. Nguyen tac thiet ke

1. Khong xem workbook nhu van ban thuan.
2. Chon mot sheet `canonical` de truy van chinh.
3. Moi dong hoc phan phai tro thanh mot `normalized course record`.
4. Cac sheet trinh bay, tong hop, ghi chu duoc ingest thanh metadata va aggregate records.
5. Truy van uu tien `structured filters`, vector search chi la lop phu.

## 3. Sheet role schema

Moi sheet trong workbook phai duoc gan `sheet_role`.

Enum de xuat:

```json
[
  "course_catalog_flat",
  "course_catalog_semester_layout",
  "course_catalog_summary",
  "course_catalog_glossary",
  "course_catalog_notes",
  "ignore"
]
```

Y nghia:
- `course_catalog_flat`
  - bang phang, moi dong la 1 hoc phan
  - day la nguon truy van uu tien
- `course_catalog_semester_layout`
  - bang trinh bay theo hoc ky, co merged cells
  - dung de doi chieu va sinh aggregate
- `course_catalog_summary`
  - tong so mon, tong so tin chi, thong tin tong quan
- `course_catalog_glossary`
  - chu giai cot viet tat nhu `LT`, `THoc`, `HP tien quyet`
- `course_catalog_notes`
  - ghi chu nguon, canh bao OCR, pham vi du lieu
- `ignore`
  - bo qua

## 4. Workbook metadata schema

Moi workbook `course_catalog` phai map ve metadata sau:

```json
{
  "source_id": "src-course-catalog-cntt-2026",
  "source_type": "excel",
  "schema_type": "course_catalog",
  "title": "Chuong trinh dao tao CNTT",
  "category": "chuong_trinh_dao_tao",
  "subcategory": "cong_nghe_thong_tin",
  "source_office": "Khoa Cong nghe thong tin",
  "trust_level": "official",
  "language": "vi",
  "status": "published",
  "academic_year": "2025-2026",
  "program_name": "Cong nghe thong tin",
  "program_code": "CNTT",
  "degree_levels": ["cu_nhan", "ky_su"],
  "source_url": null,
  "file_name": "Danh_sach_mon_hoc.xlsx",
  "storage_path": "knowledge_raw/chuong_trinh_dao_tao/Danh_sach_mon_hoc.xlsx",
  "notes": "Nguon Excel tong hop tu PDF scan, can doi chieu lai ban chinh thuc neu dung cho ho so."
}
```

Truong bat buoc:
- `source_id`
- `source_type`
- `schema_type`
- `title`
- `category`
- `source_office`
- `trust_level`
- `language`
- `status`
- `program_name`

## 5. Workbook config schema

Moi file Excel thuoc schema `course_catalog` nen co mot `sheet config`.

```json
{
  "schema_type": "course_catalog",
  "canonical_sheet": "Du_lieu",
  "sheets": [
    {
      "sheet_name": "Du_lieu",
      "sheet_role": "course_catalog_flat",
      "header_row": 1,
      "data_start_row": 2,
      "column_map": {
        "Chuong trinh": "program_track",
        "Hoc ky": "semester_label",
        "TT": "course_order",
        "Ten hoc phan": "course_name",
        "Ma hoc phan": "course_code",
        "So TC": "credits",
        "LT": "lecture_hours",
        "TL/BT": "discussion_hours",
        "TKMH": "course_design_hours",
        "BTL": "project_hours",
        "TN": "lab_hours",
        "TH": "practice_hours",
        "THoc": "self_study_hours",
        "HP tien quyet": "prerequisite_text",
        "NNGD": "teaching_language"
      }
    },
    {
      "sheet_name": "Tong_quan",
      "sheet_role": "course_catalog_summary"
    },
    {
      "sheet_name": "Cu_nhan",
      "sheet_role": "course_catalog_semester_layout"
    },
    {
      "sheet_name": "Ky_su",
      "sheet_role": "course_catalog_semester_layout"
    },
    {
      "sheet_name": "Ghi_chu",
      "sheet_role": "course_catalog_glossary"
    }
  ]
}
```

## 6. Normalized course record schema

Day la schema quan trong nhat. Moi dong hoc phan can duoc dua ve dang nay.

```json
{
  "course_record_id": "src-course-catalog-cntt-2026-du-lieu-row-0001",
  "source_id": "src-course-catalog-cntt-2026",
  "source_version_id": "uuid",
  "sheet_name": "Du_lieu",
  "row_number": 2,
  "program_track": "cu_nhan",
  "degree_level": "cu_nhan",
  "program_variant": "standard",
  "semester_number": 1,
  "semester_label": "Hoc ky 1",
  "course_order": 1,
  "course_name": "Triet hoc Mac-Le nin",
  "normalized_course_name": "triet hoc mac le nin",
  "course_name_aliases": ["triet hoc mac lenin"],
  "course_code": "PS0.001.3",
  "credits": 3,
  "lecture_hours": 30,
  "discussion_hours": 30,
  "course_design_hours": null,
  "project_hours": null,
  "lab_hours": null,
  "practice_hours": null,
  "self_study_hours": 90,
  "prerequisite_text": null,
  "prerequisite_codes": [],
  "teaching_language": "viet",
  "assessment_type": null,
  "group_name": null,
  "status": "published",
  "trust_level": "official",
  "search_text": "cu nhan hoc ky 1 triet hoc mac le nin PS0.001.3 3 tin chi viet",
  "raw_row_data": {
    "Chuong trinh": "Cu nhan",
    "Hoc ky": "Hoc ky 1",
    "TT": "1",
    "Ten hoc phan": "Triet hoc Mac-Le nin",
    "Ma hoc phan": "PS0.001.3",
    "So TC": "3",
    "LT": "30",
    "TL/BT": "30",
    "THoc": "90",
    "NNGD": "Viet"
  }
}
```

Truong bat buoc:
- `course_record_id`
- `source_id`
- `sheet_name`
- `row_number`
- `program_track`
- `semester_label`
- `course_name`
- `course_code`
- `credits`
- `search_text`
- `raw_row_data`

## 7. Canonical field definitions

### 7.1. Track va degree

`program_track`

```json
["cu_nhan", "ky_su", "tich_hop", "khac"]
```

`degree_level`

```json
["cu_nhan", "ky_su", "thac_si", "tien_si", "khac"]
```

### 7.2. Gio hoc va tin chi

Tat ca cac cot sau phai chuan hoa ve `integer | null`:
- `credits`
- `lecture_hours`
- `discussion_hours`
- `course_design_hours`
- `project_hours`
- `lab_hours`
- `practice_hours`
- `self_study_hours`

### 7.3. Ngon ngu giang day

`teaching_language`

```json
["viet", "anh", "song_ngu", "khac"]
```

### 7.4. Hoc phan tien quyet

Khong nen chi luu text. Nen co ca:
- `prerequisite_text`
- `prerequisite_codes`

Neu khong tach duoc ma mon, `prerequisite_codes = []`.

## 8. Aggregate schema

Ngoai row records, can sinh them aggregate records de tra loi cau tong hop nhanh va on dinh.

### 8.1. Semester aggregate

```json
{
  "aggregate_id": "src-course-catalog-cntt-2026-cu-nhan-hoc-ky-1",
  "source_id": "src-course-catalog-cntt-2026",
  "aggregate_type": "semester_summary",
  "program_track": "cu_nhan",
  "semester_number": 1,
  "semester_label": "Hoc ky 1",
  "course_count": 7,
  "total_credits": 17,
  "course_codes": ["PS0.001.3", "PE0.001.1", "BS0.001.2"],
  "status": "published"
}
```

### 8.2. Program aggregate

```json
{
  "aggregate_id": "src-course-catalog-cntt-2026-cu-nhan-total",
  "source_id": "src-course-catalog-cntt-2026",
  "aggregate_type": "program_summary",
  "program_track": "cu_nhan",
  "total_courses": 75,
  "total_credits": 141,
  "status": "published"
}
```

### 8.3. Glossary aggregate

```json
{
  "aggregate_id": "src-course-catalog-cntt-2026-glossary",
  "source_id": "src-course-catalog-cntt-2026",
  "aggregate_type": "glossary",
  "items": [
    {"key": "LT", "value": "Ly thuyet"},
    {"key": "THoc", "value": "Tu hoc"}
  ],
  "status": "published"
}
```

## 9. OCR correction / alias schema

File chuong trinh dao tao rat hay co loi OCR. Vi vay can co bang alias rieng.

```json
{
  "alias_id": "alias-dai-so-tuyen-tinh",
  "source_id": "src-course-catalog-cntt-2026",
  "alias_type": "ocr_correction",
  "original_text": "ai so tuyen tinh",
  "normalized_text": "dai so tuyen tinh",
  "target_field": "course_name",
  "status": "published"
}
```

Nen co 3 loai alias:
- `ocr_correction`
- `search_synonym`
- `abbreviation`

Vi du:
- `HP tien quyet` -> `hoc phan tien quyet`
- `NNGD` -> `ngon ngu giang day`

## 10. Query intent schema

He thong truy van cho `course_catalog` nen phan loai it nhat cac intent sau:

```json
[
  "course_lookup_by_name",
  "course_lookup_by_code",
  "semester_course_list",
  "program_summary",
  "prerequisite_lookup",
  "language_filter",
  "credit_lookup",
  "hour_breakdown_lookup",
  "glossary_lookup"
]
```

### 10.1. Query filter payload

```json
{
  "intent": "semester_course_list",
  "program_track": "cu_nhan",
  "semester_number": 2,
  "course_code": null,
  "course_name_query": null,
  "teaching_language": null,
  "prerequisite_code": null
}
```

## 11. Retrieval strategy

Thu tu truy van de xuat:

1. `exact filters`
   - `course_code`
   - `program_track`
   - `semester_number`
2. `normalized lexical match`
   - `normalized_course_name`
   - `course_name_aliases`
3. `aggregate lookup`
   - neu intent la tong hop
4. `vector search`
   - chi de ho tro cau hoi mo ho, khong phai lop dau tien

## 12. Mapping cho file Danh_sach_mon_hoc.xlsx

Workbook [Danh_sach_mon_hoc.xlsx](D:/Download/Danh_sach_mon_hoc.xlsx) co the map nhu sau:

### 12.1. `Tong_quan`
- `sheet_role = course_catalog_summary`
- dung de sinh:
  - tong so hoc phan
  - tong so tin chi cu nhan
  - tong so tin chi ky su
  - tong so tin chi tich hop

### 12.2. `Du_lieu`
- `sheet_role = course_catalog_flat`
- day la `canonical_sheet`
- moi dong la 1 hoc phan
- day la nguon truy van chinh

### 12.3. `Cu_nhan`
- `sheet_role = course_catalog_semester_layout`
- dung de:
  - doi chieu hoc ky
  - xac minh tong tin chi hoc ky
  - khong query truc tiep neu da co `Du_lieu`

### 12.4. `Ky_su`
- `sheet_role = course_catalog_semester_layout`
- dung tuong tu `Cu_nhan`

### 12.5. `Ghi_chu`
- `sheet_role = course_catalog_glossary`
- dung de sinh glossary va metadata canh bao OCR

## 13. Validation rules

Bat buoc:
- `canonical_sheet` phai ton tai
- moi `course_code` phai unique trong cung `program_track + semester_label` hoac co ly do lap
- `credits` phai la so nguyen khong am
- `semester_number` phai parse duoc tu `semester_label` neu co mau `Hoc ky N`
- merged rows nhu `Hoc ky 1`, `Cong hoc ky` khong duoc coi la course record

Canh bao:
- ten mon co ve la OCR loi
- `course_code` thieu
- `credits` thieu
- row chi co 1-2 cot co du lieu

## 14. Database mapping de xuat

Neu muon toi uu cho nhom file nay, nen bo sung bang rieng:

### 14.1. `knowledge_course_catalogs`

```text
id uuid pk
source_version_id uuid not null
catalog_id varchar(255) unique not null
program_name varchar(255) not null
program_code varchar(100) null
academic_year varchar(50) null
canonical_sheet varchar(255) not null
status varchar(50) not null
created_at timestamptz not null
updated_at timestamptz not null
```

### 14.2. `knowledge_courses`

```text
id uuid pk
catalog_pk_id uuid not null
course_record_id varchar(255) unique not null
sheet_name varchar(255) not null
row_number integer not null
program_track varchar(50) not null
degree_level varchar(50) null
semester_number integer null
semester_label varchar(100) not null
course_order integer null
course_name varchar(500) not null
normalized_course_name varchar(500) not null
course_code varchar(100) not null
credits integer not null
lecture_hours integer null
discussion_hours integer null
course_design_hours integer null
project_hours integer null
lab_hours integer null
practice_hours integer null
self_study_hours integer null
prerequisite_text text null
prerequisite_codes jsonb not null default '[]'
teaching_language varchar(50) null
search_text text not null
raw_row_data jsonb not null
status varchar(50) not null
created_at timestamptz not null
updated_at timestamptz not null
```

### 14.3. Index uu tien

- `(catalog_pk_id, program_track, semester_number)`
- `(catalog_pk_id, course_code)`
- `gin(normalized_course_name gin_trgm_ops)` neu dung trigram
- `gin(search_text)`

## 15. Cach ap dung cho cac file Excel khac

Schema nay khong chi dung cho 1 file.

Muons dung lai cho file Excel khac, can:
1. xac dinh `canonical sheet`
2. map `column_map`
3. khai bao `sheet_role`
4. dinh nghia normalization rules rieng neu co OCR
5. ingest thanh `course records + aggregate records`

Neu mot file moi van la bang hoc phan / chuong trinh dao tao, khong can doi schema; chi can doi config.

## 16. Khuyen nghi implementation

Thu tu implementation de xuat:

1. them `sheet_schema_config` cho `course_catalog`
2. ingest `Du_lieu` thanh `knowledge_courses`
3. ingest `Tong_quan` va `Ghi_chu` thanh aggregate records
4. them tool `search_course_catalog`
5. them answer formatter rieng cho:
   - tra cuu mon hoc
   - danh sach mon theo hoc ky
   - tong so tin chi
   - hoc phan tien quyet

Ket qua mong muon:
- cau hoi `IT1.103.3 la mon gi` tra dung exact
- cau hoi `hoc ky 2 cu nhan co nhung mon nao` tra dung list
- cau hoi `mon nao day bang tieng Anh` tra dung filter
- cau hoi `tong so tin chi cu nhan la bao nhieu` tra tu aggregate, khong can vector search
