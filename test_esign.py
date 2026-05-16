# test_esign.py
import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException

BASE_URL = os.getenv("BASE_URL", "https://test-env-slim.synel-saas.com")

# Paths for test files - they will be created in CI if missing
TEST_FILES_DIR = "test_files"
VALID_PDF = os.path.join(TEST_FILES_DIR, "valid.pdf")
INVALID_TXT = os.path.join(TEST_FILES_DIR, "invalid.txt")
LARGE_PDF = os.path.join(TEST_FILES_DIR, "large.pdf")

# Helper to wait for any error message on the page
def wait_for_error(driver, timeout=5):
    try:
        error = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'error') or contains(@class, 'alert') or contains(text(), 'Error') or contains(text(), 'required')]"))
        )
        return error.text
    except TimeoutException:
        return None

def test_TC01_successful_submission(driver):
    """Positive: all valid data -> success message"""
    driver.get(BASE_URL)

    driver.find_element(By.ID, "description").send_keys("Test Contract")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    success = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Success') or contains(text(), 'sent') or contains(text(), 'signed')]"))
    )
    assert success is not None

def test_TC02_missing_recipient(driver):
    """Recipient not selected -> error message"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver)
    assert error is not None, "No error message when recipient missing"
    assert "recipient" in error.lower() or "select" in error.lower()

def test_TC03_missing_category(driver):
    """Category not selected -> possibly optional? We'll check."""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver)
    if error is None:
        pytest.xfail("Category may be optional – confirm requirement")
    else:
        assert "category" in error.lower() or "select" in error.lower()

def test_TC04_empty_email(driver):
    """Email field empty -> error required"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    # email left blank
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver)
    assert error is not None, "No error when email empty"
    assert "email" in error.lower() or "required" in error.lower()

def test_TC05_invalid_email_format(driver):
    """Email without @ and domain -> error"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(VALID_PDF)
    driver.find_element(By.ID, "email").send_keys("invalid_email")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver)
    assert error is not None, "No error for invalid email format"
    assert "valid" in error.lower() or "email" in error.lower()

def test_TC06_no_file_selected(driver):
    """No file uploaded -> error"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver)
    assert error is not None, "No error when no file selected"
    assert "file" in error.lower() or "document" in error.lower()

def test_TC07_non_pdf_file(driver):
    """Upload .txt file -> should reject"""
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(INVALID_TXT)
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver, timeout=10)
    assert error is not None, "Application accepted .txt file (bug)"
    assert "pdf" in error.lower() or "format" in error.lower()

def test_TC08_file_size_exceeds_25mb(driver):
    """File >25 MB -> error"""
    if not os.path.exists(LARGE_PDF):
        pytest.skip("large.pdf not found, skipping size test")
    driver.get(BASE_URL)
    driver.find_element(By.ID, "description").send_keys("Test")
    Select(driver.find_element(By.ID, "recipient")).select_by_visible_text("John Smith")
    Select(driver.find_element(By.ID, "category")).select_by_visible_text("Onboarding")
    driver.find_element(By.CSS_SELECTOR, "input[type='file']").send_keys(LARGE_PDF)
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.XPATH, "//button[text()='Submit']").click()

    error = wait_for_error(driver, timeout=10)
    assert error is not None, "Application accepted file >25MB (bug)"
    assert "25" in error.lower() or "size" in error.lower() or "mb" in error.lower()
