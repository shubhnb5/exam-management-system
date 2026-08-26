import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.pdf_generator import TicketConfig, generate_hall_ticket_pdf
from app.services.qr_service import generate_qr_token

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ticket_template", "config.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "storage", "tickets", "sample_ticket.pdf")

if __name__ == "__main__":
    config = TicketConfig.load(CONFIG_PATH)
    token = generate_qr_token()
    generate_hall_ticket_pdf(
        output_path=OUTPUT_PATH,
        student_name="Asha Patil",
        mobile_number="9876543210",
        exam_center_name="Center A - Ramanbaug, New English School",
        qr_token=token,
        config=config,
    )
    print(f"QR token: {token}")
    print(f"Ticket written to: {os.path.abspath(OUTPUT_PATH)}")
