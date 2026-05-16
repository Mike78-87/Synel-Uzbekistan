# test_esign.py
import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

BASE_URL = os.getenv("BASE_URL", "https://test-env-slim.synel-saas.com")

TEST_FILES_DIR = "test_files"
VALID_PDF = os.path.join(TEST_FILES_DIR, "valid.pdf")
INVALID_TXT = os.path.join(TEST_FILES_DIR, "invalid.txt")
LARGE_PDF = os.path.join(TEST_FILES_DIR, "large.pdf")

def wait_for_validation_error(driver, field_name, timeout=5):
    """Wait for a validation error message for a specific field"""
    try:
        error_span = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, f"//span[@data-valmsg-for='{field_name}' and contains(@class, 'text-danger') and not(text()='')]"))
        )
        return error_span.text
    except TimeoutException:
        return None

def wait_for_success_message(driver, timeout=5):
    """Check if success message appears after submission"""
    try:
        # После успешной отправки обычно происходит редирект или появляется сообщение
        # Если редирект – проверяем URL
        WebDriverWait(driver, timeout).until(
            EC.url_changes(BASE_URL)
        )
        return "Redirected"
    except TimeoutException:
        # Если нет редиректа, ищем сообщение об успехе на странице
        try:
            success = driver.find_element(By.XPATH, "//*[contains(text(), 'Success') or contains(text(), 'sent') or contains(text(), 'signed')]")
            return success.text
        except:
            return None

# ========== TESTS ==========

def test_TC01_successful_submission(driver):
    """Positive: all valid data -> success or redirect"""
    driver.get(BASE_URL)
    
    # Fill description
    driver.find_element(By.ID, "Description").send_keys("Test Contract")
    # Select recipient
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    # Select category
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    # Upload PDF
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    # Fill email
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    # Submit
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
    
    # Recipient is required? Check validation for Recipient field
    error = wait_for_validation_error(driver, "Recipient")
    # Если нет специального сообщения для Recipient, проверяем общую валидацию
    if error is None:
        error = wait_for_validation_error(driver, "Description")  # any validation summary?
    assert error is not None, "No error when recipient missing"
    assert "select" in error.lower() or "recipient" in error.lower()

def test_TC03_missing_category(driver):
    """Category not selected -> error or allowed (depends on requirements)"""
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
    """Description empty (it is required according to data-val-required)"""
    driver.get(BASE_URL)
    # Don't fill Description
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
    # Leave email empty
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    
    error = wait_for_validation_error(driver, "SenderEmail")
    assert error is not None, "No error when email empty"
    assert "required" in error.lower() or "email" in error.lower()

def test_TC06_invalid_email_format(driver):
    """Email without @ and domain -> should be invalid, but server-side validation may not catch it."""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "SenderEmail").send_keys("invalid_email")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    
    # Check if browser's built-in validation catches it or server returns error
    error = wait_for_validation_error(driver, "SenderEmail", timeout=3)
    if error is None:
        # Maybe HTML5 validation prevents submission? Check if page reloaded
        if driver.current_url == BASE_URL:
            pytest.fail("No client-side or server-side validation for invalid email format (bug)")
        else:
            pytest.fail("Form submitted with invalid email (bug)")
    else:
        assert "valid" in error.lower() or "email" in error.lower()

def test_TC07_no_file_selected(driver):
    """No file uploaded -> error"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    
    # File validation might be on server side, check for any error
    # If page reloads with same URL, check for validation summary
    if driver.current_url == BASE_URL:
        # Try to find any error message
        try:
            error = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-danger') and text()!='']"))
            )
            assert "file" in error.text.lower() or "document" in error.text.lower()
        except:
            pytest.fail("No error when no file selected (bug)")
    else:
        # Redirected? Possibly means file is optional? That would be a bug.
        pytest.fail("Form submitted without file (bug)")

def test_TC08_non_pdf_file(driver):
    """Upload .txt file -> should reject"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "Description").send_keys("Test")
    Select(driver.find_element(By.ID, "Recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "Category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(INVALID_TXT)
    driver.find_element(By.ID, "SenderEmail").send_keys("test@example.com")
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    
    # If browser accepts .txt, that's a bug. Wait for potential error.
    if driver.current_url == BASE_URL:
        error = wait_for_validation_error(driver, "file", timeout=5)
        if error:
            assert "pdf" in error.lower() or "format" in error.lower()
        else:
            # Check if any server-side validation message appears
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
        error = wait_for_validation_error(driver, "file", timeout=5)
        if error:
            assert "25" in error.lower() or "size" in error.lower() or "mb" in error.lower()
        else:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            assert "25" in body_text.lower() or "size" in body_text.lower(), "Application accepted >25MB file (bug)"
    else:
        pytest.fail("Application accepted >25MB file and redirected (bug)")
