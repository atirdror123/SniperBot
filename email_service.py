
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_daily_recap(signals):
    """
    Sends an email with the list of signals found today.
    signals: List of StockSetup objects or dicts.
    """
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")

    if not sender_email or not sender_password or not recipient_email:
        print("[EMAIL] Credentials missing in .env. Skipping email.")
        return

    subject = f"🎯 Sniper Scan Results - {len(signals)} Signals Found"
    
    body = "<h2>Daily Scan Complete</h2>"
    body += f"<p>Found {len(signals)} potential setups:</p><ul>"
    
    for s in signals:
        # Handle both object and dict (depending on where it's called)
        ticker = getattr(s, 'ticker', s.get('ticker', 'UNKNOWN'))
        score = getattr(s, 'final_score', s.get('final_score', 0))
        price = getattr(s, 'price', s.get('entry_price', 0))
        
        body += f"<li><b>{ticker}</b> - Score: {score:.1f} (Price: ${price:.2f})</li>"
    
    body += "</ul><p>Check the Dashboard for details.</p>"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        # Default to Gmail SMTP (587)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print("[EMAIL] Notification sent successfully.")
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")
