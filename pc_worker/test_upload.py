"""Test script to upload sample audio to Supabase Storage"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Supabase 클라이언트 생성
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
client = create_client(url, key)

# 파일 업로드
test_user_id = 'fac89c62-b933-4b8f-8e84-be00e825407f'
local_file = r'D:\Productions\meetingminutes\data\samplemeeting.m4a'
storage_path = f'users/{test_user_id}/meetings/test/samplemeeting.m4a'

print(f'Uploading: {local_file}')
print(f'To: {storage_path}')
print(f'File size: {os.path.getsize(local_file) / 1024 / 1024:.2f} MB')

with open(local_file, 'rb') as f:
    file_data = f.read()

result = client.storage.from_('recordings').upload(
    storage_path,
    file_data,
    file_options={'content-type': 'audio/m4a'}
)

print(f'Upload result: {result}')

# Signed URL 생성 (1시간 유효)
signed_url = client.storage.from_('recordings').create_signed_url(storage_path, 3600)
print(f'Signed URL: {signed_url}')
