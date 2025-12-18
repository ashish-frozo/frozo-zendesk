"""
Celery worker task for PDF redaction.

Supports:
- Text-layer PDFs (PyMuPDF native redaction)
- Scanned PDFs (OCR + image masking)
"""

import logging
import io
import fitz  # PyMuPDF
from typing import List, Dict
from PIL Image
from worker.celery_app import celery_app
from api.db.database import SessionLocal
from api.db.models import RunAsset, AssetStatus
from api.services.redaction import create_detector
from api.config import settings

logger = logging.getLogger(__name__)


def redact_text_layer_pdf(pdf_bytes: bytes, pii_results: List) -> bytes:
    """
    Redact text-layer PDF using PyMuPDF.
    
    Args:
        pdf_bytes: PDF file content
        pii_results: PII detection results from Presidio
        
    Returns:
        Redacted PDF as bytes
    """
    # Open PDF
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    try:
        # Process each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Get text with positions
            text_instances = page.get_text("dict")
            
            # For each PII entity, find and redact
            for pii in pii_results:
                # Search for text on page
                text_to_redact = pii.text if hasattr(pii, 'text') else ""
                
                if text_to_redact:
                    # Find all occurrences
                    areas = page.search_for(text_to_redact)
                    
                    # Add redaction annotation for each occurrence
                    for area in areas:
                        # Add redaction with black fill
                        page.add_redact_annot(area, fill=(0, 0, 0))
            
            # Apply all redactions on this page
            page.apply_redactions()
        
        # Strip metadata
        pdf_document.set_metadata({})
        
        # Save to bytes
        output = io.BytesIO()
        pdf_document.save(output)
        pdf_document.close()
        
        return output.getvalue()
        
    except Exception as e:
        pdf_document.close()
        raise


def redact_scanned_pdf(pdf_bytes: bytes) -> bytes:
    """
    Redact scanned PDF by converting to images, masking, and rebuilding.
    
    Args:
        pdf_bytes: PDF file content
        
    Returns:
        Redacted PDF as bytes
    """
    from worker.tasks.ocr_image import ocr_with_tesseract, apply_blur_mask
    
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    try:
        # Create new PDF for output
        output_pdf = fitz.open()
        
        detector = create_detector()
        
        # Process each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Render page to image
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            # Convert to PIL Image
            from PIL import Image
            image = Image.open(io.BytesIO(img_bytes))
            
            # Run OCR
            ocr_results = ocr_with_tesseract(image)
            ocr_text = " ".join([r['text'] for r in ocr_results])
            
            # Detect PII
            pii_results = detector.analyze(ocr_text)
            
            # Map to bounding boxes
            boxes_to_mask = []
            for pii in pii_results:
                pii_text = ocr_text[pii.start:pii.end]
                
                for ocr_box in ocr_results:
                    if pii_text.lower() in ocr_box['text'].lower():
                        padding = 5
                        box = (
                            max(0, ocr_box['left'] - padding),
                            max(0, ocr_box['top'] - padding),
                            min(image.width, ocr_box['left'] + ocr_box['width'] + padding),
                            min(image.height, ocr_box['top'] + ocr_box['height'] + padding)
                        )
                        boxes_to_mask.append(box)
            
            # Apply masking
            masked_image = apply_blur_mask(image, boxes_to_mask)
            
            # Convert back to bytes
            img_buffer = io.BytesIO()
            masked_image.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            # Add as new page to output PDF
            img_pdf = fitz.open(stream=img_data, filetype="png")
            output_pdf.insert_pdf(img_pdf)
            img_pdf.close()
        
        # Save output
        output = io.BytesIO()
        output_pdf.save(output)
        output_pdf.close()
        pdf_document.close()
        
        return output.getvalue()
        
    except Exception as e:
        output_pdf.close()
        pdf_document.close()
        raise


