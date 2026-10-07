"""
Script to generate a realistic synthetic clinical PDF: Discharge_Summary_Jonathan_Doe.pdf
Contains structured clinical notes, confirmed/negated conditions, medications,
investigations, procedures, and follow-ups.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf(output_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom clinical document styles
    header_title_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
    )
    
    sub_title_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        leftIndent=15,
        textColor=colors.HexColor('#1E293B'),
    )

    story = []

    # Hospital Header
    story.append(Paragraph("ST. JUDE REGIONAL MEDICAL CENTER - INPATIENT CARDIOLOGY", header_title_style))
    story.append(Paragraph("CLINICAL DISCHARGE SUMMARY & DOSSIER REPORT", sub_title_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=10))

    # Patient Demographic Banner Table
    demo_data = [
        [
            Paragraph("<b>Patient Name:</b> Jonathan Doe", body_style),
            Paragraph("<b>MRN:</b> MRN-2026-9812", body_style),
            Paragraph("<b>DOB:</b> 1964-04-12 (62 yrs)", body_style),
        ],
        [
            Paragraph("<b>Admission Date:</b> 2026-09-28", body_style),
            Paragraph("<b>Discharge Date:</b> 2026-10-02", body_style),
            Paragraph("<b>Attending:</b> Dr. Sarah Jenkins, MD (Cardiology)", body_style),
        ]
    ]
    t_demo = Table(demo_data, colWidths=[200, 160, 170])
    t_demo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_demo)
    story.append(Spacer(1, 10))

    # Reason for Admission & History
    story.append(Paragraph("REASON FOR ADMISSION & CLINICAL COURSE", section_heading))
    story.append(Paragraph(
        "Jonathan Doe is a 62-year-old male with a history of hypertension and type 2 diabetes mellitus "
        "who presented to the Emergency Department experiencing acute substernal chest pressure radiating "
        "to the left jaw and diaphoresis on exertion. Symptoms began approximately 3 hours prior to presentation. "
        "In the ED, the patient was hemodynamically stable. An urgent CTA showed no acute pulmonary embolism or aortic dissection. "
        "Initial troponin elevation confirmed an Acute Non-ST Elevation Myocardial Infarction (NSTEMI). "
        "The patient was started on dual antiplatelet therapy and anticoagulation and admitted to the Cardiac Care Unit (CCU).",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Diagnostic Findings & Investigations
    story.append(Paragraph("DIAGNOSTIC INVESTIGATIONS & LABORATORY RESULTS", section_heading))
    lab_data = [
        [Paragraph("<b>Investigation</b>", body_style), Paragraph("<b>Result Value</b>", body_style), Paragraph("<b>Reference Range</b>", body_style), Paragraph("<b>Clinical Interpretation</b>", body_style)],
        [Paragraph("High-Sensitivity Troponin T", body_style), Paragraph("142 ng/L", body_style), Paragraph("< 14 ng/L", body_style), Paragraph("Markedly Elevated (Myocardial Necrosis)", body_style)],
        [Paragraph("12-Lead Electrocardiogram (ECG)", body_style), Paragraph("Sinus rhythm, 74 bpm", body_style), Paragraph("Normal", body_style), Paragraph("1.5mm ST-segment depression leads V4-V6", body_style)],
        [Paragraph("Transthoracic Echocardiogram (TTE)", body_style), Paragraph("LVEF 55%", body_style), Paragraph("50% - 70%", body_style), Paragraph("Hypokinesis of inferolateral wall", body_style)],
        [Paragraph("Serum Creatinine", body_style), Paragraph("1.0 mg/dL", body_style), Paragraph("0.7 - 1.3 mg/dL", body_style), Paragraph("Normal renal function baseline", body_style)],
        [Paragraph("Fasting Serum Glucose", body_style), Paragraph("138 mg/dL", body_style), Paragraph("70 - 99 mg/dL", body_style), Paragraph("Mildly elevated, consistent with T2DM", body_style)],
        [Paragraph("Serum Potassium", body_style), Paragraph("4.2 mEq/L", body_style), Paragraph("3.5 - 5.0 mEq/L", body_style), Paragraph("Normal electrolyte homeostasis", body_style)],
    ]
    t_lab = Table(lab_data, colWidths=[150, 90, 90, 200])
    t_lab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_lab)
    story.append(Spacer(1, 8))

    # Procedures Done
    story.append(Paragraph("INVASIVE PROCEDURES PERFORMED", section_heading))
    story.append(Paragraph(
        "<b>Coronary Angiography and Percutaneous Coronary Intervention (PCI):</b> Performed on hospital day 2 via right radial approach. "
        "Angiography demonstrated an 80% eccentric stenosis in the mid-left anterior descending (LAD) artery. Successful pre-dilation and "
        "deployment of a 3.0 x 18 mm Drug-Eluting Stent (DES) with 0% residual stenosis and TIMI-3 flow restored. No procedural complications.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Diagnoses (Confirmed & Negated)
    story.append(Paragraph("DISCHARGE DIAGNOSES", section_heading))
    story.append(Paragraph("<b>Confirmed Diagnoses:</b>", body_style))
    story.append(Paragraph("- Acute Non-ST Elevation Myocardial Infarction (NSTEMI) - Post-PCI to LAD", bullet_style))
    story.append(Paragraph("- Essential Hypertension (HTN) - Controlled", bullet_style))
    story.append(Paragraph("- Type 2 Diabetes Mellitus (T2DM) - Chronic, non-insulin dependent", bullet_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Rule-Out / Negated Conditions:</b>", body_style))
    story.append(Paragraph("- Ruled out Acute Pulmonary Embolism (PE) - CT pulmonary angiography negative", bullet_style))
    story.append(Paragraph("- Ruled out Acute Aortic Dissection - Normal mediastinum and aortic lumen", bullet_style))
    story.append(Spacer(1, 8))

    # Discharge Medications
    story.append(Paragraph("DISCHARGE MEDICATIONS REGIMEN", section_heading))
    med_data = [
        [Paragraph("<b>Medication Name</b>", body_style), Paragraph("<b>Dose</b>", body_style), Paragraph("<b>Route</b>", body_style), Paragraph("<b>Frequency</b>", body_style), Paragraph("<b>Indication</b>", body_style)],
        [Paragraph("Atorvastatin", body_style), Paragraph("80 mg", body_style), Paragraph("Oral", body_style), Paragraph("Once daily at bedtime", body_style), Paragraph("High-intensity statin / Atherosclerosis", body_style)],
        [Paragraph("Metoprolol Tartrate", body_style), Paragraph("25 mg", body_style), Paragraph("Oral", body_style), Paragraph("Twice daily with meals", body_style), Paragraph("Beta-blocker / Post-MI cardioprotection", body_style)],
        [Paragraph("Aspirin (Enteric Coated)", body_style), Paragraph("81 mg", body_style), Paragraph("Oral", body_style), Paragraph("Once daily in morning", body_style), Paragraph("Antiplatelet therapy", body_style)],
        [Paragraph("Metformin HCl", body_style), Paragraph("500 mg", body_style), Paragraph("Oral", body_style), Paragraph("Twice daily with meals", body_style), Paragraph("Type 2 Diabetes Mellitus control", body_style)],
        [Paragraph("Lisinopril", body_style), Paragraph("10 mg", body_style), Paragraph("Oral", body_style), Paragraph("Once daily in morning", body_style), Paragraph("ACE inhibitor / Hypertension & LV protection", body_style)],
    ]
    t_med = Table(med_data, colWidths=[130, 60, 50, 130, 160])
    t_med.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_med)
    story.append(Spacer(1, 8))

    # Follow-Up and Plan
    story.append(Paragraph("FOLLOW-UP INSTRUCTIONS & OUTSTANDING ACTIONS", section_heading))
    story.append(Paragraph("1. <b>Cardiology Clinic Follow-up:</b> Appointment with Dr. Sarah Jenkins in 2 weeks for clinical post-PCI review and wound check.", bullet_style))
    story.append(Paragraph("2. <b>Laboratory Re-evaluation:</b> Fasting Lipid Panel and Comprehensive Metabolic Panel (CMP) repeat in 6 weeks.", bullet_style))
    story.append(Paragraph("3. <b>Cardiac Rehabilitation:</b> Enrollment in Phase II Cardiac Rehab Program starting within 3 weeks.", bullet_style))
    story.append(Spacer(1, 10))

    # Clinician Sign-off
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#94A3B8'), spaceAfter=8))
    story.append(Paragraph("Electronically Verified & Signed: <b>Dr. Sarah Jenkins, MD, FACC</b> - License #MD-883921", body_style))
    story.append(Paragraph("St. Jude Regional Medical Center Cardiology Service", sub_title_style))

    doc.build(story)
    print(f"Successfully generated clinical PDF at: {output_path}")

if __name__ == "__main__":
    generate_pdf("demo/Discharge_Summary_Jonathan_Doe.pdf")
