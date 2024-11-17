import os
import smtplib
import faker
import stripe

from stripe import StripeError
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

_ = load_dotenv(override=True)
faker = faker.Faker(locale="es_AR")


class PaymentProcessor:
    def process_transaction(self, customer_data, payment_data):
        if not customer_data.get("name"):
            print("Invalid customer data: missing name")
            return

        if not customer_data.get("contact_info"):
            print("Invalid customer data: missing contact info")
            return

        if not payment_data.get("source"):
            print("Invalid payment data")
            return

        stripe.api_key = os.getenv("STRIPE_API_KEY")

        try:
            charge = stripe.Charge.create(
                amount=payment_data["amount"],
                currency="usd",
                source=payment_data["source"],
                description="Charge for " + customer_data["name"],
            )
            print("Payment successful")
        except StripeError as e:
            print("Payment failed:", e)
            return

        if "email" in customer_data["contact_info"]:

            msg = MIMEMultipart()
            password = os.getenv("GMAIL_PASS")
            print(f'Password: {password}')
            msg["From"] = "ethical.hacking.python@gmail.com"
            msg["To"] = customer_data["contact_info"]["email"]
            msg["Subject"] = "Payment Confirmation"
            msg.attach(MIMEText("The payment has been successful. Congrats!"))
            print("Msj to send: ", msg.as_string())

            try:
                server = smtplib.SMTP('smtp.gmail.com:587')
                server.starttls()
                print("Server started")
                server.login(user=msg['From'], password=password)
                print("Server logged in")
                server.sendmail(from_addr=msg["From"], to_addrs=msg['To'], msg=msg.as_string())
                print("Email sent")
                server.quit()
            except Exception as e:
                print("Error sending email: ", e)
            print("Email sent to", customer_data["contact_info"]["email"])

        elif "phone" in customer_data["contact_info"]:
            sms_gateway = "twilio"
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            print(f'Account SID: {account_sid}')
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            print(f'Auth token: {auth_token}')
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                messaging_service_sid=os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
                body='Ahoy 👋 Thank you for your payment!',
                to=customer_data["contact_info"]["phone"],
            )
            print("Send the sms using twilio")
            print(f"messaging_service_sid: {os.getenv('TWILIO_MESSAGING_SERVICE_SID')}")
            print(
                f"send the sms using {sms_gateway}: SMS sent to {customer_data["contact_info"]["phone"]}: Thank you for your payment."
            )
            print(message.sid)

        else:
            print("No valid contact information for notification")
            return

        with open("transactions.log", "a") as log_file:
            log_file.write(
                f"{customer_data['name']} paid {payment_data['amount']}\n"
            )
            log_file.write(f"Payment status: {charge['status']}\n")


if __name__ == "__main__":
    payment_processor = PaymentProcessor()

    customer_data_with_email = {
        "name": faker.name(),
        "contact_info": {"email": "gobeamariano@gmail.com"},
    }
    customer_data_with_phone = {
        "name": faker.name(),
        "contact_info": {"phone": "+5491138089556"},
    }

    payment_data_email = {"amount": faker.random_int(min=100, max=20000), "source": "tok_mastercard", "cvv": 123}
    payment_data_phone = {"amount": faker.random_int(min=100, max=20000), "source": "tok_visa", "cvv": 345}

    payment_processor.process_transaction(
        customer_data_with_email, payment_data_email
    )
    payment_processor.process_transaction(
        customer_data_with_phone, payment_data_phone
    )
