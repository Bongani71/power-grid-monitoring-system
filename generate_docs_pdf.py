
from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(0, 82, 204)
        self.cell(0, 10, 'South African National Grid Monitoring System', border=False, align='C')
        self.ln(10)
        self.set_font('helvetica', 'I', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'SYSTEM DOCUMENTATION - END-TO-END SUMMARY', border=False, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def create_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # 1. Title & Intro
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, '1. Executive Overview', ln=True)
    pdf.ln(5)
    pdf.set_font('helvetica', '', 11)
    summary = (
        "The Power Grid Monitoring System is a professional, enterprise-grade solution "
        "designed for real-time grid telemetry tracking and predictive demand management. "
        "It provides a unified command center for grid operators, enabling preemptive "
        "decision-making via Machine Learning forecasting."
    )
    pdf.multi_cell(0, 7, summary)
    pdf.ln(10)

    # 2. Add System Screenshot (Elite touch)
    if os.path.exists("docs_screenshot.png"):
        pdf.image("docs_screenshot.png", x=15, w=180)
        pdf.ln(5)
        pdf.set_font('helvetica', 'I', 9)
        pdf.cell(0, 10, 'Figure 1: Real-time Control Room Dashboard Interface', align='C', ln=True)
        pdf.ln(10)

    # 3. The 5 Pillars
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '2. The 5 Pillars of Quality IT Alignment', ln=True)
    pdf.ln(5)
    
    pillars = [
        ("People", "Designed for humans with intuitive UI/UX and actionable AI insights."),
        ("Data", "Ingestion of real-time multi-variate telemetry (MW, Hz, kV)."),
        ("Network", "A distributed architecture using a robust REST API service layer."),
        ("Security", "Fault-tolerant design with robust input validation and model fallbacks."),
        ("Software/Hardware", "Modern stack (FastAPI + Streamlit) optimized for performance.")
    ]
    
    for title, desc in pillars:
        pdf.set_font('helvetica', 'B', 11)
        pdf.cell(40, 7, f"- {title}:", ln=False)
        pdf.set_font('helvetica', '', 11)
        pdf.multi_cell(0, 7, desc)
        pdf.ln(2)
        
    pdf.ln(10)

    # 4. Architecture
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, '3. End-to-End System Workflow', ln=True)
    pdf.ln(5)
    pdf.set_font('helvetica', '', 11)
    workflow = (
        "1. Data Layer: Ingests telemetry into the central database.\n"
        "2. Analysis Layer: Aggregates national metrics and runs ML models.\n"
        "3. Forecasting Layer: Predicts demand curves for the next 6 hours.\n"
        "4. Presentation Layer: Displays interactive maps, charts, and risk levels."
    )
    pdf.multi_cell(0, 7, workflow)
    
    # Finalizing
    pdf.output("System_Documentation.pdf")
    print("✅ System_Documentation.pdf generated successfully.")

if __name__ == "__main__":
    create_pdf()
