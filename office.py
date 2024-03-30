import random
import smtplib
import string  
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import time
import concurrent.futures
from tqdm import tqdm

logging.basicConfig(level=logging.DEBUG)

def load_smtp_credentials(file_path):
    smtp_credentials_list = []
    try:
        with open(file_path, 'r') as smtp_file:
            for line in smtp_file:
                email, password = line.strip().split(':')
                smtp_credentials_list.append((email, password))
    except FileNotFoundError:
        logging.error(f"Le fichier '{file_path}' est introuvable.")
    return smtp_credentials_list

smtp_credentials_list = load_smtp_credentials('smtp.txt')
if not smtp_credentials_list:
    logging.error("Aucune information SMTP n'a été trouvée dans le fichier 'smtp.txt'.")
    exit(1)

message_content_template = ''
try:
    with open('message.html', 'r') as file:
        message_content_template = file.read()
except FileNotFoundError:
    logging.error("Le fichier 'message.html' est introuvable.")
    exit(1)

recipients = []
try:
    with open('liste.txt', 'r') as file:
        recipients = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    logging.error("Le fichier 'liste.txt' est introuvable.")
    exit(1)

if not recipients:
    logging.error("Aucun destinataire trouvé dans le fichier 'liste.txt'.")
    exit(1)

subjects = []
try:
    with open('sujet.txt', 'r') as file:
        subjects = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    logging.error("Aucun sujet trouvé dans le fichier 'sujet.txt'.")
    exit(1)

links = []
try:
    with open("liens.txt", 'r') as file:
        links = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    logging.error("Aucun lien trouvé dans le fichier 'liens.txt'.")
    exit(1)

max_attempts = 3

def generate_code(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def format_subject(subject, recipient):
    return subject.replace('##Email##', recipient)

def send_email(sender_email, sender_password, recipient):
    sender_name = ""
    subject = random.choice(subjects)
    subject_with_code = subject + ' #' + generate_code()

    msg = MIMEMultipart()
    msg['From'] = f"{sender_name} <{sender_email}>"
    msg['To'] = recipient
    msg['Subject'] = subject_with_code

    message_content = message_content_template.replace('##Email##', recipient)

    random_link = random.choice(links)
    message_content = message_content.replace('##lien##', random_link)

    msg.attach(MIMEText(message_content, 'html'))

    attempt = 1
    while attempt <= max_attempts:
        try:
            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient, msg.as_string())
                logging.info(f"L'email a été envoyé à {recipient} avec le sujet : {subject_with_code}")
                return True
        except smtplib.SMTPAuthenticationError as e:
            logging.error(f"Authentification échouée pour {sender_email}: {e.smtp_error.decode()}")
            logging.info(f"Suppression du SMTP {sender_email} de la liste...")
            smtp_credentials_list.remove((sender_email, sender_password))
            with open('smtp.txt', 'w') as smtp_file:
                for email, password in smtp_credentials_list:
                    smtp_file.write(f"{email}:{password}\n")
            return False
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'email à {recipient} avec le sujet : {subject_with_code} - Tentative {attempt}: {e}")
            attempt += 1
            time.sleep(1)

    logging.error(f"Échec de l'envoi de l'email à {recipient} après {max_attempts} tentatives.")
    return False

def send_emails_with_retry(smtp_credentials_list, recipients):
    num_threads = min(len(smtp_credentials_list), 700)
    total_emails = len(recipients)
    sent_emails = 0
    with tqdm(total=total_emails, desc="Envoi des emails", unit="email") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for recipient in recipients:
                smtp_credentials = random.choice(smtp_credentials_list)
                sender_email, sender_password = smtp_credentials
                futures.append(executor.submit(send_email, sender_email, sender_password, recipient))

            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    sent_emails += 1
                    pbar.update(1)
                    pbar.set_postfix(sent=sent_emails, remaining=total_emails - sent_emails)

if __name__ == "__main__":
    send_emails_with_retry(smtp_credentials_list, recipients)

logging.info("Tous les courriers ont été envoyés.")
