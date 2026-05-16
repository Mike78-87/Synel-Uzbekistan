# test_esign.py
import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

BASE_URL = os.getenv("BASE_URL", "https://test-env-slim.synel-saas.com")

# ========== ABSOLUTE PATHS FOR TEST FILES ==========
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILES_DIR = os.path.join(SCRIPT_DIR, "test_files")
VALID_PDF = os.path.join(TEST_FILES_DIR, "valid.pdf")
INVALID_TXT = os.path.join(TEST_FILES_DIR, "invalid.txt")
LARGE_PDF = os.path.join(TEST_FILES_DIR, "large.pdf")

# ========== CREATE TEST FILES IF NOT EXIST ==========
os.makedirs(TEST_FILES_DIR, exist_ok=True)

# Create valid PDF using reportlab (must be installed)
if not os.path.exists(VALID_PDF):
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(VALID_PDF)
        c.drawString(100, 750, "Test PDF for E-Sign")
        c.save()
        print(f"Created {VALID_PDF} using reportlab")
    except ImportError:
        # If reportlab not installed, create an empty PDF with a basic header (ASCII only)
        with open(VALID_PDF, "wb") as f:
            f.write(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/MediaBox [0 0 612 792]\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Test) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000015 00000 n\n0000000074 00000 n\n0000000129 00000 n\n0000000235 00000 n\n0000000302 00000 n\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n389\n%%EOF\n")
        print(f"Created fallback ASCII PDF at {VALID_PDF}")

# Create invalid .txt file
if not os.path.exists(INVALID_TXT):
    with open(INVALID_TXT, "w") as f:
        f.write("This is not a PDF file.")
    print(f"Created {INVALID_TXT}")

# Optionally create large file (26 MB) – uncomment if needed
# if not os.path.exists(LARGE_PDF):
#     with open(LARGE_PDF, "wb") as f:
#         f.seek(26 * 1024 * 1024 - 1)
#         f.write(b'\0')
#     print(f"Created {LARGE_PDF}")

# ========== HELPER FUNCTIONS ==========
def wait_for_validation_error(driver, field_name, timeout=5):
    """Wait for a validation error message for a specific field (by data-valmsg-for)"""
    try:
        error_span = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, f"//span[@data-valmsg-for='{field_name}' and contains(@class, 'text-danger') and not(text()='')]"))
        )
        return error_span.text
    except TimeoutException:
        return None

def wait_for_success_message(driver, timeout=5):
    """Check if success message appears or page redirects after submission"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.url_changes(BASE_URL)
        )
        return "Redirected"
    except TimeoutException:
        try:
            success = driver.find_element(By.XPATH, "//*[contains(text(), 'Success') or contains(text(), 'sent') or contains(text(), 'signed')]")
            return success.text
        except:
            return None

# ========== TEST CASES ==========
def test_TC01_successful_submission(driver):
    """Positive: all valid data -> success or redirect"""
    driver.get(BASE_URL)

    driver.find_element(By.ID, "Description").send_keys("Test Contract")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    result = wait_for_success_message(driver)
    assert result is not None, "No success message or redirect after submission"

def test_TC02_missing_recipient(driver):
    """Recipient not selected -> error message"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    error = wait_for_validation_error(driver, "Recipient")
    if error is None:
        error = wait_for_validation_error(driver, "Description")
    assert error is not None, "No error when recipient missing"
    assert "select" in error.lower() or "recipient" in error.lower()

def test_TC03_missing_category(driver):
    """Category not selected -> optional or required? We'll check."""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    error = wait_for_validation_error(driver, "Category")
    if error is None:
        pytest.xfail("Category may be optional – confirm requirement")
    else:
        assert "category" in error.lower() or "select" in error.lower()

def test_TC04_empty_description(driver):
    """Description empty (field is required per data-val-required)"""
    driver.get(BASE_URL)
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    error = wait_for_validation_error(driver, "Description")
    assert error is not None, "No error when Description empty"
    assert "required" in error.lower() or "description" in error.lower()

def test_TC05_empty_email(driver):
    """Email field empty -> error (field is required)"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    error = wait_for_validation_error(driver, "SenderEmail")
    assert error is not None, "No error when email empty"
    assert "required" in error.lower() or "email" in error.lower()

def test_TC06_invalid_email_format(driver):
    """Email without @ and domain -> should be rejected (server-side ideally)"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("invalid_email")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    error = wait_for_validation_error(driver, "SenderEmail", timeout=3)
    if error is None:
        if driver.current_url == BASE_URL:
            pytest.fail("No client-side or server-side validation for invalid email format (bug)")
        else:
            pytest.fail("Form submitted with invalid email (bug)")
    else:
        assert "valid" in error.lower() or "email" in error.lower()

def test_TC07_no_file_selected(driver):
    """No file uploaded -> error (critical requirement)"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    if driver.current_url == BASE_URL:
        try:
            error = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-danger') and text()!='']"))
            )
            assert "file" in error.text.lower() or "document" in error.text.lower()
        except TimeoutException:
            pytest.fail("No error when no file selected (bug)")
    else:
        pytest.fail("Form submitted without file (bug)")

def test_TC08_non_pdf_file(driver):
    """Upload .txt file -> should be rejected"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(INVALID_TXT)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    if driver.current_url == BASE_URL:
        try:
            error = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-danger')]"))
            )
            assert "pdf" in error.text.lower() or "format" in error.text.lower()
        except TimeoutException:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert "pdf" in body_text.lower() or "format" in body_text.lower(), "Application accepted .txt file (bug)"
    else:
        pytest.fail("Application accepted .txt file and redirected (bug)")

def test_TC09_file_size_exceeds_25mb(driver):
    """File >25 MB -> error"""
    if not os.path.exists(LARGE_PDF):
        pytest.skip("large.pdf not found, skipping size test")
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(LARGE_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    if driver.current_url == BASE_URL:
        try:
            error = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-danger')]"))
            )
            assert "25" in error.text.lower() or "size" in error.text.lower() or "mb" in error.text.lower()
        except TimeoutException:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert "25" in body_text.lower() or "size" in body_text.lower(), "Application accepted >25MB file (bug)"
    else:
        pytest.fail("Application accepted >25MB file and redirected (bug)")
