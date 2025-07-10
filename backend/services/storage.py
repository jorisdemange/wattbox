import os
import shutil
from datetime import datetime
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, 
                 upload_directory: str = "./static/uploads",
                 s3_bucket: Optional[str] = None,
                 aws_region: Optional[str] = None):
        self.upload_directory = upload_directory
        self.s3_bucket = s3_bucket
        self.s3_client = None
        
        if s3_bucket and aws_region:
            self.s3_client = boto3.client('s3', region_name=aws_region)
        
        # Ensure local directories exist
        for subdir in ['raw', 'processed', 'failed']:
            os.makedirs(os.path.join(upload_directory, subdir), exist_ok=True)
    
    def save_raw_image(self, file_content: bytes, filename: str, 
                      device_id: Optional[str] = None) -> str:
        """Save raw image and return relative path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if device_id:
            directory = f"raw/{device_id}"
        else:
            directory = "raw/manual"
        
        # Create filename with timestamp
        name, ext = os.path.splitext(filename)
        new_filename = f"{timestamp}_{name}{ext}"
        
        if self.s3_client and self.s3_bucket:
            # Save to S3
            s3_key = f"{directory}/{new_filename}"
            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=file_content
                )
                return s3_key
            except ClientError as e:
                logger.error(f"S3 upload failed: {str(e)}")
                raise
        else:
            # Save to local filesystem
            local_dir = os.path.join(self.upload_directory, directory)
            os.makedirs(local_dir, exist_ok=True)
            
            file_path = os.path.join(local_dir, new_filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Return relative path
            return f"{directory}/{new_filename}"
    
    def save_processed_image(self, original_path: str, processed_content: bytes) -> str:
        """Save processed image and return relative path"""
        # Extract filename from original path
        filename = os.path.basename(original_path)
        directory = "processed"
        
        if self.s3_client and self.s3_bucket:
            # Save to S3
            s3_key = f"{directory}/{filename}"
            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=processed_content
                )
                return s3_key
            except ClientError as e:
                logger.error(f"S3 upload failed: {str(e)}")
                raise
        else:
            # Save to local filesystem
            local_dir = os.path.join(self.upload_directory, directory)
            file_path = os.path.join(local_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(processed_content)
            
            return f"{directory}/{filename}"
    
    def move_to_failed(self, original_path: str) -> str:
        """Move image to failed directory"""
        filename = os.path.basename(original_path)
        
        if self.s3_client and self.s3_bucket:
            # Copy to failed directory in S3
            source_key = original_path
            dest_key = f"failed/{filename}"
            
            try:
                self.s3_client.copy_object(
                    Bucket=self.s3_bucket,
                    CopySource={'Bucket': self.s3_bucket, 'Key': source_key},
                    Key=dest_key
                )
                # Optionally delete the original
                # self.s3_client.delete_object(Bucket=self.s3_bucket, Key=source_key)
                return dest_key
            except ClientError as e:
                logger.error(f"S3 move failed: {str(e)}")
                raise
        else:
            # Move in local filesystem
            source_path = os.path.join(self.upload_directory, original_path)
            dest_path = os.path.join(self.upload_directory, "failed", filename)
            
            shutil.move(source_path, dest_path)
            return f"failed/{filename}"
    
    def get_image_url(self, path: str, expiration: int = 3600) -> str:
        """Get URL for accessing image"""
        if self.s3_client and self.s3_bucket:
            # Generate presigned URL for S3
            try:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.s3_bucket, 'Key': path},
                    ExpiresIn=expiration
                )
                return url
            except ClientError as e:
                logger.error(f"Failed to generate presigned URL: {str(e)}")
                raise
        else:
            # Return relative URL for local storage
            return f"/images/{path}"
    
    def get_full_path(self, relative_path: str) -> str:
        """Get full filesystem path for a relative path"""
        return os.path.join(self.upload_directory, relative_path)