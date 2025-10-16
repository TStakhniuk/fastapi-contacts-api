import cloudinary
import cloudinary.uploader
from src.config.settings import settings

cloudinary.config(
    cloud_name=settings.cloudinary_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True
)

async def upload_avatar(file, public_id: str):
    result = cloudinary.uploader.upload(
        file,
        public_id=public_id,
        overwrite=True
    )
    return cloudinary.CloudinaryImage(public_id).build_url(
        width=250, height=250, crop="fill", version=result.get("version")
    )
