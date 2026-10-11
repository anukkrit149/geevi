from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
root=Path(__file__).resolve().parents[1]/'fixtures'
for name in ['meera','arun']:
    c=canvas.Canvas(str(root/f'{name}-profile-context.pdf'),pagesize=A4)
    c.setTitle(f'{name.title()} - synthetic profile context')
    c.setFont('Helvetica-Bold',16);c.drawString(40,800,'SYNTHETIC DEMO - NOT A CLINICAL REPORT')
    lines=[f'Patient ID: DEMO-{name.upper()}','Report date: 2026-10-11',
           'Disease extent: Marrow involvement recorded; other sites not assessed.',
           'Functional assessment: '+('Independent daily activity in this fictional note.' if name=='meera' else 'Current functional assessment pending.'),
           'Organ assessment: Current organ assessment pending.',
           'Patient priorities: '+('Wants a fertility discussion before care planning.' if name=='meera' else 'Wants family included in discussions about goals of care.'),
           'Access and support: '+('Family transport available; cost discussion pending.' if name=='meera' else 'Depends on family transport; financial assessment pending.')]
    c.setFont('Helvetica',10)
    for i,line in enumerate(lines): c.drawString(40,755-i*32,line)
    c.drawString(40,430,'Fictional context for interface review only. No treatment outcome is represented.')
    c.save()
