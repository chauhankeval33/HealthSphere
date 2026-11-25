
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

file_name = "conflicting_liver_report.pdf"

pdf = canvas.Canvas(file_name, pagesize=A4)
width, height = A4

pdf.setTitle("Fictional Liver Function Test - Conflict Test")

pdf.setFont("Helvetica-Bold", 16)
pdf.drawString(60, height - 70, "LIVER FUNCTION TEST REPORT")

pdf.setFont("Helvetica", 11)
pdf.drawString(60, height - 110, "Patient: Fictional Test Patient")
pdf.drawString(60, height - 130, "Report Type: Training / Conflict Testing")
pdf.drawString(60, height - 150, "Date: 25 November 2026")

pdf.setFont("Helvetica-Bold", 12)
pdf.drawString(60, height - 195, "Test")
pdf.drawString(260, height - 195, "Result")
pdf.drawString(380, height - 195, "Unit")

pdf.setFont("Helvetica", 12)
pdf.drawString(60, height - 225, "Alanine Aminotransferase (ALT / SGPT)")
pdf.drawString(260, height - 225, "58")
pdf.drawString(380, height - 225, "U/L")

pdf.drawString(60, height - 265, "Reference Range: Male <45 U/L")
pdf.drawString(60, height - 295, "This is a fictional training document.")
pdf.drawString(60, height - 315, "It is not a real medical report or clinical result.")

pdf.save()

print(f"Created successfully: {file_name}")
