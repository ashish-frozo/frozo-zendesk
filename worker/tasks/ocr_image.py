"""
Celery worker task for image OCR and masking.

Process:
1. Download image from Zendesk
2. Run OCR (Tesseract primary, Cloud Vision fallback)
3. Detect PII in OCR text
4. Map entities to bounding boxes
5. Apply masking (blur or solid block)
6. Upload sanitized image to S3
7. Update RunAsset status
"""

import logging
from typing import List, Dict, Tuple
import io
from PIL import Image, ImageFilter, ImageDraw
import pytesseract
from worker.celery_app import celery_app
from api.db.database import SessionLocal
from api.db.models import RunAsset, AssetStatus, Run
from api.services.redaction import create_detector
from api.config import settings

logger = logging.getLogger(__name__)


def ocr_with_tesseract(image: Image.Image) -> List[Dict]:
    """
    Run OCR using Tesseract and get bounding boxes.
    
    Returns:
        List of dicts with: text, left, top, width, height, conf
    """
    try:
        # Get detailed OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        # Filter out empty text and low confidence
        results = []
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            if text and conf > 30:  # Confidence threshold
                results.append({
                    'text': text,
                    'left': ocr_data['left'][i],
                    'top': ocr_data['top'][i],
                    'width': ocr_data['width'][i],
                    'height': ocr_data['height'][i],
                    'conf': conf
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
        raise


def ocr_with_cloud_vision(image_bytes: bytes) -> List[Dict]:
    """
    Run OCR using Google Cloud Vision API (fallback).
    
    Returns:
        List of dicts with: text, vertices (bounding polygon)
    """
    try:
        from google.cloud import vision
        
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        
        response = client.text_detection(image=image)
        texts = response.text_annotations
        
        if not texts:
            return []
        
        results = []
        # Skip first annotation (full text), process word-level annotations
        for text in texts[1:]:
            vertices = text.bounding_poly.vertices
            
            # Convert vertices to left, top, width, height
            xs = [v.x for v in vertices]
            ys = [v.y for v in vertices]
            
            results.append({
                'text': text.description,
                'left': min(xs),
                'top': min(ys),
                'width': max(xs) - min(xs),
                'height': max(ys) - min(ys),
                'conf': 100  # Cloud Vision doesn't provide confidence per word
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Cloud Vision OCR failed: {e}")
        raise


def apply_blur_mask(image: Image.Image, boxes: List[Tuple[int, int, int, int]], blur_radius: int = 15) -> Image.Image:
    """
    Apply blur masking to specified regions.
    
    Args:
        image: PIL Image
        boxes: List of (left, top, right, bottom) tuples
        blur_radius: Blur intensity
        
    Returns:
        Masked image
    """
    img_copy = image.copy()
    
    for box in boxes:
        left, top, right, bottom = box
        
        # Extract region
        region = img_copy.crop(box)
        
        # Apply blur
        blurred = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Paste back
        img_copy.paste(blurred, box)
    
    return img_copy


def apply_solid_mask(image: Image.Image, boxes: List[Tuple[int, int, int, int]], color: str = 'black') -> Image.Image:
    """
    Apply solid block masking to specified regions.
    
    Args:
        image: PIL Image
        boxes: List of (left, top, right, bottom) tuples
        color: Fill color
        
    Returns:
        Masked image
    """
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    for box in boxes:
        draw.rectangle(box, fill=color)
    
    return img_copy


@celery_app.task(bind=True, name='worker.tasks.ocr_image.process_image')
def process_image(self, asset_id: int, image_url: str, masking_style: str = 'blur'):
    """
    Celery task to process image: OCR, detect PII, mask, upload.
    
    Args:
        asset_id: RunAsset ID
        image_url: URL to download image from Zendesk
        masking_style: 'blur' or 'solid'
    """
    db = SessionLocal()
    
    try:
        # Get asset
        asset = db.query(RunAsset).filter(RunAsset.id == asset_id).first()
        if not asset:
            raise Exception(f"Asset {asset_id} not found")
        
        # Update status
        asset.status = AssetStatus.PROCESSING
        db.commit()
        
        # Download image
        import requests
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        image_bytes = response.content
        
        # Open image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        logger.info(f"Processing image {asset.filename}: {image.size}")
        
        # Run OCR (try Tesseract first, fallback to Cloud Vision)
        ocr_results = None
        ocr_method = 'tesseract'
        
        try:
            ocr_results = ocr_with_tesseract(image)
            logger.info(f"Tesseract OCR: {len(ocr_results)} text regions found")
        except Exception as e:
            logger.warning(f"Tesseract failed, trying Cloud Vision: {e}")
            try:
                ocr_results = ocr_with_cloud_vision(image_bytes)
                ocr_method = 'cloud_vision'
                logger.info(f"Cloud Vision OCR: {len(ocr_results)} text regions found")
            except Exception as e2:
                logger.error(f"Both OCR methods failed: {e2}")
                asset.status = AssetStatus.FAILED
                asset.meta_json = {"error": "OCR failed", "details": str(e2)}
                db.commit()
                return
        
        # Combine OCR text for PII detection
        ocr_text = " ".join([r['text'] for r in ocr_results])
        
        # Detect PII
        detector = create_detector()
        pii_results = detector.analyze(ocr_text)
        
        logger.info(f"Detected {len(pii_results)} PII entities in OCR text")
        
        # Map PII to bounding boxes
        boxes_to_mask = []
        
        for pii in pii_results:
            pii_text = ocr_text[pii.start:pii.end]
            
            # Find matching OCR boxes
            for ocr_box in ocr_results:
                if pii_text.lower() in ocr_box['text'].lower():
                    # Add bounding box with padding
                    padding = 5
                    box = (
                        max(0, ocr_box['left'] - padding),
                        max(0, ocr_box['top'] - padding),
                        min(image.width, ocr_box['left'] + ocr_box['width'] + padding),
                        min(image.height, ocr_box['top'] + ocr_box['height'] + padding)
                    )
                    boxes_to_mask.append(box)
        
        logger.info(f"Masking {len(boxes_to_mask)} regions")
        
        # Apply masking
        if masking_style == 'blur':
            masked_image = apply_blur_mask(image, boxes_to_mask)
        else:
            masked_image = apply_solid_mask(image, boxes_to_mask)
        
        # Save to bytes
        output_buffer = io.BytesIO()
        masked_image.save(output_buffer, format='PNG')
        output_bytes = output_buffer.getvalue()
        
        # Upload to S3
        from api.services.storage import upload_to_s3
        
        s3_key = f"sanitized/{asset.run_id}/{asset.filename}"
        storage_url = upload_to_s3(s3_key, output_bytes, 'image/png')
        
        # Update asset
        asset.status = AssetStatus.COMPLETED
        asset.storage_ref = s3_key
        asset.meta_json = {
            "ocr_method": ocr_method,
            "ocr_text_length": len(ocr_text),
            "pii_count": len(pii_results),
            "masked_regions": len(boxes_to_mask),
            "masking_style": masking_style,
            "image_size": {"width": image.width, "height": image.height}
        }
        db.commit()
        
        logger.info(f"Image {asset.filename} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing image {asset_id}: {e}")
        asset.status = AssetStatus.FAILED
        asset.meta_json = {"error": str(e)}
        db.commit()
        raise
    
    finally:
        db.close()
