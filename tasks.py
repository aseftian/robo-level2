from robocorp.tasks import task
from robocorp import browser, storage
from RPA.Tables import Tables
from RPA.PDF import PDF
from fpdf import FPDF
from bs4 import BeautifulSoup
import requests
from os.path import basename
import os
import time
import shutil
from pathlib import Path

baseurl = "https://robotsparebinindustries.com"

@task
def order_robot_from_RobotSpareBin():
    """
    Orders robots from RobotSpareBin Industries Inc.
    Saves the order HTML receipt as a PDF file.
    Saves the screenshot of the ordered robot.
    Embeds the screenshot of the robot to the PDF receipt.
    Creates ZIP archive of the receipts and the images.
    """
    browser.configure(
        slowmo=500,
    )
    get_order_url = f"{baseurl}/orders.csv"
    orders = get_orders(get_order_url)
    open_robot_order_website()
    for order in orders:
        print(f"order robot: {order}")
        close_annoying_modal()
        fill_and_submit_order_robot(order)
    
    archive_receipts()

def open_robot_order_website():
    """Navigates to the given URL"""
    browser.goto(f"{baseurl}/#/robot-order")

def close_annoying_modal():
    """
    Close the modal when open the website for the first time
    or when create new order
    """
    page = browser.page()
    page.wait_for_selector(".modal")
    page.click("button:text('OK')")

def download_order_file(url: str) -> str:
    """
    Download the order file
    """
    response = requests.get(url)
    response.raise_for_status()
    filename = f"output/{basename(response.url)}"
    print(f"Downloaded filename {filename}")
    with open(filename, 'wb') as stream:
        stream.write(response.content)
    return filename

def get_orders(url: str):
    """
    Get orders by download the order file then convert as Tables
    """
    order_file = download_order_file(url)
    library = Tables()
    orders = library.read_table_from_csv(order_file, columns=["Order number", "Head", "Body", "Legs", "Address"])
    return orders

def fill_and_submit_order_robot(order):
    """Building the robot by the specified order"""
    page = browser.page()
    page.select_option("select#head", value=str(order["Head"]))
    body = order["Body"]
    page.click(f"input[type='radio'][value='{body}']")
    locator = "xpath=//label[contains(text(),'3. Legs:')]/following-sibling::input"
    page.wait_for_selector(locator)
    page.fill(locator, order["Legs"])
    page.fill("#address", order["Address"])
    page.click("button:text('Order')")
    while(page.is_visible(".alert-danger")):
        page.click("button:text('Order')")
    
    # Get the order receipt
    order_number = order["Order number"]
    robot_receipt = store_receipt_as_pdf(order_number)

    robot_image = screenshot_robot(order_number)
    embed_screenshot_to_receipt(robot_image, robot_receipt)
    
    page.click("button:text('Order another robot')")

def store_receipt_as_pdf(order_number):
    """Create receipt to PDF"""
    output_folder = "output"
    pdf = PDF()
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    page = browser.page()
    soup = BeautifulSoup(page.content(), 'html.parser')
    receipt = soup.find('div', id='receipt')
    print(f"Receipt content: {receipt}")

    output_path = f"{output_folder}/receipt_{order_number}.pdf"
    receipt_str = str(receipt)+''
    pdf.html_to_pdf(receipt_str, output_path, margin=10)

    return output_path

def screenshot_robot(order_number):
    """Screenshot preview robot"""
    page = browser.page()
    robot_preview = page.locator("div#robot-preview-image")
    # sometimes, the robot preview missing its part in the screenshot
    # so, add at least 1 or 2 seconds to make sure the preview has been loaded in browser to take a screenshot
    time.sleep(1)
    robot_preview_img_bytes = browser.screenshot(robot_preview)

    with open(f"output/temp_img_{order_number}.png", "wb") as file:
        file.write(robot_preview_img_bytes)

    return file.name

def embed_screenshot_to_receipt(screenshot, pdf_file):
    """Embedding the screenshot of preview robot"""
    pdf = PDF()
    pdf.add_watermark_image_to_pdf(
        image_path=screenshot,
        source_path=pdf_file,
        output_path=pdf_file
    )
    os.remove(screenshot)

def archive_receipts():
    dir_path = "output"
    files = list(Path(dir_path).glob('*.pdf'))

    temp_dir_path = Path("output/temp_archive_dir")
    temp_dir_path.mkdir(parents=True, exist_ok=True)

    for file_path in files:
        shutil.copy(file_path, temp_dir_path/file_path.name)
        os.remove(file_path)
    
    output_zip_path = Path("output/order_receipts")

    shutil.make_archive(output_zip_path, 'zip', temp_dir_path)
    shutil.rmtree(temp_dir_path)
