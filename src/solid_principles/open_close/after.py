import os
import smtplib
import faker
import stripe

from twilio.rest import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from pydantic import BaseModel
from stripe import Charge
from stripe import StripeError

_ = load_dotenv()


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerData(BaseModel):
    name: str
    contact_info: ContactInfo


class PaymentData(BaseModel):
    amount: int
    source: str


class Notifier(ABC):
    @abstractmethod
    def send_confirmation(self, customer_data: CustomerData): ...


class EmailNotifier(Notifier):
    def send_confirmation(self, customer_data: CustomerData):
        msg = MIMEMultipart()
        password = os.getenv("GMAIL_PASS")
        msg["From"] = "ethical.hacking.python@gmail.com"
        msg["To"] = customer_data.contact_info.email
        msg["Subject"] = "Payment Confirmation"
        msg.attach(MIMEText("The payment has been successful. Congrats!"))

        try:
            server = smtplib.SMTP('smtp.gmail.com:587')
            server.starttls()
            server.login(user=msg['From'], password=password)
            server.sendmail(from_addr=msg["From"], to_addrs=msg['To'], msg=msg.as_string())
            server.quit()
            print("Email successfully sent.")
        except Exception as e:
            print("Error while sending email:", e)


class SMSNotifier(Notifier):
    def send_confirmation(self, customer_data: CustomerData):
        sms_gateway = "Twilio"
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)

        try:
            message = client.messages.create(
                messaging_service_sid=os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
                body='Ahoy 👋 Thank you for your payment!',
                to=customer_data.contact_info.phone,
            )
            print(
                f"SMS successfully sent to {customer_data.contact_info.phone} using {sms_gateway}. Message SID: {message.sid}")
        except Exception as e:
            print("Error while sending SMS:", e)


@dataclass
class TransactionLogger:
    @staticmethod
    def log(
            customer_data: CustomerData,
            payment_data: PaymentData,
            charge: Charge
    ):
        with open("transactions.log", "a") as log_file:
            log_file.write(f"{customer_data.name} paid {payment_data.amount}\n")
            log_file.write(f"Payment status: {charge['status']}\n")


class PaymentProcessor(ABC):
    @abstractmethod
    def process_transaction(
            self,
            customer_data: CustomerData,
            payment_data: PaymentData
    ) -> Charge: ...


@dataclass
class StripePaymentProcessor(PaymentProcessor):
    def process_transaction(
            self,
            customer_data: CustomerData,
            payment_data: PaymentData
    ) -> Charge:
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        try:
            charge = stripe.Charge.create(
                amount=payment_data.amount,
                currency="usd",
                source=payment_data.source,
                description="Charge for " + customer_data.name,
            )
            print("Payment successful")
            return charge
        except StripeError as e:
            print("Payment failed:", e)
            raise e


@dataclass
class PaymentService:
    payment_processor: PaymentProcessor = field(default_factory=StripePaymentProcessor)
    notifier: Notifier = field(default_factory=EmailNotifier)
    logger = TransactionLogger()

    def process_transaction(
            self,
            customer_data: CustomerData,
            payment_data: PaymentData
    ) -> Charge:
        try:
            charge = self.payment_processor.process_transaction(
                customer_data, payment_data
            )
            self.notifier.send_confirmation(customer_data)
            self.logger.log(customer_data, payment_data, charge)
            return charge
        except StripeError as e:
            raise e


if __name__ == "__main__":
    faker = faker.Faker(locale="es_AR")
    sms_notifier = SMSNotifier()
    payment_processor_sms = PaymentService(notifier=sms_notifier)
    payment_processor_email = PaymentService()

    customer_data_with_email = CustomerData(
        name=faker.name(),
        contact_info=ContactInfo(
            email="gobeamariano@gmail.com"
        )
    )
    customer_data_with_phone = CustomerData(
        name=faker.name(),
        contact_info=ContactInfo(
            phone="+5491138089556"
        )
    )

    payment_info = PaymentData(
        amount=faker.random_int(min=100, max=5000),
        source="tok_visa"
    )

    payment_processor_sms.process_transaction(customer_data_with_phone, payment_info)
    payment_processor_email.process_transaction(customer_data_with_email, payment_info)

    try:
        error_payment_data = PaymentData(
            amount=faker.random_int(min=100, max=5000),
            source="tok_radarBlock"
        )
        payment_processor_email.process_transaction(
            customer_data_with_email,
            error_payment_data
        )
    except Exception as err:
        print(f"Payment failed and PaymentProcessor raised an exception: {err}")