def verify_pdf_redaction(pdf_bytes: bytes, original_pii_patterns: List[str]) -> bool:
    """
    Verify that PDF redaction was successful by checking for residual PII.
    
    Args:
        pdf_bytes: Redacted PDF content
        original_pii_patterns: List of PII patterns from original
        
    Returns:
        True if no PII patterns found, False otherwise
    """
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    try:
        # Extract all text from PDF
        full_text = ""
        for page in pdf_document:
            full_text += page.get_text()
        
        # Check for residual patterns
        for pattern in original_pii_patterns:
            if pattern.lower() in full_text.lower():
                logger.warning(f"Found residual PII pattern: {pattern[:20]}...")
                return False
        
        return True
        
    finally:
        pdf_document.close()


@celery_app.task(bind=True, name='worker.tasks.redact_pdf.process_pdf')
def process_pdf(self, asset_id: int, pdf_url: str, max_pages: int = 10, max_size_mb: int = 10):
    """
    Celery task to process PDF: detect if text-layer or scanned, redact, verify.
    
    Args:
        asset_id: RunAsset ID
        pdf_url: URL to download PDF from Zendesk
        max_pages: Maximum pages allowed
        max_size_mb: Maximum file size in MB
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
        
        # Download PDF
        import requests
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        pdf_bytes = response.content
        
        # Check size
        size_mb = len(pdf_bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            raise Exception(f"PDF too large: {size_mb:.2f}MB > {max_size_mb}MB")
        
        # Open PDF
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(pdf_document)
        
        # Check page count
        if page_count > max_pages:
            raise Exception(f"PDF has too many pages: {page_count} > {max_pages}")
        
        logger.info(f"Processing PDF {asset.filename}: {page_count} pages, {size_mb:.2f}MB")
        
        # Detect if text-layer or scanned
        text_content = ""
        for page in pdf_document:
            text_content += page.get_text()
        
        is_text_layer = len(text_content.strip()) > 100  # Heuristic
        pdf_document.close()
        
        # Detect PII in text
        detector = create_detector()
        pii_results = detector.analyze(text_content)
        
        logger.info(f"PDF type: {'text-layer' if is_text_layer else 'scanned'}, PII count: {len(pii_results)}")
        
        # Redact based on type
        if is_text_layer:
            redacted_pdf = redact_text_layer_pdf(pdf_bytes, pii_results)
            redaction_method = "pymupdf_native"
        else:
            redacted_pdf = redact_scanned_pdf(pdf_bytes)
            redaction_method = "ocr_image_rebuild"
        
        # Verify redaction
        pii_patterns = [text_content[pii.start:pii.end] for pii in pii_results]
        verification_passed = verify_pdf_redaction(redacted_pdf, pii_patterns)
        
        if not verification_passed:
            # Verification failed - block export
            asset.status = AssetStatus.BLOCKED
            asset.meta_json = {
                "error": "Redaction verification failed",
                "reason": "Residual PII detected in sanitized PDF"
            }
            db.commit()
            logger.error(f"PDF {asset.filename} redaction verification FAILED")
            return
        
        # Upload to S3
        from api.services.storage import upload_to_s3
        
        s3_key = f"sanitized/{asset.run_id}/{asset.filename}"
        storage_url = upload_to_s3(s3_key, redacted_pdf, 'application/pdf')
        
        # Update asset
        asset.status = AssetStatus.COMPLETED
        asset.storage_ref = s3_key
        asset.meta_json = {
            "page_count": page_count,
            "size_mb": size_mb,
            "is_text_layer": is_text_layer,
            "redaction_method": redaction_method,
            "pii_count": len(pii_results),
            "verification_passed": verification_passed
        }
        db.commit()
        
        logger.info(f"PDF {asset.filename} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing PDF {asset_id}: {e}")
        asset.status = AssetStatus.FAILED
        asset.meta_json = {"error": str(e)}
        db.commit()
        raise
    
    finally:
        db.close()
