import os
import shutil
import datetime
import boto3
from botocore.exceptions import NoCredentialsError

# Postavke
KRONOS_DATA_DIR = os.environ.get("KRONOS_DATA_DIR", "kronos/data")
BACKUP_LOCAL_PATH = "/tmp/kronos_backup.zip"
BUCKET_NAME = os.environ.get("BACKUP_BUCKET_NAME")
S3_ENDPOINT = os.environ.get("BACKUP_S3_ENDPOINT") # npr. https://<id>.r2.cloudflarestorage.com
S3_ACCESS_KEY = os.environ.get("BACKUP_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("BACKUP_SECRET_KEY")

def create_zip():
    print(f"📦 Pakiram bazu iz {KRONOS_DATA_DIR}...")
    shutil.make_archive(BACKUP_LOCAL_PATH.replace(".zip", ""), 'zip', KRONOS_DATA_DIR)
    return BACKUP_LOCAL_PATH

def upload_to_s3(file_path):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    object_name = f"kronos_backup_{timestamp}.zip"
    
    print(f"🚀 Šaljem {object_name} na S3...")
    s3_client = boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY
    )
    
    try:
        s3_client.upload_file(file_path, BUCKET_NAME, object_name)
        print("✅ Backup uspješno poslan!")
    except Exception as e:
        print(f"❌ Greška pri uploadu: {e}")

if __name__ == "__main__":
    if not all([BUCKET_NAME, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY]):
        print("⚠️ Backup nije konfiguriran (nedostaju ENV varijable).")
    else:
        zip_file = create_zip()
        upload_to_s3(zip_file)
        # Očisti lokalni tmp file
        if os.path.exists(zip_file):
            os.remove(zip_file)
