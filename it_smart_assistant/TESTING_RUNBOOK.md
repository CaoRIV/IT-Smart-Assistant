# Testing Runbook

Tai lieu nay dung de chay du an moi khi can test local.

Tat ca lenh ben duoi duoc chay tu thu muc:

```powershell
D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant
```

## 1. Yeu cau can co

- Docker Desktop
- Python + `uv`
- Node.js + `npm`

## 2. Chuan bi lan dau

### 2.1. Backend

```powershell
make install
```

Cap nhat file [backend/.env](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/.env):

- `LLM_PROVIDER=openai` hoac 'google`
- `OPENAI_API_KEY=...` neu dung OpenAI
- `GOOGLE_API_KEY=...` neu dung Google
- `AI_MODEL=gpt-4o-mini` neu dung OpenAI

Luu y:

- `ChatGPT Plus` khong thay the cho `OpenAI API`
- Muon dung OpenAI qua code, ban can API key va billing tren `platform.openai.com`

### 2.2. Frontend

Neu chua co file `frontend/.env.local`, tao file moi voi noi dung:

```env
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

Sau do cai dependency frontend:

```powershell
cd frontend
npm install
cd ..
```

### 2.3. Database va Redis

Khoi dong PostgreSQL va Redis:

```powershell
make docker-db
make docker-redis
```

Chay migration:

```powershell
make db-upgrade
```

Neu can tai khoan admin:

```powershell
make create-admin
```

## 3. Quy trinh chay de test hang ngay

### Terminal 1: ha tang

```powershell
make docker-db
make docker-redis
```

### Terminal 2: backend

```powershell
make run
```

Backend se chay tai:

- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- Admin: `http://localhost:8000/admin`

### Terminal 3: frontend

```powershell
cd frontend
npm run dev
```

Frontend se chay tai:

- App: `http://localhost:3000`

## 4. Smoke test nhanh sau khi mo du an

### 4.1. Test backend song

Mo:

- `http://localhost:8000/docs`
- `http://localhost:8000/api/v1/health`

### 4.2. Test frontend song

Mo:

- `http://localhost:3000`

### 4.3. Test login va chat

1. Dang ky tai khoan moi hoac dang nhap
2. Vao `/chat`
3. Thu mot trong cac cau:
   - `Thu tuc bao luu hoc tap gom nhung gi?`
   - `Neu nop hoc phi tre thi sao?`
   - `Lam sao de xin giay xac nhan sinh vien?`
4. Kiem tra bot co tra loi bang tieng Viet va co phan `Nguon tham khao`

## 5. Lenh test nhanh cho developer

### Backend

```powershell
uv run --directory backend pytest tests -v
```

### Frontend type-check

```powershell
cd frontend
npm run type-check
```

### Frontend unit test

```powershell
cd frontend
npm run test:run
```

## 6. Khi sua du lieu tri thuc chatbot

Neu ban them hoac sua file trong:

- [backend/app/knowledge/documents](D:/ITSmartAssistant_AdministrativeAgent/IT-Smart-Assistant/it_smart_assistant/backend/app/knowledge/documents)

thi chi can:

1. luu file `.json`
2. restart backend
3. vao chat va test lai

Khong can migration database cho bo tri thuc dang o phien ban MVP hien tai.

## 7. Cac loi hay gap

### Loi khong chat duoc voi OpenAI

Kiem tra:

- `backend/.env` da co `OPENAI_API_KEY`
- `LLM_PROVIDER=openai`
- `AI_MODEL=gpt-4o-mini`
- API key la key cua `platform.openai.com`, khong phai ChatGPT Plus

### Loi backend khong len

Kiem tra:

- Docker Desktop da chay
- PostgreSQL da len o port `5432`
- Redis da len o port `6379`
- da chay `make db-upgrade`

### Loi frontend mo duoc nhung chat khong stream

Kiem tra file `frontend/.env.local`:

```env
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

Sau do restart frontend.

## 8. Rebuild knowledge tu PDF

Bo PDF goc vao:

```text
it_smart_assistant/knowledge_raw/
  hoc_phi/
  so_tay_sinh_vien/
```

Sau do chay:

```powershell
cd D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant\backend
uv run it_smart_assistant knowledge ingest `
  --raw-dir D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant\knowledge_raw `
  --output-dir D:\ITSmartAssistant_AdministrativeAgent\IT-Smart-Assistant\it_smart_assistant\knowledge_processed
```

He thong se sinh ra:

- `knowledge_processed/knowledge_manifest.csv`
- `knowledge_processed/documents/*.json`
- `knowledge_processed/chunks/*.json`

Sau khi ingest xong, restart backend de chatbot nap bo tri thuc moi.

## 9. Tat he thong sau khi test

### Dung frontend

Nhan `Ctrl + C` o terminal frontend.

### Dung backend

Nhan `Ctrl + C` o terminal backend.

### Dung PostgreSQL va Redis

```powershell
make docker-db-stop
make docker-redis-stop
```

Neu muon tat toan bo docker stack:

```powershell
make docker-down
```

## 10. Quy trinh ngan nhat

Neu da setup xong tu truoc, moi lan test chi can:

```powershell
make docker-db
make docker-redis
make run
```

va o terminal khac:

```powershell
cd frontend
npm run dev
```
