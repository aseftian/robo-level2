from robocorp.tasks import task
from robocorp import browser
from RPA.Tables import Tables
import requests
from os.path import basename

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
    get_order_url = "https://robotsparebinindustries.com/orders.csv"
    orders = get_orders(get_order_url)
    open_robot_order_website()
    for order in orders:
        print(f"order robot: {order}")
        close_annoying_modal()
        fill_and_submit_order_robot(order)

def open_robot_order_website():
    """Navigates to the given URL"""
    browser.goto("https://robotsparebinindustries.com/#/robot-order")

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
    filename = basename(response.url)
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

    page.click("button:text('Order another robot')")

def store_receipt_as_pdf(order_number):
    """Create receipt to PDF"""
